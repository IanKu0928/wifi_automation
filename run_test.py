from config.testbed import (
    CONTROL_DATA_IP,
    DUT_IP,
    DUT_WIFI_SSID,
    STA_MGMT_IP,
    STA_WIFI_INTERFACE,
)

from config.credentials import (
    DUT_USERNAME,
    DUT_PASSWORD,
    STA_USERNAME,
    STA_PASSWORD,
)

from device.dut import DUT
from device.golden_sta import GoldenSTA
from library.logger import TestLogger


def main():

    logger = TestLogger()

    logger.info("================================")
    logger.info(" WiFi Automation Framework")
    logger.info("================================")
    logger.info(f"Run ID: {logger.run_id}")

    dut = DUT(
        host=DUT_IP,
        username=DUT_USERNAME,
        password=DUT_PASSWORD,
        logger=logger
    )

    sta = GoldenSTA(
        host=STA_MGMT_IP,
        username=STA_USERNAME,
        password=STA_PASSWORD,
        wifi_interface=STA_WIFI_INTERFACE,
        ssid=DUT_WIFI_SSID,
        logger=logger
    )

    try:

        # --------------------------------
        # DUT Management
        # --------------------------------

        logger.info("[1] Connect DUT")

        dut.connect()

        logger.pass_result(
            "DUT management connection"
        )

        # --------------------------------
        # DUT Information
        # --------------------------------

        logger.info("[2] Get DUT Version")

        version = dut.get_version()

        logger.info(
            "DUT version collected"
        )

        # --------------------------------
        # STA Management
        # --------------------------------

        logger.info("[3] Connect Golden STA")

        sta.connect()

        logger.pass_result(
            "STA management connection"
        )

        # --------------------------------
        # Prepare WiFi
        # --------------------------------

        logger.info("[4] Prepare STA WiFi")

        wifi_ip = sta.prepare_wifi()

        logger.pass_result(
            f"STA WiFi connected: {wifi_ip}"
        )

        # --------------------------------
        # Validate Route
        # --------------------------------

        logger.info("[5] Validate Data Route")

        route = sta.get_route(
            CONTROL_DATA_IP
        )

        expected = (
            f"dev {STA_WIFI_INTERFACE}"
        )

        if expected not in route["stdout"]:
            raise RuntimeError(
                f"Wrong route to {CONTROL_DATA_IP}: "
                f"expected {STA_WIFI_INTERFACE}"
            )

        logger.pass_result(
            "STA data route"
        )

        # --------------------------------
        # Ping DUT
        # --------------------------------

        logger.info("[6] Ping DUT")

        ping_dut = sta.ping(DUT_IP)

        if ping_dut["exit_code"] != 0:
            raise RuntimeError(
                "STA cannot reach DUT"
            )

        logger.pass_result(
            "STA -> DUT connectivity"
        )

        # --------------------------------
        # DUT Firewall
        # --------------------------------

        logger.info(
            "[7] Prepare DUT Firewall"
        )

        dut.prepare_test_firewall(
            sta_ip=wifi_ip,
            control_ip=CONTROL_DATA_IP
        )

        logger.pass_result(
            "DUT firewall preparation"
        )

        # --------------------------------
        # Ping Control
        # --------------------------------

        logger.info(
            "[8] Ping Control PC"
        )

        ping_control = sta.ping(
            CONTROL_DATA_IP
        )

        if ping_control["exit_code"] != 0:
            raise RuntimeError(
                "STA cannot reach Control PC"
            )

        logger.pass_result(
            "STA -> Control connectivity"
        )

        # --------------------------------
        # Final Result
        # --------------------------------

        logger.info(
            "================================"
        )

        logger.pass_result(
            "ENVIRONMENT READY"
        )

        logger.info(
            "================================"
        )

        logger.info(
            f"STA WiFi IP : {wifi_ip}"
        )

        logger.info(
            f"DUT IP      : {DUT_IP}"
        )

        logger.info(
            f"Control IP  : {CONTROL_DATA_IP}"
        )

    except Exception as e:

        logger.info(
            "================================"
        )

        logger.fail_result(
            "ENVIRONMENT NOT READY"
        )

        logger.fail_result(
            f"Error: {e}"
        )

        logger.info(
            "================================"
        )

    finally:

        sta.close()
        dut.close()

        logger.info(
            f"Log directory: {logger.run_dir}"
        )


if __name__ == "__main__":
    main()
