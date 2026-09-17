from library.logger import TestLogger


logger = TestLogger()

logger.info("Automation started")

logger.pass_result(
    "DUT connection"
)

logger.pass_result(
    "STA connection"
)

logger.log_dut(
    "cat /etc/version",
    "DS254GR-AID-v1.0_260728"
)

logger.log_sta(
    "iw dev wlp2s0 link",
    "Connected to 00:e0:4c:86:70:01",
    "",
    0
)

logger.info(
    f"Log directory: {logger.run_dir}"
)
