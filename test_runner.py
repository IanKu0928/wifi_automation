from config.testbed import (
    DUT_IP,
    CONTROL_DATA_IP,
    STA_MGMT_IP,
    STA_WIFI_INTERFACE,
)

from config.credentials import (
    STA_USERNAME,
    STA_PASSWORD,
)

from device.golden_sta import GoldenSTA
from testcase.connectivity import ConnectivityTest
from testcase.runner import TestRunner


def main():

    print("================================")
    print(" Connectivity Test Runner")
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

        runner = TestRunner()

        print()
        print("[2] Execute Test Cases")

        tc01 = ConnectivityTest(
            sta=sta,
            destination=DUT_IP,
            test_id="TC01",
            name="STA to DUT Connectivity",
            ping_count=10,
            max_packet_loss_percent=1.0
        )

        tc02 = ConnectivityTest(
            sta=sta,
            destination=CONTROL_DATA_IP,
            test_id="TC02",
            name="STA to Control Connectivity",
            ping_count=10,
            max_packet_loss_percent=1.0
        )

        runner.run_test(tc01)
        runner.run_test(tc02)

        overall_pass = runner.print_summary()

        if overall_pass:
            print()
            print("[PASS] ALL TEST CASES PASSED")
        else:
            print()
            print("[FAIL] TEST SUITE FAILED")

    finally:
        sta.close()


if __name__ == "__main__":
    main()
