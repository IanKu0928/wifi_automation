import subprocess
import time

from config.testbed import DUT_IP
from config.credentials import DUT_USERNAME, DUT_PASSWORD
from device.dut import DUT


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
            return True

        time.sleep(1)

    return False


def wait_dut_up(ip, timeout=90):
    start = time.time()

    while time.time() - start < timeout:

        if ping_dut(ip):
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


def wait_ap_enabled(dut, interface="wlan0", timeout=30):
    print(
        f"[WAIT] Waiting for {interface} AP recovery"
    )

    start = time.time()

    while time.time() - start < timeout:

        try:
            output = dut.get_ap_status(interface)

            if "state=ENABLED" in output:
                elapsed = time.time() - start

                print(
                    f"[PASS] {interface} AP ENABLED "
                    f"after {elapsed:.1f}s"
                )

                return True

        except Exception:
            pass

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

    # --------------------------------
    # Baseline
    # --------------------------------

    print("[2] Discover radio before reboot")

    radio_before = dut.get_radio_info("wlan0")

    print(
        f"SSID      : {radio_before['ssid']}"
    )
    print(
        f"BSSID     : {radio_before['bssid']}"
    )
    print(
        f"Frequency : "
        f"{radio_before['frequency_ghz']} GHz"
    )

    if not dut.is_ap_enabled("wlan0"):
        raise RuntimeError(
            "wlan0 is not ENABLED before reboot"
        )

    print("[PASS] Pre-reboot wlan0")

    # --------------------------------
    # Reboot
    # --------------------------------

    print("[3] Reboot DUT")

    reboot_start = time.time()

    dut.reboot()

    # --------------------------------
    # DOWN
    # --------------------------------

    print("[4] Wait DUT DOWN")

    if not wait_dut_down(
        DUT_IP,
        timeout=15
    ):
        raise RuntimeError(
            "DUT did not go DOWN"
        )

    print("[PASS] DUT DOWN detected")

    # --------------------------------
    # Network
    # --------------------------------

    print("[5] Wait DUT network")

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
        f"[PASS] DUT network recovered "
        f"after {network_time:.1f}s"
    )

    # --------------------------------
    # Telnet
    # --------------------------------

    print("[6] Wait DUT Telnet")

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

    # Give shell a short stabilization period.
    # Current DUT Telnet output may be delayed
    # immediately after login.
    time.sleep(5)

    # --------------------------------
    # AP
    # --------------------------------

    print("[7] Wait wlan0 AP recovery")

    if not wait_ap_enabled(
        dut,
        interface="wlan0",
        timeout=30
    ):
        raise RuntimeError(
            "wlan0 AP did not recover"
        )

    ap_time = (
        time.time() - reboot_start
    )

    print(
        f"[INFO] Reboot-to-AP time: "
        f"{ap_time:.1f}s"
    )

    # --------------------------------
    # Radio identity
    # --------------------------------

    print("[8] Verify radio after reboot")

    radio_after = dut.get_radio_info(
        "wlan0"
    )

    print(
        f"SSID      : {radio_after['ssid']}"
    )
    print(
        f"BSSID     : {radio_after['bssid']}"
    )
    print(
        f"Frequency : "
        f"{radio_after['frequency_ghz']} GHz"
    )

    if (
        radio_after["ssid"]
        != radio_before["ssid"]
    ):
        raise RuntimeError(
            "SSID changed after reboot"
        )

    if (
        radio_after["bssid"]
        != radio_before["bssid"]
    ):
        raise RuntimeError(
            "BSSID changed after reboot"
        )

    if (
        radio_after["frequency_ghz"]
        != radio_before["frequency_ghz"]
    ):
        raise RuntimeError(
            "Frequency changed after reboot"
        )

    print(
        "[PASS] wlan0 radio identity "
        "preserved"
    )

    print("==============================")
    print("[PASS] WIFI AP RECOVERY")
    print("==============================")


finally:

    try:
        dut.close()
    except Exception:
        pass
