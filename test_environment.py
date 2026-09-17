from device.dut import DUT
from device.golden_sta import GoldenSTA

from config.testbed import (
    CONTROL_DATA_IP,
    DUT_IP,
    DUT_USERNAME,
    DUT_PASSWORD,
    DUT_WIFI_SSID,
    STA_MGMT_IP,
    STA_USERNAME,
    STA_PASSWORD,
    STA_WIFI_INTERFACE,
)


def main():

    print("================================")
    print(" Environment Preparation Test")
    print("================================")

    dut = DUT(
        host=DUT_IP,
        username=DUT_USERNAME,
        password=DUT_PASSWORD
    )

    sta = GoldenSTA(
        host=STA_MGMT_IP,
        username=STA_USERNAME,
        password=STA_PASSWORD,
        wifi_interface=STA_WIFI_INTERFACE,
        ssid=DUT_WIFI_SSID
    )

    try:

        # --------------------------------
        # 1. Connect DUT
        # --------------------------------

        print("\n[1] Connect DUT")

        dut.connect()

        print("[DUT] Management connection PASS")

        # --------------------------------
        # 2. Connect Golden STA
        # --------------------------------

        print("\n[2] Connect Golden STA")

        sta.connect()

        print("[STA] Management connection PASS")

        # --------------------------------
        # 3. Prepare STA WiFi
        # --------------------------------

        print("\n[3] Prepare STA WiFi")

        wifi_ip = sta.prepare_wifi()

        print(f"[STA] WiFi IP = {wifi_ip}")

        # --------------------------------
        # 4. Validate route
        # --------------------------------

        print("\n[4] Validate Data Route")

        route = sta.get_route(CONTROL_DATA_IP)

        print(route["stdout"])

        expected = f"dev {sta.wifi_interface}"

        if expected not in route["stdout"]:
            raise RuntimeError(
                f"Wrong route to {CONTROL_DATA_IP}"
            )

        print("[STA] Data route PASS")

        # --------------------------------
        # 5. Ping DUT
        # --------------------------------

        print("\n[5] Ping DUT")

        result = sta.ping(DUT_IP)

        print(result["stdout"])

        if result["exit_code"] != 0:
            raise RuntimeError(
                "STA cannot reach DUT"
            )

        print("[STA] Ping DUT PASS")

        # --------------------------------
        # 6. Prepare DUT firewall
        # --------------------------------

        print("\n[6] Prepare DUT Firewall")

        dut.prepare_test_firewall(
            sta_ip=wifi_ip,
            control_ip=CONTROL_DATA_IP
        )

        # --------------------------------
        # 7. Ping Control PC
        # --------------------------------

        print("\n[7] Ping Control PC")

        result = sta.ping(CONTROL_DATA_IP)

        print(result["stdout"])

        if result["exit_code"] != 0:
            raise RuntimeError(
                "STA cannot reach Control PC"
            )

        print("[STA] Ping Control PC PASS")

        # --------------------------------
        # Final
        # --------------------------------

        print("\n================================")
        print(" ENVIRONMENT PREPARATION PASS")
        print("================================")

        print(f"STA WiFi IP : {wifi_ip}")
        print(f"DUT IP      : {DUT_IP}")
        print(f"Control IP  : {CONTROL_DATA_IP}")

    except Exception as e:

        print("\n================================")
        print(" ENVIRONMENT PREPARATION FAIL")
        print("================================")

        print(f"Error: {e}")

    finally:

        sta.close()
        dut.close()


if __name__ == "__main__":
    main()
