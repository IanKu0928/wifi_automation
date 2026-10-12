import time

from config.testbed import (
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


def wait_ap_state(
    dut,
    interface,
    expected_enabled,
    timeout=10
):
    start = time.time()

    while time.time() - start < timeout:

        enabled = dut.is_ap_enabled(interface)

        if enabled == expected_enabled:
            return True

        time.sleep(1)

    return False


def wait_sta_disconnected(sta, timeout=10):
    start = time.time()

    while time.time() - start < timeout:

        result = sta.get_wifi_status()

        if "Not connected" in result["stdout"]:
            return True

        time.sleep(1)

    return False


dut = DUT(
    host=DUT_IP,
    username=DUT_USERNAME,
    password=DUT_PASSWORD
)

sta = None

try:

    # --------------------------------
    # DUT
    # --------------------------------

    print("[1] Connect DUT")
    dut.connect()

    print("[2] Discover DUT wlan0")

    radio = dut.get_radio_info("wlan0")

    print(f"Target SSID  : {radio['ssid']}")
    print(f"Target BSSID : {radio['bssid']}")
    print(f"Frequency    : {radio['frequency_ghz']} GHz")

    if not dut.is_ap_enabled("wlan0"):
        raise RuntimeError(
            "wlan0 is not ENABLED before test"
        )

    print("[PASS] wlan0 initial state = ENABLED")

    # --------------------------------
    # Golden STA
    # --------------------------------

    print("[3] Connect Golden STA management")

    sta = GoldenSTA(
        host=STA_MGMT_IP,
        username=STA_USERNAME,
        password=STA_PASSWORD,
        wifi_interface=STA_WIFI_INTERFACE,
        ssid=radio["ssid"]
    )

    sta.connect()

    print("[4] Connect STA to target BSSID")

    wifi_ip = sta.prepare_target_wifi(
        radio["bssid"]
    )

    print(
        f"[PASS] STA connected to target BSSID "
        f"({wifi_ip})"
    )

    # --------------------------------
    # Disable AP
    # --------------------------------

    print("[5] Disable DUT wlan0")

    dut.disable_ap("wlan0")

    if not wait_ap_state(
        dut,
        "wlan0",
        expected_enabled=False,
        timeout=10
    ):
        raise RuntimeError(
            "wlan0 did not enter DISABLED state"
        )

    print("[PASS] DUT wlan0 = DISABLED")

    # --------------------------------
    # Verify STA disconnect
    # --------------------------------

    print("[6] Verify STA disconnected")

    if not wait_sta_disconnected(
        sta,
        timeout=10
    ):
        raise RuntimeError(
            "STA remained connected after AP disable"
        )

    print("[PASS] STA disconnected")

    # --------------------------------
    # Enable AP
    # --------------------------------

    print("[7] Enable DUT wlan0")

    dut.enable_ap("wlan0")

    if not wait_ap_state(
        dut,
        "wlan0",
        expected_enabled=True,
        timeout=10
    ):
        raise RuntimeError(
            "wlan0 did not recover to ENABLED state"
        )

    print("[PASS] DUT wlan0 = ENABLED")

    # --------------------------------
    # Reconnect target radio
    # --------------------------------

    print("[8] Reconnect STA to target BSSID")

    wifi_ip = sta.prepare_target_wifi(
        radio["bssid"]
    )

    # --------------------------------
    # Final verification
    # --------------------------------

    print("[9] Verify actual STA connection")

    if not sta.verify_wifi_connection(
        expected_ssid=radio["ssid"],
        expected_bssid=radio["bssid"]
    ):
        raise RuntimeError(
            "STA recovered to wrong radio"
        )

    print(
        "[PASS] STA recovered to target wlan0"
    )

    print(f"STA WiFi IP : {wifi_ip}")
    print(f"Target SSID : {radio['ssid']}")
    print(f"Target BSSID: {radio['bssid']}")

    print("==============================")
    print("[PASS] AP RECOVERY TEST")
    print("==============================")

finally:

    # Safety recovery:
    # Do not leave DUT wlan0 disabled
    try:
        if not dut.is_ap_enabled("wlan0"):
            print(
                "[RECOVERY] Re-enable DUT wlan0"
            )
            dut.enable_ap("wlan0")
    except Exception:
        pass

    if sta:
        sta.close()

    dut.close()
