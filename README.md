# WiFi Automation Framework

## Purpose and architecture

This framework validates a Realtek WiFi AP (the device under test, or DUT)
using a Linux Control PC and a Golden STA. The Control PC orchestrates tests,
collects results, and produces local JSON and HTML reports. Diagnostic analysis
uses predefined rules; it is not an LLM and does not call a cloud AI service.

```text
Control PC --- Telnet management ---> DUT (WiFi AP)
    |
    +--------- SSH management ------> Golden STA
    |                                    |
    +--------- iperf3 server <--- TCP ----+--- WiFi ---> DUT
```

Keep management access independent of the WiFi data path where practical.
The STA must reach the Control PC data IP through its configured WiFi interface.

| Test | Validation |
| --- | --- |
| TC01 | STA → DUT ping and packet loss |
| TC02 | STA → Control PC ping and packet loss |
| TC03 | Associated SSID and BSSID match the discovered DUT radio |
| TC04 | RSSI meets the configured minimum |
| TC05 | TCP upload from STA to Control PC |
| TC06 | TCP download from Control PC to STA |

## Tested environment and dependencies

These are the project's recorded tested versions, not a compatibility matrix
or a promise that package repositories will always supply identical versions.

| Component | Recorded environment |
| --- | --- |
| Control PC | Ubuntu 24.04.4 LTS; Python 3.12.3 |
| Control PC Python dependency | Paramiko 2.12.0, supplied by `python3-paramiko` |
| Control PC throughput tool | iperf3 3.16 |
| Golden STA | Ubuntu 20.04.6 LTS |
| Golden STA tools | NetworkManager 1.22.10, iw 5.4, iperf3 3.7, iproute2, iputils-ping, OpenSSH server |
| DUT | Realtek AP firmware exposing the expected Telnet shell and radio/firewall commands |

The Control PC imports Paramiko and Python's standard library, including
`telnetlib`. Python 3.12 includes the deprecated `telnetlib`; Python 3.13 removed
it and is unsupported by this implementation. The STA executes shell commands
through SSH and does not need the Control PC's Python packages.

Deployment uses Ubuntu apt packages. `requirements.txt` is a comments-only
reference, not a pip installation manifest; `pip install -r requirements.txt`
installs nothing. Use the system Python with the apt-provided Paramiko.
A virtual environment normally cannot see apt-installed Python modules and
requires separate dependency and compatibility validation.

## Installation

Obtain the repository and run Control PC commands from its root:

```bash
git clone https://github.com/IanKu0928/wifi_automation.git
cd wifi_automation
```

Review both installers before execution. They require `sudo`, `apt-get`,
package repository access, and the indicated Ubuntu release. The following
installation commands change systems and belong in an approved deployment
window; offline regression does not run them.

Control PC (Ubuntu 24.04):

```bash
bash -n install_control.sh
bash install_control.sh
```

`install_control.sh` runs `apt-get update` and installs `python3`,
`python3-paramiko`, `iperf3`, `iputils-ping`, `iproute2`, and `openssh-client`.
It verifies Python 3.12, imports Paramiko and telnetlib, prints Python/Paramiko
versions, and checks `iperf3`, `ping`, `ip`, and `ssh`. It does not run a
throughput test or install the framework as a service.

On the Golden STA (Ubuntu 20.04), copy and review `install_sta.sh`, then run:

```bash
bash -n install_sta.sh
bash install_sta.sh
```

This installs `network-manager`, `iw`, `iproute2`, `iputils-ping`, `iperf3`,
and `openssh-server`. It verifies commands, NetworkManager, and the SSH
service; missing/inactive critical dependencies cause a nonzero exit.
Installing NetworkManager or SSH packages may affect an existing remote
session. Review management access and service policy beforehand. The script
does not explicitly enable or restart services, but package installation
may start services through the package manager.

Both installers have offline syntax coverage. **Fresh-machine installation
has not been validated in Week 10 Phase 2.** Package provisioning does not
prove radio, routing, firewall, authentication, or throughput readiness.

## Local configuration and security

Create local copies only if they do not already exist. These commands preserve
existing files:

```bash
cp -n config/credentials.example.py config/credentials.py
cp -n config/testbed.example.py config/testbed.py
chmod 600 config/credentials.py config/testbed.py
```

Edit both local files before running preflight. Both are Git-ignored, and
neither should be committed or shared. The tracked examples contain placeholders.
Configuration files are executable Python: use only trusted local files.

| File | Variables to configure |
| --- | --- |
| `config/credentials.py` | `DUT_USERNAME`, `DUT_PASSWORD`, `STA_USERNAME`, `STA_PASSWORD` |
| `config/testbed.py` | `CONTROL_DATA_IP`, `DUT_IP`, `STA_MGMT_IP`, `DUT_WIFI_INTERFACE`, `STA_WIFI_INTERFACE`, `DUT_WIFI_SSID`, `DUT_WIFI_PASSWORD` |

