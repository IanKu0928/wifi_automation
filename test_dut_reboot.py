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

    print("[WAIT] Waiting for DUT to go DOWN")

    start = time.time()

    while time.time() - start < timeout:

        if not ping_dut(ip):
            elapsed = time.time() - start

            print(
                f"[PASS] DUT DOWN detected "
                f"after {elapsed:.1f}s"
            )

            return True

        time.sleep(1)

    return False


def wait_dut_up(ip, timeout=90):

    print("[WAIT] Waiting for DUT network recovery")

    start = time.time()

    while time.time() - start < timeout:

        if ping_dut(ip):
            elapsed = time.time() - start

            print(
                f"[PASS] DUT network UP "
                f"after {elapsed:.1f}s"
            )

            return True

        time.sleep(1)

    return False

def get_dut_uptime(dut, timeout=15):

    print("[WAIT] Reading DUT uptime")

    start = time.time()

    while time.time() - start < timeout:

        try:
            output = dut.run_command(
                "cat /proc/uptime"
            )

            print(
                f"[DEBUG] uptime raw output: "
                f"{output!r}"
            )

            for line in output.splitlines():

                line = line.strip()

                parts = line.split()

                if len(parts) < 2:
                    continue

                try:
                    uptime = float(parts[0])
                    idle = float(parts[1])

                    return uptime

                except ValueError:
                    continue

        except Exception as e:
            print(
                f"[WAIT] uptime not ready: {e}"
            )

        time.sleep(1)

    raise RuntimeError(
        "Failed to read DUT uptime"
    )

dut = DUT(
    host=DUT_IP,
    username=DUT_USERNAME,
    password=DUT_PASSWORD
)


try:

    # --------------------------------
    # Initial connection
    # --------------------------------

    print("[1] Connect DUT")

    dut.connect()

    print("[PASS] DUT connected")

    # --------------------------------
    # Read uptime before reboot
    # --------------------------------

    print("[2] Read uptime before reboot")

    output = dut.run_command(
        "cat /proc/uptime"
    )

    print(output)

    # --------------------------------
    # Reboot
    # --------------------------------

    print("[3] Reboot DUT")

    reboot_start = time.time()

    dut.reboot()

    print("[INFO] Reboot command sent")

    # --------------------------------
    # Detect DOWN
    # --------------------------------

    print("[4] Detect DUT DOWN")

    if not wait_dut_down(
        DUT_IP,
        timeout=15
    ):
        raise RuntimeError(
            "DUT did not go DOWN after reboot"
        )

    # --------------------------------
    # Wait network recovery
    # --------------------------------

    print("[5] Wait DUT network recovery")

    if not wait_dut_up(
        DUT_IP,
        timeout=90
    ):
        raise RuntimeError(
            "DUT network did not recover"
        )

    total_network_time = (
        time.time() - reboot_start
    )

    print(
        f"[INFO] Total reboot-to-network time: "
        f"{total_network_time:.1f}s"
    )

    # --------------------------------
    # Reconnect Telnet
    # --------------------------------

    print("[6] Reconnect DUT Telnet")

    telnet_start = time.time()

    while True:

        try:

            dut.connect()

            break

        except Exception:

            if (
                time.time() - telnet_start
                > 30
            ):
                raise RuntimeError(
                    "DUT network recovered but "
                    "Telnet did not recover"
                )

            time.sleep(2)

    print("[PASS] DUT Telnet recovered")

    # --------------------------------
    # Verify uptime
    # --------------------------------

    print("[7] Verify reboot")

    uptime = get_dut_uptime(
        dut,
        timeout=15
    )

    print(
        f"[INFO] DUT uptime after reboot: "
        f"{uptime:.1f}s"
    )

    if uptime > 180:
        raise RuntimeError(
            "DUT uptime is too high; "
            "reboot could not be verified"
        )

    print("[PASS] DUT reboot verified")

    print("==============================")
    print("[PASS] DUT REBOOT RECOVERY")
    print("==============================")


finally:

    try:
        dut.close()
    except Exception:
        pass
