import subprocess
import time


class IperfServer:

    def __init__(self, port=5201):
        self.port = port
        self.process = None

    def start(self):

        if self.process is not None:
            raise RuntimeError(
                "iperf3 server is already managed"
            )

        print(
            f"[IPERF] Start server on port "
            f"{self.port}"
        )

        self.process = subprocess.Popen(
            [
                "iperf3",
                "-s",
                "-p",
                str(self.port)
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        time.sleep(1)

        if self.process.poll() is not None:
            self.process = None

            raise RuntimeError(
                f"Failed to start iperf3 server "
                f"on port {self.port}"
            )

        print("[IPERF] Server ready")

    def stop(self):

        if self.process is None:
            return

        print("[IPERF] Stop server")

        self.process.terminate()

        try:
            self.process.wait(timeout=3)

        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

        self.process = None

        print("[IPERF] Server stopped")