Use IPv4 for `CONTROL_DATA_IP` and `DUT_IP`: STA address discovery and DUT
firewall preparation currently use IPv4. `STA_MGMT_IP` accepts IPv4 or IPv6
syntax because it is used for SSH management; IPv6 management still requires
separate hardware acceptance. Choose the correct management addresses and a
Control PC data address reachable through STA WiFi. Interface names must match the corresponding host;
preflight checks their syntax but cannot verify that remote interfaces exist.
The supported syntax is 1–15 ASCII letters, digits, `_`, `.`, `:`, `@`, or `-`,
excluding `.`/`..` and leading `-`, because existing remote commands interpolate
interface names into shell commands.

`run_test.py` discovers the actual SSID/BSSID from `DUT_WIFI_INTERFACE`; it does
not configure the AP from `DUT_WIFI_SSID`. Keep that reference SSID accurate.
Preflight accepts SSIDs of 1–32 UTF-8 bytes, including spaces and Unicode.
Remote shell handling of unusual SSIDs still requires hardware acceptance.

Set `DUT_WIFI_PASSWORD` to the actual WiFi password, or `""`/`None` for an open
network. Preflight does not impose WPA-specific password lengths or reject open
networks. Management usernames must be nonempty strings; management passwords
must be strings (an empty password is allowed syntactically). Valid syntax does
not establish successful authentication or a secure deployment policy.

Use restrictive permissions on both local files: `testbed.py` contains the WiFi
password. Preflight fails for group/other access to `credentials.py` and warns
for group/other access to `testbed.py`. It does not change file permissions.
Telnet transports management credentials without encryption; restrict it to an
isolated, trusted lab network. Paramiko currently accepts unknown SSH host keys;
verify the STA identity and management network through your lab procedures.
Review logs and reports before external sharing: they contain IP addresses,
SSID/BSSID, firmware, commands, and diagnostic evidence. Never paste credentials
into issue trackers, reports, profile names, or command-line arguments.

## Profiles and thresholds

| CLI profile | Configuration file | Recorded defaults: ping count / duration |
| --- | --- | --- |
| `smoke` | `config/smoke.json` | 5 pings / 5 seconds per throughput test |
| `default` | `config/test_profile.json` | 10 pings / 10 seconds |
| `performance` | `config/performance.json` | 20 pings / 30 seconds |

Each JSON file requires the following structure:

```json
{
  "profile_name": "smoke",
  "connectivity": {
    "ping_count": 5,
    "max_packet_loss_percent": 1.0
  },
  "wifi_signal": {"min_signal_dbm": -70},
  "throughput": {
    "duration_sec": 5,
    "upload_min_mbps": 30.0,
    "download_min_mbps": 30.0
  }
}
```

`profile_name` must be a nonempty string and is used in metadata/history grouping;
keep it consistent with the intended profile. Ping count and duration are positive
integers. Packet loss is numeric in [0, 100], RSSI in [-120, 0] dBm, and minimum
throughputs are nonnegative numeric Mbps. Booleans, NaN, and infinity are rejected.
Preflight and execution use the same profile validator. Unknown additional keys
are retained for compatibility. Choose limits appropriate to your test plan;
these limits affect test verdicts, while diagnostic rules provide separate advice.

## Offline preflight

```bash
python3 check_environment.py
```

The checker validates Ubuntu 24.04, Python 3.12, required Python imports and
commands, local configuration variables and types, IP syntax, interface/SSID
syntax, file permissions, all three profiles, and core framework files. It
suppresses local configuration output and reports validation failures without
printing credential values or Python source lines.

The summary uses PASS / FAIL / WARNING. Exit code 1 means a critical local check
failed; exit code 0 permits warnings. Address warnings before delivery.
**DUT/STA connectivity, credentials, remote interfaces/services, and hardware
configuration are NOT VERIFIED by preflight.** It does not connect to devices
or change network settings.

## Hardware execution

Only after preflight and explicit lab authorization, run one profile:

```bash
python3 run_test.py --profile smoke
python3 run_test.py --profile default
python3 run_test.py --profile performance
```

These are live hardware operations. Execution connects to DUT/STA, configures
STA BSSID/WiFi, prepares DUT firewall rules, and starts iperf3 traffic. Run one
DUT workflow at a time; unique Run Directories do not make shared-device tests
safe to execute concurrently. The commands above are alternatives, not a request
to run three simultaneous sessions.

- **PASS:** all recorded test cases passed their configured criteria.
- **FAIL:** one or more recorded test cases failed criteria.
- **ERROR:** setup, execution, interruption, or cleanup prevented a normal run.

