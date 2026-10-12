from config.testbed import (
    DUT_IP,
    STA_MGMT_IP,
    STA_WIFI_INTERFACE,
)

from config.credentials import (
    STA_USERNAME,
    STA_PASSWORD,
)

from device.golden_sta import GoldenSTA
from testcase.connectivity import ConnectivityTest


def main():

    print("================================")
    print(" TC01 Connectivity Test")
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

        print("[2] Execute connectivity test")

        test = ConnectivityTest(
            sta=sta,
            destination=DUT_IP,
            test_id="TC01",
            name="STA to DUT Connectivity",
            ping_count=10,
            max_packet_loss_percent=1.0
        )

        result = test.run()

        print()
        print("Test Result")
        print("------------------------------")

        print(f"Test ID      : {result.test_id}")
        print(f"Name         : {result.name}")
        print(f"Result       : {result.status}")
        print(f"Message      : {result.message}")

        print(
            f"Packet Loss  : "
            f"{result.metrics['packet_loss_percent']}%"
        )

        print(
            f"Avg Latency  : "
            f"{result.metrics['avg_latency_ms']} ms"
        )

        print(
            f"Max Latency  : "
            f"{result.metrics['max_latency_ms']} ms"
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
