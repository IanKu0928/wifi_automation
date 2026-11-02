from config.testbed import (
    DUT_WIFI_INTERFACE,
    CONTROL_DATA_IP,
    DUT_IP,
    STA_MGMT_IP,
    STA_WIFI_INTERFACE,
)

from config.credentials import (
    DUT_USERNAME,
    DUT_PASSWORD,
    STA_USERNAME,
    STA_PASSWORD,
)

from device.dut import DUT
from device.golden_sta import GoldenSTA
from library.logger import TestLogger

from testcase.connectivity import ConnectivityTest
from testcase.runner import TestRunner
from testcase.wifi_link import WiFiLinkTest
from testcase.wifi_signal import WiFiSignalTest
from testcase.throughput import ThroughputTest

import os
import argparse
from pathlib import Path

import time
from datetime import datetime

from library.result_writer import write_result_json
from library.iperf_server import IperfServer
from library.config_loader import ConfigLoader
from library.html_report import generate_html_report
from library.analysis_writer import generate_analysis_json

def parse_args():

    parser = argparse.ArgumentParser(
        description="WiFi Automation Framework"
    )

    parser.add_argument(
        "--profile",
        choices=["default", "smoke", "performance"],
        default="default",
        help="Select test profile (default: default)"
    )

    return parser.parse_args()

