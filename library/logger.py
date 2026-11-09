import os
from datetime import datetime


class TestLogger:

    def __init__(self, base_dir="logs"):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(base_dir, exist_ok=True)
        sequence = 0
        while True:
            run_id = timestamp if sequence == 0 else f"{timestamp}_{sequence:03d}"
            run_dir = os.path.join(base_dir, run_id)
            try:
                os.mkdir(run_dir)
            except FileExistsError:
                sequence += 1
            else:
                self.run_id = run_id
                self.run_dir = run_dir
                break

        self.run_log = os.path.join(
            self.run_dir,
            "run.log"
        )

        self.dut_log = os.path.join(
            self.run_dir,
            "dut.log"
        )

        self.sta_log = os.path.join(
            self.run_dir,
            "sta.log"
        )

    def _timestamp(self):
        return datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def _write(self, filename, message):

        with open(
            filename,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                f"[{self._timestamp()}] "
                f"{message}\n"
            )

    def info(self, message):

        print(message)

        self._write(
            self.run_log,
            f"[INFO] {message}"
        )

    def pass_result(self, message):

        print(f"[PASS] {message}")

        self._write(
            self.run_log,
            f"[PASS] {message}"
        )

    def fail_result(self, message):

        print(f"[FAIL] {message}")

        self._write(
            self.run_log,
            f"[FAIL] {message}"
        )

    def log_dut(self, command, output):

        self._write(
            self.dut_log,
            f"COMMAND: {command}"
        )

        self._write(
            self.dut_log,
            f"OUTPUT:\n{output}"
        )

    def log_sta(
        self,
        command,
        stdout,
        stderr="",
        exit_code=None
    ):

        self._write(
            self.sta_log,
            f"COMMAND: {command}"
        )

        self._write(
            self.sta_log,
            f"EXIT CODE: {exit_code}"
        )

        self._write(
            self.sta_log,
            f"STDOUT:\n{stdout}"
        )

        if stderr:

            self._write(
                self.sta_log,
                f"STDERR:\n{stderr}"
            )
