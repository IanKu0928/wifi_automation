import time
import re

from library.ssh_client import SSHClient


class GoldenSTA:
    def __init__(
        self,
        host,
        username,
        password,
        wifi_interface="wlp2s0",
        ssid="RTL867x-ADSL",
        logger=None
    ):
        self.host = host
        self.wifi_interface = wifi_interface
        self.ssid = ssid
        self.logger = logger

        self.client = SSHClient(
            host=host,
            username=username,
            password=password
        )

    def connect(self):
        self.client.connect()

    def run_command(self, command):
        result = self.client.execute(command)

        if self.logger:
            self.logger.log_sta(
                command=result["command"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                exit_code=result["exit_code"]
            )

        return result

    def enable_wifi(self):
        return self.run_command("nmcli radio wifi on")

    def connect_wifi(self):
        command = (
            f'nmcli dev wifi connect "{self.ssid}" '
            f'ifname {self.wifi_interface}'
        )
        return self.run_command(command)

    def get_wifi_status(self):
        return self.run_command(
            f"iw dev {self.wifi_interface} link"
        )

    def get_ip_address(self):
        return self.run_command(
            f"ip -4 addr show {self.wifi_interface}"
        )

    def get_wifi_ip(self):
        result = self.get_ip_address()

        match = re.search(
            r"inet\s+(\d+\.\d+\.\d+\.\d+)/",
            result["stdout"]
        )

        if match:
            return match.group(1)

        return None

    def get_route(self, destination):
        return self.run_command(
            f"ip route get {destination}"
        )

    def ping(self, destination, count=3):
        return self.run_command(
            f"ping -I {self.wifi_interface} "
            f"-c {count} {destination}"
        )

    def wait_for_wifi(self, timeout=15):
        start = time.time()

        while time.time() - start < timeout:

            result = self.get_wifi_status()
            output = result["stdout"]

            connected = "Connected to" in output
            correct_ssid = f"SSID: {self.ssid}" in output

            if connected and correct_ssid:
                return True

            time.sleep(1)

        return False

    def prepare_wifi(self):

        print("[STA] Enable WiFi")
        self.enable_wifi()

        print(f"[STA] Connect SSID: {self.ssid}")

        result = self.connect_wifi()

        if result["exit_code"] != 0:
            print(
                "[STA] nmcli returned an error; "
                "verifying actual WiFi state..."
            )

        if not self.wait_for_wifi():
            raise RuntimeError(
                f"Failed to connect WiFi SSID: {self.ssid}"
            )

        print("[STA] WiFi connected")

        wifi_ip = self.get_wifi_ip()

        if wifi_ip is None:
            raise RuntimeError(
                "WiFi connected but DHCP IP was not obtained"
            )

        print(f"[STA] WiFi IP: {wifi_ip}")

        return wifi_ip

    def close(self):
        self.client.close()
