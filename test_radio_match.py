from config.testbed import (
    DUT_WIFI_INTERFACE,
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


dut = DUT(
    host=DUT_IP,
    username=DUT_USERNAME,
    password=DUT_PASSWORD
)

sta = None

try:
    print("[1] Connect DUT")
    dut.connect()

    print(f"[2] Get DUT {DUT_WIFI_INTERFACE} information")
    radio = dut.get_radio_info(DUT_WIFI_INTERFACE)

    print(f"DUT SSID      : {radio['ssid']}")
    print(f"DUT BSSID     : {radio['bssid']}")
    print(f"DUT Frequency : {radio['frequency_ghz']} GHz")

    print("[3] Create Golden STA using DUT SSID")

    sta = GoldenSTA(
        host=STA_MGMT_IP,
        username=STA_USERNAME,
        password=STA_PASSWORD,
        wifi_interface=STA_WIFI_INTERFACE,
        ssid=radio["ssid"],
    )

    print("[4] Connect Golden STA management")
    sta.connect()

    print("[5] Configure target BSSID")
    result = sta.set_wifi_bssid(radio["bssid"])

    if result["exit_code"] != 0:
        raise RuntimeError(
            f"Failed to configure BSSID: {result['stderr']}"
        )

    print(f"Target BSSID : {radio['bssid']}")

    print("[6] Verify configured BSSID")
    result = sta.get_configured_bssid()

    configured_bssid = (
        result["stdout"]
        .strip()
        .lower()
        .replace("\\:", ":")
    )

    print(f"Configured BSSID : {configured_bssid}")

    if configured_bssid != radio["bssid"]:
        raise RuntimeError(
            f"Configured BSSID does not match DUT {DUT_WIFI_INTERFACE}"
        )

    print("[PASS] BSSID configuration")

    print("[7] Prepare STA WiFi")
    wifi_ip = sta.prepare_wifi()

    print(f"STA WiFi IP : {wifi_ip}")

    print("[8] Verify actual WiFi connection")

    matched = sta.verify_wifi_connection(
        expected_ssid=radio["ssid"],
        expected_bssid=radio["bssid"]
    )

    if not matched:
        raise RuntimeError(
            f"Golden STA is not connected to DUT {DUT_WIFI_INTERFACE}"
        )

    print(f"[PASS] Golden STA is connected to DUT {DUT_WIFI_INTERFACE}")

finally:
    if sta:
        sta.close()

    dut.close()