Ctrl+C records ERROR and attempts applicable iperf3, STA, and DUT cleanup.
Completed results and cleanup errors remain in `result.json`. Cleanup closes
managed services/connections; it does not promise rollback of WiFi or firewall
changes. Execution/setup/cleanup errors and report-generation failures now
return exit code 1. A completed suite, including a test-criteria FAIL, returns
0; automation must read `overall_status` in `result.json` for the test verdict.

## Outputs and failure reporting

Each run reserves a new directory under `logs/` in the working directory:

```text
logs/YYYYMMDD_HHMMSS[_NNN]/
    result.json
    analysis.json
    report.html
    run.log
    dut.log    (when DUT commands were logged)
    sta.log    (when STA commands were logged)
```

The unsuffixed timestamp is allocated first; collisions use `_001`, `_002`,
and onward (at least three digits). Existing Run Directories are never reused.

`result.json` contains the original PASS/FAIL/ERROR verdict, metadata, timing,
completed test cases, and any execution/cleanup error. `analysis.json` contains
rule findings and historical comparison. `report.html` is a standalone view;
open it in a browser after the run. Possible causes are hypotheses, not confirmed
root causes. Analysis does not change test verdicts.

Missing, malformed, or invalid profile configuration now produces normal ERROR
reports once a logger/Run Directory exists, with zero completed test cases and
no device construction. Resource-construction errors use the same reporting path.
Configured passwords are redacted from exception messages. If `result.json`
cannot be written, the failure is logged, dependent reporting is skipped, and
execution returns 1. Analysis and HTML failures are logged independently;
HTML is still attempted after analysis failure. Check `run.log` for generation
failures rather than assuming that all output files exist.

Startup imports (including missing/broken local Python configuration or Python
dependencies), argument parsing, and Run Directory creation happen before this
reporting protection. They can fail without a report. Run preflight first; avoid
sharing raw startup tracebacks because Python may show configuration source lines.
Report generation also requires writable storage and cannot recover from every
filesystem or logging failure. Run from the repository root so output paths and
history discovery agree.

## Historical baseline comparison

Comparison requires at least three prior complete PASS runs with all six PASS
cases and matching profile name, DUT IP/firmware, radio interface, SSID, BSSID,
and frequency. FAIL, ERROR, incomplete, and differently grouped runs do not
enter the current run's comparison baseline. Each metric needs at least three
valid numeric samples; the baseline uses the median. Otherwise the comparison
reports `INSUFFICIENT_HISTORY` and does not claim a ready baseline.

Legacy and suffixed directory IDs are supported. Ordering uses
(timestamp, numeric suffix), with zero for the legacy timestamp. Self and later
allocations are excluded; earlier same-second allocations may be included if
complete and eligible. Suffixes express directory allocation order, not completion
order. No completion-time ordering or concurrent hardware safety is implied.
RF conditions and other variables absent from metadata can still affect
comparability. Do not edit historical production results to obtain a baseline.

## Offline regression and troubleshooting

Safe local regression commands (synthetic data, temporary output, mocked I/O):

```bash
bash -n install_control.sh
bash -n install_sta.sh
python3 test_w9_analysis_regression.py
python3 test_w9_html_regression.py
python3 test_run_error.py
python3 test_w10_interrupt_cleanup.py
python3 test_w10_full_cleanup.py
python3 test_w10_run_history.py
python3 test_w10_configuration.py
python3 test_w10_config_error.py
python3 check_environment.py
```

Offline regressions do not install packages or exercise the real AP/STA.
They do not replace real hardware acceptance, fresh-machine deployment tests,
or operational security review.

| Symptom | Next action |
| --- | --- |
| Missing local config | Create missing local copies from examples; retain existing files and fill in required values. |
| Config syntax/type/range failure | Review the named file locally against the examples and schema; never paste its secrets into reports. |
| Permission failure/warning | Review ownership and apply `chmod 600` to the two local configuration files. |
| Missing Python module/tool | Confirm system Python 3.12 and approved apt provisioning; avoid an unconfigured virtual environment. |
| Unsupported OS/Python | Use the recorded supported Control PC environment; Python 3.13 needs a separate Telnet migration. |
| ERROR report | Inspect `error` and `run.log`; determine whether setup, interruption, or cleanup failed. |
| Missing analysis/HTML | Inspect report-generation errors in `run.log` and check storage permissions/capacity. |
| Insufficient history | Collect three complete, comparable prior PASS runs; do not mix firmware, profiles, or radios. |
| Live authentication/routing/throughput failure | Under separate lab approval, verify management access, STA interface/profile, WiFi route, DUT-specific firewall behavior, and iperf3 compatibility. |

## Known limitations and handover status

