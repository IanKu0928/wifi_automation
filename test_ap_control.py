import time

from config.testbed import DUT_IP, DUT_WIFI_INTERFACE
from config.credentials import DUT_USERNAME, DUT_PASSWORD
from device.dut import DUT


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


dut = DUT(
    host=DUT_IP,
    username=DUT_USERNAME,
    password=DUT_PASSWORD
)

try:
    print("[1] Connect DUT")
    dut.connect()

    print("[2] Check initial AP status")

    if not dut.is_ap_enabled(DUT_WIFI_INTERFACE):
        raise RuntimeError(
            f"{DUT_WIFI_INTERFACE} is not enabled before test"
        )

    print(f"[PASS] {DUT_WIFI_INTERFACE} initial state = ENABLED")

    print(f"[3] Disable {DUT_WIFI_INTERFACE}")

    dut.disable_ap(DUT_WIFI_INTERFACE)

    if not wait_ap_state(
        dut,
        DUT_WIFI_INTERFACE,
        expected_enabled=False,
        timeout=10
    ):
        raise RuntimeError(
            f"{DUT_WIFI_INTERFACE} did not enter DISABLED state"
        )

    print(f"[PASS] {DUT_WIFI_INTERFACE} state = DISABLED")

    print(f"[4] Enable {DUT_WIFI_INTERFACE}")

    dut.enable_ap(DUT_WIFI_INTERFACE)

    if not wait_ap_state(
        dut,
        DUT_WIFI_INTERFACE,
        expected_enabled=True,
        timeout=10
    ):
        raise RuntimeError(
            f"{DUT_WIFI_INTERFACE} did not recover to ENABLED state"
        )

    print(f"[PASS] {DUT_WIFI_INTERFACE} state = ENABLED")

    print("[PASS] DUT AP Disable / Enable")

finally:
    dut.close()
