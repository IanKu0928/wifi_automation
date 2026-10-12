import subprocess
import time

from config.testbed import (
    DUT_IP,
    CONTROL_DATA_IP,
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


# ============================================================
# DUT helpers
# ============================================================

def ping_dut(ip):
    result = subprocess.run(
        [
            "ping",
            "-c", "1",
            "-W", "1",
            ip
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return result.returncode == 0


def wait_dut_down(ip, timeout=15):
    start = time.time()

    while time.time() - start < timeout:

        if not ping_dut(ip):
            elapsed = time.time() - start

            print(
                f"[PASS] DUT DOWN detected "
                f"after {elapsed:.1f}s"
            )

            return True

        time.sleep(1)

    return False


def wait_dut_up(ip, timeout=90):
    start = time.time()

    while time.time() - start < timeout:

        if ping_dut(ip):
            elapsed = time.time() - start

            print(
                f"[PASS] DUT network UP "
                f"after {elapsed:.1f}s"
            )

            return True

        time.sleep(1)

    return False


def wait_telnet_recovery(dut, timeout=30):
    start = time.time()

    while time.time() - start < timeout:

        try:
            dut.connect()
            return True

        except Exception:
            time.sleep(2)

    return False


def wait_ap_enabled(
    dut,
    interface="wlan0",
    timeout=30
):
    start = time.time()

    while time.time() - start < timeout:

        try:
            output = dut.get_ap_status(
                interface
            )

            if "state=ENABLED" in output:
                return True

        except Exception:
            pass

        time.sleep(1)

    return False


# ============================================================
# STA helpers
# ============================================================

def wait_sta_target_recovery(
    sta,
    expected_ssid,
    expected_bssid,
    timeout=15
):
    """
    Observe natural STA recovery.

    Do NOT issue nmcli connect here.
    """

    start = time.time()

    while time.time() - start < timeout:

        try:

            if sta.verify_wifi_connection(
                expected_ssid=expected_ssid,
                expected_bssid=expected_bssid
            ):
                wifi_ip = sta.get_wifi_ip()

                if wifi_ip:
                    elapsed = (
                        time.time() - start
                    )

                    return True, wifi_ip, elapsed

        except Exception:
            pass

        time.sleep(1)

    return False, None, None


def validate_sta_route(
    sta,
    destination
):
    result = sta.get_route(destination)

    output = result["stdout"]

    correct_interface = (
        f"dev {STA_WIFI_INTERFACE}"
        in output
    )

    if not correct_interface:
        print(
            "[FAIL] Unexpected STA route:"
        )
        print(output)

        return False

    return True


# ============================================================
# Test
# ============================================================

dut = DUT(
    host=DUT_IP,
    username=DUT_USERNAME,
    password=DUT_PASSWORD
)

sta = None


try:

    print("================================")
    print(" Full Reboot Recovery Test")
    print("================================")

    # --------------------------------------------------------
    # Initial DUT
    # --------------------------------------------------------

    print("[1] Connect DUT")

    dut.connect()

    print("[PASS] DUT connected")

    # --------------------------------------------------------
    # Discover target radio
    # --------------------------------------------------------

    print("[2] Discover DUT wlan0")

    radio = dut.get_radio_info("wlan0")

    target_ssid = radio["ssid"]
    target_bssid = radio["bssid"]

    print(
        f"Target SSID  : {target_ssid}"
    )

    print(
        f"Target BSSID : {target_bssid}"
    )

    print(
        f"Frequency    : "
        f"{radio['frequency_ghz']} GHz"
    )

    if not dut.is_ap_enabled("wlan0"):
        raise RuntimeError(
            "wlan0 is not ENABLED"
        )

    print("[PASS] DUT wlan0 ready")

    # --------------------------------------------------------
    # Connect Golden STA management
    # --------------------------------------------------------

    print("[3] Connect Golden STA management")

    sta = GoldenSTA(
        host=STA_MGMT_IP,
        username=STA_USERNAME,
        password=STA_PASSWORD,
        wifi_interface=STA_WIFI_INTERFACE,
        ssid=target_ssid
    )

    sta.connect()

    print("[PASS] STA management connected")

    # --------------------------------------------------------
    # Establish pre-reboot baseline
    # --------------------------------------------------------

    print(
        "[4] Prepare STA on target BSSID"
    )

    wifi_ip = sta.prepare_target_wifi(
        target_bssid
    )

    print(
        f"[PASS] STA baseline ready: "
        f"{wifi_ip}"
    )

    # Verify route before reboot

    if not validate_sta_route(
        sta,
        CONTROL_DATA_IP
    ):
        raise RuntimeError(
            "Invalid STA route before reboot"
        )

    print("[PASS] STA baseline route")

    # Verify STA -> DUT

    result = sta.ping(
        DUT_IP,
        count=3
    )

    if result["exit_code"] != 0:
        raise RuntimeError(
            "STA cannot ping DUT "
            "before reboot"
        )

    print("[PASS] STA -> DUT baseline")

    # --------------------------------------------------------
    # Reboot
    # --------------------------------------------------------

    print("[5] Reboot DUT")

    reboot_start = time.time()

    dut.reboot()

    print("[INFO] Reboot command sent")

    # --------------------------------------------------------
    # Detect DUT DOWN
    # --------------------------------------------------------

    print("[6] Wait DUT DOWN")

    if not wait_dut_down(
        DUT_IP,
        timeout=15
    ):
        raise RuntimeError(
            "DUT did not go DOWN"
        )

    # --------------------------------------------------------
    # Network recovery
    # --------------------------------------------------------

    print("[7] Wait DUT network recovery")

    if not wait_dut_up(
        DUT_IP,
        timeout=90
    ):
        raise RuntimeError(
            "DUT network did not recover"
        )

    network_time = (
        time.time() - reboot_start
    )

    print(
        f"[INFO] Reboot-to-network: "
        f"{network_time:.1f}s"
    )

    # --------------------------------------------------------
    # Telnet recovery
    # --------------------------------------------------------

    print("[8] Wait DUT Telnet recovery")

    if not wait_telnet_recovery(
        dut,
        timeout=30
    ):
        raise RuntimeError(
            "DUT Telnet did not recover"
        )

    telnet_time = (
        time.time() - reboot_start
    )

    print(
        f"[PASS] DUT Telnet recovered "
        f"after {telnet_time:.1f}s"
    )

    # Current DUT Telnet shell may need
    # stabilization immediately after boot.

    time.sleep(5)

    # --------------------------------------------------------
    # AP recovery
    # --------------------------------------------------------

    print("[9] Wait DUT wlan0 recovery")

    if not wait_ap_enabled(
        dut,
        interface="wlan0",
        timeout=30
    ):
        raise RuntimeError(
            "DUT wlan0 did not recover"
        )

    ap_time = (
        time.time() - reboot_start
    )

    print(
        f"[PASS] DUT wlan0 recovered "
        f"after {ap_time:.1f}s"
    )

    # --------------------------------------------------------
    # Verify radio identity
    # --------------------------------------------------------

    print("[10] Verify DUT radio identity")

    radio_after = dut.get_radio_info(
        "wlan0"
    )

    if (
        radio_after["ssid"]
        != target_ssid
    ):
        raise RuntimeError(
            "DUT SSID changed after reboot"
        )

    if (
        radio_after["bssid"]
        != target_bssid
    ):
        raise RuntimeError(
            "DUT BSSID changed after reboot"
        )

    print(
        "[PASS] DUT target radio recovered"
    )

    # --------------------------------------------------------
    # NATURAL STA RECOVERY
    # --------------------------------------------------------

    print(
        "[11] Observe STA natural recovery"
    )

    natural_ok, wifi_ip, natural_wait = (
        wait_sta_target_recovery(
            sta,
            expected_ssid=target_ssid,
            expected_bssid=target_bssid,
            timeout=15
        )
    )

    if natural_ok:

        sta_time = (
            time.time() - reboot_start
        )

        print(
            "[PASS] STA natural recovery"
        )

        print(
            f"[INFO] Natural recovery "
            f"observation: {natural_wait:.1f}s"
        )

        print(
            f"[INFO] Reboot-to-STA: "
            f"{sta_time:.1f}s"
        )

        recovery_mode = "NATURAL"

    else:

        print(
            "[WARN] STA natural recovery "
            "timeout"
        )

        # ----------------------------------------------------
        # FORCED STA RECOVERY
        # ----------------------------------------------------

        print(
            "[12] Force STA target recovery"
        )

        wifi_ip = sta.prepare_target_wifi(
            target_bssid
        )

        if not sta.verify_wifi_connection(
            expected_ssid=target_ssid,
            expected_bssid=target_bssid
        ):
            raise RuntimeError(
                "Forced STA recovery failed"
            )

        sta_time = (
            time.time() - reboot_start
        )

        print(
            "[PASS] Forced STA recovery"
        )

        print(
            f"[INFO] Reboot-to-STA: "
            f"{sta_time:.1f}s"
        )

        recovery_mode = "FORCED"

    # --------------------------------------------------------
    # DHCP verification
    # --------------------------------------------------------

    print("[13] Verify STA DHCP")

    if not wifi_ip:
        wifi_ip = sta.get_wifi_ip()

    if not wifi_ip:
        raise RuntimeError(
            "STA has no WiFi IP"
        )

    print(
        f"[PASS] STA WiFi IP: {wifi_ip}"
    )

    # --------------------------------------------------------
    # Route verification
    # --------------------------------------------------------

    print("[14] Verify STA data route")

    if not validate_sta_route(
        sta,
        CONTROL_DATA_IP
    ):
        raise RuntimeError(
            "STA data route did not recover"
        )

    print(
        f"[PASS] Route to "
        f"{CONTROL_DATA_IP} "
        f"uses {STA_WIFI_INTERFACE}"
    )

    # --------------------------------------------------------
    # STA -> DUT connectivity
    # --------------------------------------------------------

    print("[15] Verify STA -> DUT")

    result = sta.ping(
        DUT_IP,
        count=3
    )

    if result["exit_code"] != 0:

        print(result["stdout"])

        raise RuntimeError(
            "STA cannot ping DUT "
            "after recovery"
        )

    print("[PASS] STA -> DUT connectivity")

    # --------------------------------------------------------
    # Final verification
    # --------------------------------------------------------

    print("[16] Final target verification")

    if not sta.verify_wifi_connection(
        expected_ssid=target_ssid,
        expected_bssid=target_bssid
    ):
        raise RuntimeError(
            "STA final BSSID verification failed"
        )

    print("[PASS] STA final target BSSID")

    # --------------------------------------------------------
    # Restore temporary DUT firewall
    # --------------------------------------------------------

    print("[17] Restore DUT test firewall")

    current_wifi_ip = sta.get_wifi_ip()

    if not current_wifi_ip:
        raise RuntimeError(
            "Cannot get STA WiFi IP "
            "for firewall recovery"
        )

    print(
        f"[INFO] Current STA WiFi IP: "
        f"{current_wifi_ip}"
    )

    dut.prepare_test_firewall(
        sta_ip=current_wifi_ip,
        control_ip=CONTROL_DATA_IP
    )

    print(
        "[PASS] DUT test firewall restored"
    )

    # --------------------------------------------------------
    # STA -> Control connectivity
    # --------------------------------------------------------

    print("[18] Verify STA -> Control")

    result = sta.ping(
        CONTROL_DATA_IP,
        count=3
    )

    if result["exit_code"] != 0:

        print(result["stdout"])

        raise RuntimeError(
            "STA cannot reach Control PC "
            "after firewall recovery"
        )

    print(
        "[PASS] STA -> Control connectivity"
    )

    # --------------------------------------------------------
    # Final data path
    # --------------------------------------------------------

    print("[19] Final data-path verification")

    if not validate_sta_route(
        sta,
        CONTROL_DATA_IP
    ):
        raise RuntimeError(
            "Final STA data route is invalid"
        )

    print("[PASS] Final WiFi data path")

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("================================")
    print("[PASS] DUT CONTROL SMOKE TEST")
    print("================================")

    print(
        f"Network Recovery : "
        f"{network_time:.1f}s"
    )

    print(
        f"Telnet Recovery  : "
        f"{telnet_time:.1f}s"
    )

    print(
        f"AP Recovery      : "
        f"{ap_time:.1f}s"
    )

    print(
        f"STA Recovery     : "
        f"{sta_time:.1f}s"
    )

    print(
        f"Recovery Mode    : "
        f"{recovery_mode}"
    )

    print(
        f"STA WiFi IP      : "
        f"{wifi_ip}"
    )

    print(
        f"Target SSID      : "
        f"{target_ssid}"
    )

    print(
        f"Target BSSID     : "
        f"{target_bssid}"
    )

    print(
        "STA -> DUT       : PASS"
    )

    print(
        "STA -> Control   : PASS"
    )

    print(
        "Firewall Restore : PASS"
    )


finally:

    if sta:

        try:
            sta.close()
        except Exception:
            pass

    try:
        dut.close()
    except Exception:
        pass
