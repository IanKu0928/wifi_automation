from device.golden_sta import GoldenSTA


STA_IP = "192.168.205.140"
STA_USERNAME = "root"
STA_PASSWORD = "111111"

CONTROL_DATA_IP = "192.168.1.2"
DUT_IP = "192.168.1.1"


def main():

    print("================================")
    print(" Golden STA Preparation Test")
    print("================================")

    sta = GoldenSTA(
        host=STA_IP,
        username=STA_USERNAME,
        password=STA_PASSWORD
    )

    try:
        print("\n[1] Connect STA Management")
        sta.connect()

        print("\n[2] Prepare WiFi")
        wifi_ip = sta.prepare_wifi()

        print("\n[3] Validate Route")
        route = sta.get_route(CONTROL_DATA_IP)

        print(route["stdout"])

        expected = f"dev {sta.wifi_interface}"

        if expected not in route["stdout"]:
            raise RuntimeError(
                f"Wrong route to {CONTROL_DATA_IP}"
            )

        print("[STA] Route validation PASS")

        print("\n[4] Ping DUT")
        ping = sta.ping(DUT_IP)

        print(ping["stdout"])

        if ping["exit_code"] != 0:
            raise RuntimeError("Ping DUT failed")

        print("[STA] Ping DUT PASS")

        print("\n================================")
        print(" GOLDEN STA PREPARATION PASS")
        print("================================")

        print(f"WiFi IP: {wifi_ip}")

    except Exception as e:

        print("\n================================")
        print(" GOLDEN STA PREPARATION FAIL")
        print("================================")

        print(f"Error: {e}")

    finally:
        sta.close()


if __name__ == "__main__":
    main()
