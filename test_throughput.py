from config.testbed import (
    CONTROL_DATA_IP,
    STA_MGMT_IP,
    STA_WIFI_INTERFACE,
)

from config.credentials import (
    STA_USERNAME,
    STA_PASSWORD,
)

from device.golden_sta import GoldenSTA
from testcase.throughput import ThroughputTest


def main():

    print("================================")
    print(" TC05 Throughput Test")
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

        print("[2] Execute throughput test")

        test = ThroughputTest(
            sta=sta,
            server_ip=CONTROL_DATA_IP,
            min_throughput_mbps=30.0
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
            f"Sender        : "
            f"{result.metrics['sender_mbps']:.1f} Mbps"
        )

        print(
            f"Receiver      : "
            f"{result.metrics['receiver_mbps']:.1f} Mbps"
        )

        print(
            f"Retransmits   : "
            f"{result.metrics['retransmits']}"
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
