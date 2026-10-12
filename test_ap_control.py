import time

from config.testbed import DUT_IP
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

    if not dut.is_ap_enabled("wlan0"):
        raise RuntimeError(
            "wlan0 is not enabled before test"
        )

    print("[PASS] wlan0 initial state = ENABLED")

    print("[3] Disable wlan0")

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

    print("[PASS] wlan0 state = DISABLED")

    print("[4] Enable wlan0")

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

    print("[PASS] wlan0 state = ENABLED")

    print("[PASS] DUT AP Disable / Enable")

finally:
    dut.close()
