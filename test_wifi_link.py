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
from testcase.wifi_link import WiFiLinkTest


def main():

    print("================================")
    print(" TC03 WiFi Link Test")
    print("================================")

    dut = DUT(
        host=DUT_IP,
        username=DUT_USERNAME,
        password=DUT_PASSWORD
    )

    sta = None

    try:

        print("[1] Connect DUT")

        dut.connect()

        print("[PASS] DUT management connection")

        print("[2] Discover DUT wlan0")

        radio = dut.get_radio_info("wlan0")

        print(f"Expected SSID  : {radio['ssid']}")
        print(f"Expected BSSID : {radio['bssid']}")

        print("[3] Connect Golden STA")

        sta = GoldenSTA(
            host=STA_MGMT_IP,
            username=STA_USERNAME,
            password=STA_PASSWORD,
            wifi_interface=STA_WIFI_INTERFACE,
            ssid=radio["ssid"]
        )

        sta.connect()

        print("[PASS] STA management connection")

        print("[4] Execute WiFi link test")

        test = WiFiLinkTest(
            sta=sta,
            expected_ssid=radio["ssid"],
            expected_bssid=radio["bssid"]
        )

        result = test.run()

        print()
        print("Test Result")
        print("------------------------------")

        print(f"Test ID        : {result.test_id}")
        print(f"Name           : {result.name}")
        print(f"Result         : {result.status}")
        print(f"Message        : {result.message}")

        print(
            f"Expected SSID  : "
            f"{result.metrics['expected_ssid']}"
        )

        print(
            f"Actual SSID    : "
            f"{result.metrics['actual_ssid']}"
        )

        print(
            f"Expected BSSID : "
            f"{result.metrics['expected_bssid']}"
        )

        print(
            f"Actual BSSID   : "
            f"{result.metrics['actual_bssid']}"
        )

        print("------------------------------")

        if not result.passed:
            raise RuntimeError(
                f"{result.test_id} FAILED"
            )

        print(
            f"[PASS] {result.test_id} "
            f"{result.name}"
        )

    finally:

        if sta:
            sta.close()

        dut.close()


if __name__ == "__main__":
    main()
