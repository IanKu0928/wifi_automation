
class AnalysisEngine:

    def __init__(self):
        # Initial heuristic thresholds.
        # These are analysis warnings, not test pass/fail limits.
        self.high_latency_ms = 100.0
        self.latency_variation_ms = 30.0
        self.high_retransmits = 100
        self.throughput_ratio = 2.0
        self.rssi_margin_db = 5.0
        self.throughput_margin_ratio = 1.2

    def analyze(self, data):
        findings = []
        testcases = data.get("testcases") or []

        def add(rule_id, severity, test_ids, title,
                evidence, possible_causes, recommendations):
            findings.append({
                "rule_id": rule_id,
                "severity": severity,
                "test_ids": test_ids,
                "title": title,
                "evidence": evidence,
                "possible_causes": possible_causes,
                "recommendations": recommendations
            })

        for tc in testcases:
            test_id = tc.get("test_id", "")
            status = tc.get("status")
            metrics = tc.get("metrics") or {}

            # Rule 1: Test case failure
            if status == "FAIL":
                add(
                    "TEST_FAILED", "CRITICAL", [test_id],
                    f"{test_id}: Test case did not meet its acceptance criteria.",
                    tc.get("message", ""),
                    ["DUT issue", "Network condition",
                     "Test environment or configuration issue"],
                    ["Review the failing metric and configured threshold.",
                     "Check DUT and STA logs.",
                     "Repeat the test to confirm reproducibility."]
                )

            if test_id in ("TC01", "TC02"):

                loss = metrics.get("packet_loss_percent")
                max_rtt = metrics.get("max_latency_ms")
                mdev = metrics.get("mdev_latency_ms")

                # Rule 2: Packet loss
                if isinstance(loss, (int, float)) and loss > 0:
                    add(
                        "PING_PACKET_LOSS", "WARNING", [test_id],
                        "ICMP packet loss detected.",
                        f"Packet loss = {loss}%",
                        ["Wireless packet loss",
                         "Network congestion",
                         "Routing or ICMP handling issue"],
                        ["Repeat ping testing.",
                         "Inspect WiFi association and route.",
                         "Check RF and interface error statistics."]
                    )

                # Rule 3: Latency spike
                if isinstance(max_rtt, (int, float)) and max_rtt > self.high_latency_ms:
                    add(
                        "PING_LATENCY_SPIKE", "WARNING", [test_id],
                        "High latency spike detected.",
                        f"Maximum RTT = {max_rtt:.3f} ms",
                        ["Temporary wireless contention",
                         "Network buffering",
                         "System scheduling delay"],
                        ["Run a longer ping test.",
                         "Compare latency with wireless statistics.",
                         "Check CPU load and background traffic."]
                    )

                # Rule 4: Latency variation
                if isinstance(mdev, (int, float)) and mdev > self.latency_variation_ms:
                    add(
                        "PING_LATENCY_VARIATION", "WARNING", [test_id],
                        "High variation in ICMP round-trip time.",
                        f"RTT mdev = {mdev:.3f} ms",
                        ["Variable airtime contention",
                         "Queueing delay",
                         "Intermittent network activity"],
                        ["Collect a longer RTT sample.",
                         "Check whether spikes repeat across runs.",
                         "Correlate with throughput and retransmissions."]
                    )

            if test_id in ("TC05", "TC06"):

                retransmits = metrics.get("retransmits")

                # Rule 5: TCP retransmissions
                if (
                    isinstance(retransmits, (int, float))
                    and retransmits >= self.high_retransmits
                ):
                    add(
                        "TCP_RETRANSMISSION_HIGH", "WARNING", [test_id],
                        "Elevated TCP retransmission count detected.",
                        f"TCP retransmits = {retransmits}",
                        ["Packet loss along the TCP path",
                         "Congestion or queueing",
                         "Wireless link instability"],
                        ["Compare retransmissions across similar runs.",
                         "Inspect interface and wireless retry counters.",
                         "Check TCP and system statistics."]
                    )

        # Rule 6: Upload / Download imbalance
        by_id = {
            tc.get("test_id"): tc
            for tc in testcases
        }

        upload = (
            (by_id.get("TC05") or {})
            .get("metrics", {})
            .get("receiver_mbps")
        )
        download = (
            (by_id.get("TC06") or {})
            .get("metrics", {})
            .get("receiver_mbps")
        )

        if (
            isinstance(upload, (int, float))
            and isinstance(download, (int, float))
            and upload > 0
            and download > 0
        ):
            ratio = max(upload, download) / min(upload, download)

            if ratio >= self.throughput_ratio:
                add(
                    "THROUGHPUT_ASYMMETRY", "WARNING",
                    ["TC05", "TC06"],
                    "Significant difference between upload and download throughput.",
                    f"Upload = {upload:.1f} Mbps; "
                    f"Download = {download:.1f} Mbps; "
                    f"Ratio = {ratio:.2f}",
                    ["Different transmission or reception conditions",
                     "Directional interference or congestion",
                     "Driver or device processing differences"],
                    ["Repeat upload and download measurements.",
                     "Compare TCP retransmissions in both directions.",
                     "Check DUT and STA wireless statistics."]
                )
        
        # --------------------------------
        # WiFi Performance / Data Quality
        # --------------------------------

        import math

        def valid_number(value):
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            )

        for tc in testcases:
            test_id = tc.get("test_id", "")
            status = tc.get("status")
            metrics = tc.get("metrics") or {}

            # RSSI validation (TC04)
            if test_id == "TC04":
                rssi = metrics.get("signal_dbm")
                min_rssi = metrics.get("min_signal_dbm")

                if not (
                    valid_number(rssi)
                    and valid_number(min_rssi)
                ):
                    if status == "PASS":
                        add(
                            "MISSING_TEST_METRIC", "WARNING",
                            [test_id],
                            "Required RSSI metrics are missing or invalid.",
                            f"RSSI = {rssi}; threshold = {min_rssi}",
                            [
                                "Signal data collection may be incomplete",
                                "Result parsing or metric mapping may be incorrect"
                            ],
                            [
                                "Check the STA signal command output.",
                                "Verify the RSSI parser and result.json metrics."
                            ]
                        )
                    continue

                margin = rssi - min_rssi

                if rssi < min_rssi:
                    add(
                        "RSSI_BELOW_THRESHOLD", "CRITICAL",
                        [test_id],
                        "WiFi signal strength is below the required threshold.",
                        f"RSSI = {rssi} dBm; minimum = {min_rssi} dBm",
                        [
                            "Weak received signal",
                            "Antenna or RF path issue",
                            "Distance or obstruction"
                        ],
                        [
                            "Verify the DUT and STA antenna connections.",
                            "Check placement and distance.",
                            "Repeat the RSSI measurement."
                        ]
                    )

                elif margin <= self.rssi_margin_db:
                    add(
                        "RSSI_NEAR_THRESHOLD", "WARNING",
                        [test_id],
                        "WiFi signal strength has limited margin.",
                        f"RSSI = {rssi} dBm; "
                        f"minimum = {min_rssi} dBm; "
                        f"margin = {margin:.1f} dB",
                        [
                            "Signal may fluctuate below the threshold",
                            "Limited RF link margin"
                        ],
                        [
                            "Repeat RSSI measurements over time.",
                            "Monitor signal stability and link performance.",
                            "Compare results under controlled RF conditions."
                        ]
                    )

            # TCP throughput validation (TC05 / TC06)
            if test_id in ("TC05", "TC06"):
                throughput = metrics.get("receiver_mbps")
                minimum = metrics.get("min_throughput_mbps")

                if not (
                    valid_number(throughput)
                    and valid_number(minimum)
                    and minimum > 0
                ):
                    if status == "PASS":
                        add(
                            "MISSING_TEST_METRIC", "WARNING",
                            [test_id],
                            "Required throughput metrics are missing or invalid.",
                            f"Throughput = {throughput}; "
                            f"threshold = {minimum}",
                            [
                                "iperf3 output may be incomplete",
                                "Throughput parser may have returned invalid data"
                            ],
                            [
                                "Inspect the original iperf3 JSON output.",
                                "Verify receiver throughput extraction.",
                                "Check the test profile threshold."
                            ]
                        )
                    continue

                if throughput < minimum:
                    add(
                        "THROUGHPUT_BELOW_THRESHOLD", "CRITICAL",
                        [test_id],
                        "TCP throughput is below the configured threshold.",
                        f"Throughput = {throughput:.2f} Mbps; "
                        f"minimum = {minimum:.2f} Mbps",
                        [
                            "Wireless link performance degradation",
                            "Network contention or retransmissions",
                            "DUT or STA processing limitations"
                        ],
                        [
                            "Repeat the iperf3 test.",
                            "Check TCP retransmissions and WiFi statistics.",
                            "Monitor system load and RF conditions."
                        ]
                    )

                elif throughput < minimum * self.throughput_margin_ratio:
                    add(
                        "THROUGHPUT_NEAR_THRESHOLD", "WARNING",
                        [test_id],
                        "TCP throughput passed with limited performance margin.",
                        f"Throughput = {throughput:.2f} Mbps; "
                        f"minimum = {minimum:.2f} Mbps; "
                        f"ratio = {throughput / minimum:.2f}",
                        [
                            "Performance margin may be insufficient",
                            "Throughput may vary under different conditions"
                        ],
                        [
                            "Repeat throughput testing across multiple runs.",
                            "Compare performance with historical baselines.",
                            "Monitor RSSI, retransmissions and channel utilization."
                        ]
                    )

        # --------------------------------
        # Cross-Test Correlation Analysis
        # --------------------------------

        by_id = {
            tc.get("test_id"): tc
            for tc in testcases
        }

        def get_metric(test_id, key):
            tc = by_id.get(test_id) or {}
            return (tc.get("metrics") or {}).get(key)

        # Rule 1:
        # Strong RSSI but high ping latency
        rssi = get_metric("TC04", "signal_dbm")

        if valid_number(rssi) and rssi >= -55:

            for ping_id in ("TC01", "TC02"):
                max_rtt = get_metric(
                    ping_id, "max_latency_ms"
                )

                if (
                    valid_number(max_rtt)
                    and max_rtt > self.high_latency_ms
                ):
                    add(
                        "STRONG_RSSI_HIGH_LATENCY",
                        "WARNING",
                        ["TC04", ping_id],
                        "High network latency detected despite strong WiFi signal.",
                        f"RSSI = {rssi} dBm; "
                        f"{ping_id} Maximum RTT = {max_rtt:.3f} ms",
                        [
                            "Wireless contention or airtime utilization",
                            "Network buffering or queueing",
                            "DUT or STA CPU scheduling delays",
                            "Other delays along the network path"
                        ],
                        [
                            "Monitor channel utilization and wireless retry counters.",
                            "Check DUT and STA CPU utilization.",
                            "Repeat ping tests with background traffic disabled.",
                            "Compare DUT and Control PC ping latency."
                        ]
                    )

        # Rule 2:
        # Packet loss and low throughput
        loss_ids = []

        for ping_id in ("TC01", "TC02"):
            loss = get_metric(
                ping_id, "packet_loss_percent"
            )

            if valid_number(loss) and loss > 0:
                loss_ids.append(ping_id)

        low_throughput_ids = []

        for throughput_id in ("TC05", "TC06"):
            throughput = get_metric(
                throughput_id, "receiver_mbps"
            )
            minimum = get_metric(
                throughput_id, "min_throughput_mbps"
            )

            if (
                valid_number(throughput)
                and valid_number(minimum)
                and minimum > 0
                and throughput < minimum
            ):
                low_throughput_ids.append(throughput_id)

        if loss_ids and low_throughput_ids:
            add(
                "PACKET_LOSS_LOW_THROUGHPUT",
                "WARNING",
                loss_ids + low_throughput_ids,
                "Packet loss and low TCP throughput detected in the same test run.",
                f"Packet loss tests: {', '.join(loss_ids)}; "
                f"Low throughput tests: {', '.join(low_throughput_ids)}",
                [
                    "Network congestion or packet delivery instability",
                    "Wireless interference or retransmissions",
                    "Routing, firewall or endpoint processing issues"
                ],
                [
                    "Compare ping and throughput results over multiple runs.",
                    "Inspect wireless interface and TCP retransmission statistics.",
                    "Check the DUT firewall and network routes.",
                    "Collect simultaneous ping and throughput measurements."
                ]
            )

        # Rule 3:
        # Throughput asymmetry with retransmissions
        upload = get_metric("TC05", "receiver_mbps")
        download = get_metric("TC06", "receiver_mbps")

        if (
            valid_number(upload)
            and valid_number(download)
            and upload > 0
            and download > 0
        ):
            ratio = max(upload, download) / min(upload, download)

            slower_id = "TC05" if upload < download else "TC06"
            slower_retransmits = get_metric(
                slower_id, "retransmits"
            )

            if (
                ratio >= self.throughput_ratio
                and valid_number(slower_retransmits)
                and slower_retransmits >= self.high_retransmits
            ):
                add(
                    "ASYMMETRY_WITH_RETRANSMITS",
                    "WARNING",
                    ["TC05", "TC06"],
                    "Throughput asymmetry accompanied by elevated TCP retransmissions.",
                    f"Upload = {upload:.1f} Mbps; "
                    f"Download = {download:.1f} Mbps; "
                    f"Ratio = {ratio:.2f}; "
                    f"{slower_id} Retransmits = {slower_retransmits}",
                    [
                        "Directional network congestion",
                        "Wireless transmission or reception differences",
                        "TCP loss recovery affecting throughput",
                        "DUT or STA processing bottlenecks"
                    ],
                    [
                        "Repeat both directions under comparable conditions.",
                        "Check TCP retransmissions and network interface errors.",
                        "Inspect wireless statistics at both endpoints.",
                        "Compare with historical throughput baselines."
                    ]
                )

        # --------------------------------
        # Environment / Execution Errors
        # --------------------------------

        if data.get("overall_status") == "ERROR":

            error_text = str(data.get("error") or "")
            error_lower = error_text.lower()

            error_rules = [
                {
                    "rule_id": "DUT_CONNECTION_ERROR",
                    "keywords": [
                        "mock dut connection failure",
                        "dut connection failed",
                        "telnet connection",
                        "failed to connect dut"
                    ],
                    "title": "DUT management connection failure detected.",
                    "causes": [
                        "DUT may be unreachable",
                        "Telnet service may not be available",
                        "Management IP or network configuration may be incorrect"
                    ],
                    "recommendations": [
                        "Ping the DUT management IP from the Control PC.",
                        "Check whether TCP port 23 is reachable.",
                        "Verify DUT IP configuration and Telnet service."
                    ]
                },
                {
                    "rule_id": "STA_CONNECTION_ERROR",
                    "keywords": [
                        "sta connection failed",
                        "ssh connection",
                        "failed to connect sta",
                        "golden sta connection"
                    ],
                    "title": "Golden STA management connection failure detected.",
                    "causes": [
                        "STA management network may be unavailable",
                        "SSH service may not be running",
                        "Authentication or SSH configuration may be incorrect"
                    ],
                    "recommendations": [
                        "Verify STA management IP connectivity.",
                        "Check SSH service and TCP port 22.",
                        "Confirm authentication configuration."
                    ]
                },
                {
                    "rule_id": "WIFI_CONNECTION_ERROR",
                    "keywords": [
                        "wifi connection failed",
                        "wifi not connected",
                        "failed to connect wifi",
                        "wrong dut radio",
                        "target bssid"
                    ],
                    "title": "Golden STA WiFi association or validation failed.",
                    "causes": [
                        "SSID or security configuration mismatch",
                        "Incorrect target BSSID",
                        "AP may not be available"
                    ],
                    "recommendations": [
                        "Verify DUT SSID, BSSID and WiFi security settings.",
                        "Inspect NetworkManager connection status.",
                        "Check DUT AP status and STA wireless logs."
                    ]
                },
                {
                    "rule_id": "NETWORK_ROUTE_ERROR",
                    "keywords": [
                        "wrong route",
                        "no route to host",
                        "network is unreachable",
                        "sta cannot reach"
                    ],
                    "title": "Network connectivity or routing failure detected.",
                    "causes": [
                        "Incorrect network route",
                        "Data interface may be unavailable",
                        "Destination may not be reachable"
                    ],
                    "recommendations": [
                        "Inspect ip route on the Golden STA.",
                        "Verify STA WiFi IP and destination IP.",
                        "Check connectivity between STA, DUT and Control PC."
                    ]
                },
                {
                    "rule_id": "FIREWALL_ERROR",
                    "keywords": [
                        "failed to configure dut firewall",
                        "firewall rule verification",
                        "iptables"
                    ],
                    "title": "DUT firewall preparation failure detected.",
                    "causes": [
                        "Firewall rule may not have been applied",
                        "iptables chain may be unavailable",
                        "DUT command execution may have failed"
                    ],
                    "recommendations": [
                        "Inspect DUT iptables rules.",
                        "Verify the expected source and destination IPs.",
                        "Confirm the required firewall chain exists."
                    ]
                },
                {
                    "rule_id": "IPERF_SERVICE_ERROR",
                    "keywords": [
                        "iperf3 server",
                        "failed to start iperf",
                        "address already in use",
                        "port 5201"
                    ],
                    "title": "iperf3 service failure detected.",
                    "causes": [
                        "Port 5201 may already be occupied",
                        "iperf3 process may have failed",
                        "Server configuration may be incorrect"
                    ],
                    "recommendations": [
                        "Check whether port 5201 is already in use.",
                        "Inspect the iperf3 server process.",
                        "Review service startup logs."
                    ]
                }
            ]

            matched = False

            for rule in error_rules:
                if any(
                    keyword in error_lower
                    for keyword in rule["keywords"]
                ):
                    matched = True

                    add(
                        rule["rule_id"],
                        "CRITICAL",
                        [],
                        rule["title"],
                        error_text,
                        rule["causes"],
                        rule["recommendations"]
                    )

            if "cleanup" in error_lower:
                matched = True

                add(
                    "CLEANUP_ERROR",
                    "WARNING",
                    [],
                    "Test environment cleanup failure detected.",
                    error_text,
                    [
                        "Connection shutdown may have failed",
                        "A test service may not have stopped cleanly"
                    ],
                    [
                        "Inspect SSH, Telnet and iperf3 cleanup logs.",
                        "Verify no stale iperf3 server remains.",
                        "Confirm environment readiness before the next run."
                    ]
                )

            if not matched:
                add(
                    "UNCLASSIFIED_EXECUTION_ERROR",
                    "WARNING",
                    [],
                    "Execution error requires further investigation.",
                    error_text or "No error details available.",
                    [
                        "The error does not match a known diagnostic rule"
                    ],
                    [
                        "Review run.log, dut.log and sta.log.",
                        "Identify the failing execution step.",
                        "Add a new diagnostic rule if the failure repeats."
                    ]
                )

        if not findings and data.get("overall_status") == "PASS":
            add(
                "NO_ANALYSIS_WARNINGS", "INFO", [],
                "No issues detected by the currently enabled analysis rules.",
                "All available metrics were checked against the configured analysis heuristics.",
                [],
                ["Continue collecting results for historical comparison."]
            )

        return {
            "run_id": data.get("run_id"),
            "test_status": data.get("overall_status"),
            "analysis_version": "W9-02-v1",
            "findings_count": len(findings),
            "findings": findings
        }

