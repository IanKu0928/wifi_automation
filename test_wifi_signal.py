from config.testbed import (
    STA_MGMT_IP,
    STA_WIFI_INTERFACE,
)

from config.credentials import (
    STA_USERNAME,
    STA_PASSWORD,
)

from device.golden_sta import GoldenSTA
from testcase.wifi_signal import WiFiSignalTest


def main():

    print("================================")
    print(" TC04 WiFi Signal Test")
    print("================================")

    sta = GoldenSTA(
        host=STA_MGMT_IP,
        username=STA_USERNAME,
        password=STA_PASSWORD,
        wifi_interface=STA_WIFI_INTERFACE
    )

    try:

        print("[1] Connect Golden STA")

        sta.connect()

        print("[PASS] STA management connection")

        print("[2] Execute WiFi signal test")

        test = WiFiSignalTest(
            sta=sta,
            test_id="TC04",
            name="WiFi Signal Validation",
            min_signal_dbm=-70
        )

        result = test.run()

        print()
        print("Test Result")
        print("------------------------------")

        print(f"Test ID       : {result.test_id}")
        print(f"Name          : {result.name}")
        print(f"Result        : {result.status}")
        print(f"Message       : {result.message}")

        print(
            f"Signal        : "
            f"{result.metrics['signal_dbm']} dBm"
        )

        print(
            f"Minimum Signal: "
            f"{result.metrics['min_signal_dbm']} dBm"
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
        sta.close()


if __name__ == "__main__":
    main()