def main():

    args = parse_args()

    profile_files = {
        "default": "test_profile.json",
        "smoke": "smoke.json",
        "performance": "performance.json"
    }

    config_path = (
        Path(__file__).resolve().parent
        / "config"
        / profile_files[args.profile]
    )

    logger = TestLogger()

    run_start_monotonic = time.monotonic()
    run_start_time = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    config = ConfigLoader(config_path).load()

    logger.info(
        f"Test Profile: {config['profile_name']}"
    )

    metadata = {
    "profile": config["profile_name"],
        "dut": {
            "ip": DUT_IP,
            "version": None
        },
            "wifi": {
            "interface": None,
            "ssid": None,
            "bssid": None,
            "frequency_ghz": None
        },
        "sta": {
            "management_ip": STA_MGMT_IP,
            "wifi_ip": None,
            "wifi_interface": STA_WIFI_INTERFACE
        },
        "control": {
            "data_ip": CONTROL_DATA_IP
        }
    }

    iperf_server = IperfServer()

    logger.info("================================")
    logger.info(" WiFi Automation Framework")
    logger.info("================================")
    logger.info(f"Run ID: {logger.run_id}")

    dut = DUT(
        host=DUT_IP,
        username=DUT_USERNAME,
        password=DUT_PASSWORD,
        logger=logger
    )

    runner = None
    sta = None
    run_error = None

    try:

        # --------------------------------
        # DUT Management
        # --------------------------------

        logger.info("[1] Connect DUT")

        dut.connect()

        logger.pass_result(
            "DUT management connection"
        )

        # --------------------------------
        # DUT Information
        # --------------------------------

        logger.info("[2] Get DUT Version")

        version = dut.get_version()

        version_lines = [
            line.strip()
            for line in version.splitlines()
            if line.strip()
            and line.strip() != "#"
            and line.strip() != "cat /etc/version"
        ]

        if not version_lines:
            raise RuntimeError(
                "Failed to parse DUT firmware version"
            )

        metadata["dut"]["version"] = version_lines[0]

        logger.info(
            f"DUT Firmware Version: {metadata['dut']['version']}"
        )


        # --------------------------------
        # DUT Radio Discovery
        # --------------------------------

        logger.info("[3] Discover DUT Radio")

        radio = dut.get_radio_info(DUT_WIFI_INTERFACE)

        metadata["wifi"].update({
            "interface": radio["interface"],
            "ssid": radio["ssid"],
            "bssid": radio["bssid"],
            "frequency_ghz": radio["frequency_ghz"]
        })

        logger.info(
            f"DUT radio interface : {radio['interface']}"
        )

        logger.info(
            f"DUT radio SSID      : {radio['ssid']}"
        )

        logger.info(
            f"DUT radio BSSID     : {radio['bssid']}"
        )

        logger.info(
            f"DUT radio frequency : "
            f"{radio['frequency_ghz']} GHz"
        )

        logger.pass_result(
            "DUT radio discovery"
        )

        # --------------------------------
        # Create Golden STA
        # --------------------------------

        sta = GoldenSTA(
            host=STA_MGMT_IP,
            username=STA_USERNAME,
            password=STA_PASSWORD,
            wifi_interface=STA_WIFI_INTERFACE,
            ssid=radio["ssid"],
            logger=logger
        )

        # --------------------------------
        # STA Management
        # --------------------------------

        logger.info("[4] Connect Golden STA")

        sta.connect()

        logger.pass_result(
            "STA management connection"
        )

        # --------------------------------
        # Configure Target BSSID
        # --------------------------------

        logger.info("[5] Configure Target BSSID")

        result = sta.set_wifi_bssid(
            radio["bssid"]
        )

        if result["exit_code"] != 0:
            raise RuntimeError(
                "Failed to configure target BSSID: "
                f"{result['stderr']}"
            )

        result = sta.get_configured_bssid()

        configured_bssid = (
            result["stdout"]
            .strip()
            .lower()
            .replace("\\:", ":")
        )

        logger.info(
            f"Target BSSID     : {radio['bssid']}"
        )

        logger.info(
            f"Configured BSSID : {configured_bssid}"
        )

        if configured_bssid != radio["bssid"]:
            raise RuntimeError(
                "Configured BSSID does not match "
                "DUT target radio"
            )

        logger.pass_result(
            "STA target BSSID configuration"
        )

        # --------------------------------
        # Prepare WiFi
        # --------------------------------

        logger.info("[6] Prepare STA WiFi")

        wifi_ip = sta.prepare_wifi()

        metadata["sta"]["wifi_ip"] = wifi_ip

        # Verify actual AP, not only SSID
        matched = sta.verify_wifi_connection(
            expected_ssid=radio["ssid"],
            expected_bssid=radio["bssid"]
        )

        if not matched:
            raise RuntimeError(
                "STA connected to wrong DUT radio"
            )

        logger.pass_result(
            f"STA WiFi connected to target radio: "
            f"{wifi_ip}"
        )

        # --------------------------------
        # Validate Route
        # --------------------------------

        logger.info("[7] Validate Data Route")

        route = sta.get_route(
            CONTROL_DATA_IP
        )

        expected = (
            f"dev {STA_WIFI_INTERFACE}"
        )

        if expected not in route["stdout"]:
            raise RuntimeError(
                f"Wrong route to {CONTROL_DATA_IP}: "
                f"expected {STA_WIFI_INTERFACE}"
            )

        logger.pass_result(
            "STA data route"
        )

        # --------------------------------
        # Ping DUT
        # --------------------------------

        logger.info("[8] Ping DUT")

        ping_dut = sta.ping(DUT_IP)

        if ping_dut["exit_code"] != 0:
            raise RuntimeError(
                "STA cannot reach DUT"
            )

        logger.pass_result(
            "STA -> DUT connectivity"
        )

        # --------------------------------
        # DUT Firewall
        # --------------------------------

        logger.info(
            "[9] Prepare DUT Firewall"
        )

        dut.prepare_test_firewall(
            sta_ip=wifi_ip,
            control_ip=CONTROL_DATA_IP
        )

        logger.pass_result(
            "DUT firewall preparation"
        )

        # --------------------------------
        # Ping Control
        # --------------------------------

        logger.info(
            "[10] Ping Control PC"
        )

        ping_control = sta.ping(
            CONTROL_DATA_IP
        )

        if ping_control["exit_code"] != 0:
            raise RuntimeError(
                "STA cannot reach Control PC"
            )

        logger.pass_result(
            "STA -> Control connectivity"
        )

        # --------------------------------
        # Final Result
        # --------------------------------

        logger.info(
            "================================"
        )

        logger.pass_result(
            "ENVIRONMENT READY"
        )

        logger.info(
            "================================"
        )

        logger.info(
            f"STA WiFi IP : {wifi_ip}"
        )

        logger.info(
            f"DUT IP      : {DUT_IP}"
        )

        logger.info(
            f"Control IP  : {CONTROL_DATA_IP}"
        )

        logger.info(
            f"Target SSID : {radio['ssid']}"
        )

        logger.info(
            f"Target BSSID: {radio['bssid']}"
        )

        logger.info(
            "================================"
        )
        logger.info(
            " Prepare Test Services"
        )
        logger.info(
            "================================"
        )

        logger.info(
            "[SERVICE] Start iperf3 server"
        )

        iperf_server.start()

        logger.pass_result(
            "iperf3 server ready"
        )

        # --------------------------------
        # Execute Test Cases
        # --------------------------------

        logger.info(
            "================================"
        )
        
        logger.info(
            " Execute Test Cases"
        )

        logger.info(
            "================================"
        )

        runner = TestRunner(
            logger=logger
        )

        tc01 = ConnectivityTest(
            sta=sta,
            destination=DUT_IP,
            test_id="TC01",
            name="STA to DUT Connectivity",
            ping_count=config["connectivity"]["ping_count"],
            max_packet_loss_percent=config["connectivity"]["max_packet_loss_percent"]
        )

        tc02 = ConnectivityTest(
            sta=sta,
            destination=CONTROL_DATA_IP,
            test_id="TC02",
            name="STA to Control Connectivity",
            ping_count=config["connectivity"]["ping_count"],
            max_packet_loss_percent=config["connectivity"]["max_packet_loss_percent"]
        )
 
        tc03 = WiFiLinkTest(
            sta=sta,
            expected_ssid=radio["ssid"],
            expected_bssid=radio["bssid"],
            test_id="TC03",
            name="WiFi Target Radio Validation"
        )

        tc04 = WiFiSignalTest(
            sta=sta,
            test_id="TC04",
            name="WiFi Signal Validation",
            min_signal_dbm=config["wifi_signal"]["min_signal_dbm"]
        )

        tc05 = ThroughputTest(
            sta=sta,
            server_ip=CONTROL_DATA_IP,
            test_id="TC05",
            name="WiFi TCP Upload Throughput",
            duration=config["throughput"]["duration_sec"],
            min_throughput_mbps=config["throughput"]["upload_min_mbps"],
            reverse=False
        )

        tc06 = ThroughputTest(
            sta=sta,
            server_ip=CONTROL_DATA_IP,
            test_id="TC06",
            name="WiFi TCP Download Throughput",
            duration=config["throughput"]["duration_sec"],
            min_throughput_mbps=config["throughput"]["download_min_mbps"],
            reverse=True
        )

        runner.run_test(tc01)
        runner.run_test(tc02)
        runner.run_test(tc03)
        runner.run_test(tc04)
        runner.run_test(tc05)
        runner.run_test(tc06)

        overall_pass = runner.print_summary()

        logger.info(
            "================================"
        )

        if overall_pass:
            logger.pass_result(
                "TEST SUITE PASSED"
            )
        else:
            logger.fail_result(
                "TEST SUITE FAILED"
            )

        logger.info(
            "================================"
        )

    except Exception as e:

        run_error = f"{type(e).__name__}: {e}"

        logger.info(
            "================================"
        )

        logger.fail_result(
            "ENVIRONMENT NOT READY"
        )

        logger.fail_result(
            f"Error: {e}"
        )

        logger.info(
            "================================"
        )

    finally:

        cleanup_errors = []

        try:
            iperf_server.stop()
        except Exception as e:
            cleanup_errors.append(
                f"iperf3 cleanup: {type(e).__name__}: {e}"
            )

        if sta is not None:
            try:
                sta.close()
            except Exception as e:
                cleanup_errors.append(
                    f"STA cleanup: {type(e).__name__}: {e}"
                )

        try:
            dut.close()
        except Exception as e:
            cleanup_errors.append(
                f"DUT cleanup: {type(e).__name__}: {e}"
            )

        for cleanup_error in cleanup_errors:
            logger.fail_result(
                f"Cleanup error: {cleanup_error}"
            )

        errors = []

        if run_error is not None:
            errors.append(run_error)

        errors.extend(cleanup_errors)

        final_error = (
            "; ".join(errors)
            if errors
            else None
        )

        run_end_time = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )

        run_duration_sec = round(
            time.monotonic() - run_start_monotonic,
            3
        )

        timing = {
            "start_time": run_start_time,
            "end_time": run_end_time,
            "duration_sec": run_duration_sec
        }

        result_file = os.path.join(
            logger.run_dir,
            "result.json"
        )

        write_result_json(
            file_path=result_file,
            run_id=logger.run_id,
            results=runner.results if runner else [],
            metadata=metadata,
            timing=timing,
            error=final_error
        )

        # --------------------------------
        # Week 9: Rule-based Analysis
        # --------------------------------
        try:
            analysis_file = generate_analysis_json(
                result_path=result_file,
                log_dir=str(
                    Path(__file__).resolve().parent / "logs"
                ),
                min_samples=3
            )

            logger.info(
                f"Analysis JSON: {analysis_file}"
            )

        except Exception as e:
            logger.fail_result(
                f"Analysis JSON Generation Failed: "
                f"{type(e).__name__}: {e}"
            )

        # --------------------------------
        # Week 8: HTML Report
        # --------------------------------

        try:
            html_file = generate_html_report(result_file)

            logger.info(
                f"HTML Report: {html_file}"
            )

        except Exception as e:
            logger.fail_result(
                f"HTML Report Generation Failed: {e}"
            )

        logger.info(
            f"Result JSON: {result_file}"
        )

        logger.info(
            f"Total Execution Duration: "
            f"{run_duration_sec:.3f} sec"
        )

        logger.info(
            f"Log directory: {logger.run_dir}"
        )

if __name__ == "__main__":
    main()