Week 9 provides rule-based analysis and historical diagnostics. Week 10 Phase 1
adds Run ID protection and interruption/cleanup regressions. Phase 2 hardens
static deployment checks, local configuration validation, early ERROR reporting,
and documentation. No hardware acceptance or fresh-machine installation was
performed as part of these offline phases.

The framework assumes a compatible Realtek shell/firmware, IPv4 data path,
NetworkManager-managed STA, an existing connection profile suitable for BSSID
selection, and the documented credentials/interface settings. Open-network
handling is supported in configuration but must be validated on the target lab.
Intermittent STA-to-DUT packet loss has previously been observed; its cause is
unconfirmed. Further hardware operations require separate lab authorization.

### DUT Firmware Image Requirements and Limitations

Telnet must be enabled in the DUT firmware image and accessible from the
Control PC on TCP port 23. An image without an accessible Telnet shell cannot
complete this framework's DUT management and automated preparation workflow.
SSH-only images are not supported by the current DUT client.

Valid Telnet credentials are required in local `config/credentials.py` as
`DUT_USERNAME` and `DUT_PASSWORD`. **Passwordless login is NOT a requirement.**
Use the credentials accepted by the image; accepting an empty password in local
validation does not establish that passwordless authentication works.
The current client expects `login:` and `Password:` prompts, sends ASCII
credentials, and uses fixed command waits. Alternate prompts, interactive menus,
MFA, slow responses, or a restricted CLI require separate client adaptation.
The client prints “Connected” without independently verifying authentication;
a successful shell command is needed to establish usable access.

The Telnet account needs a shell with permission to read device/radio state and
modify the test firewall chain. Root or equivalent directly granted privileges
are needed for privileged commands; the framework does not invoke `sudo` or
answer privilege-escalation prompts. Firmware must expose these commands and
compatible output formats (examples below document behavior; do not run them
as part of offline preparation):

| Scope | DUT commands and required access |
| --- | --- |
| Device information | `cat /etc/version`, `ifconfig br0`: readable version file and bridge state. |
| Radio discovery | `iwconfig <DUT_WIFI_INTERFACE>`: readable radio state with `ESSID:"..."`, `Access Point: <MAC>`, and `Frequency:<number> GHz` fields. |
| Firewall inspection | `iptables -L wifi_nosecurity_access -n -v --line-numbers` and `iptables -C wifi_nosecurity_access -s <STA_WIFI_IP> -d <CONTROL_DATA_IP> -j ACCEPT`. |
| Firewall preparation | `iptables -I wifi_nosecurity_access 1 -s <STA_WIFI_IP> -d <CONTROL_DATA_IP> -j ACCEPT`: permission to modify the existing IPv4 chain; it must be connected to the applicable forwarding path. |
| Optional legacy AP/recovery scripts | `hostapd_cli -i <DUT_WIFI_INTERFACE> status`, `disable`, `enable`; access to the hostapd control socket, compatible `state=ENABLED` output, and permission to change AP state. |
| Optional legacy reboot scripts | `reboot`, `cat /proc/uptime`: reboot privilege and readable uptime; these scripts interrupt service. |

The standard six-case profiles do not require AP disable/enable or reboot.
Interface names, bridge name, firewall chain, utilities, and radio output are
firmware-specific assumptions. Images missing these interfaces/commands or
using incompatible output need adaptation and new acceptance testing.
Telnet command execution does not reliably capture shell exit codes; firewall
preparation checks listed rules instead. Closing a run does not remove inserted
firewall rules or restore previous WiFi settings. Review persistent lab changes
under the lab's operating procedure.

Restrict Telnet to an isolated trusted test network because credentials and
commands travel without encryption.

### Week 10 hardware acceptance record

The final hardware acceptance supplied for this delivery completed successfully:

| Profile | Result | Framework exit code | Artifacts |
| --- | --- | --- | --- |
| smoke | 6/6 PASS | 0 | Valid `result.json`, `analysis.json`, `report.html` |
| default | 6/6 PASS | 0 | Valid `result.json`, `analysis.json`, `report.html` |
| performance | 6/6 PASS | 0 | Valid `result.json`, `analysis.json`, `report.html` |

No residual iperf3 server process was detected after acceptance. These results
apply to the accepted lab image and setup; they do not establish compatibility
with other firmware images or fresh-machine installation. Final delivery
preparation uses offline checks only and does not repeat hardware operations.

Legacy `test_*.py` scripts include live device operations at module scope.
Do not use blanket test discovery/imports for offline validation; run only the
explicit offline regression list above. Legacy credential imports were audited:
management credentials belong in `config.credentials`, while topology and WiFi
settings belong in `config.testbed`. `test_sta.py` now uses those local modules
instead of embedded STA credentials and addresses.
