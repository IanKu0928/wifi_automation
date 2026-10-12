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

    def verify_wifi_connection(self, expected_ssid, expected_bssid):
        result = self.get_wifi_status()
        output = result["stdout"]

        ssid_match = re.search(
            r"SSID:\s*(.+)",
            output
        )

        bssid_match = re.search(
            r"Connected to\s+([0-9A-Fa-f:]{17})",
            output
        )

        if not ssid_match or not bssid_match:
            return False

        actual_ssid = ssid_match.group(1).strip()
        actual_bssid = bssid_match.group(1).lower()

        expected_bssid = expected_bssid.lower()

        return (
            actual_ssid == expected_ssid
            and actual_bssid == expected_bssid
        )

    def set_wifi_bssid(self, bssid):
        command = (
            f'nmcli connection modify "{self.ssid}" '
            f'802-11-wireless.bssid {bssid}'
        )

        return self.run_command(command)

    def get_configured_bssid(self):
        command = (
            f'nmcli -g 802-11-wireless.bssid '
            f'connection show "{self.ssid}"'
        )

        return self.run_command(command)

    def prepare_target_wifi(self, expected_bssid):

        print("[STA] Enable WiFi")
        self.enable_wifi()

        print(
            f"[STA] Configure target BSSID: "
            f"{expected_bssid}"
        )

        result = self.set_wifi_bssid(expected_bssid)

        if result["exit_code"] != 0:
            raise RuntimeError(
                "Failed to configure target BSSID"
            )

        print(
            f"[STA] Connect target SSID: "
            f"{self.ssid}"
        )

        result = self.connect_wifi()

        if result["exit_code"] != 0:
            print(
                "[STA] nmcli returned an error; "
                "verifying actual WiFi state..."
            )

        start = time.time()

        while time.time() - start < 15:

            if self.verify_wifi_connection(
                expected_ssid=self.ssid,
                expected_bssid=expected_bssid
            ):
                print(
                    "[STA] Connected to target BSSID"
                )

                wifi_ip = self.get_wifi_ip()

                if wifi_ip:
                    print(
                        f"[STA] WiFi IP: {wifi_ip}"
                    )
                    return wifi_ip

            time.sleep(1)

        raise RuntimeError(
            f"Failed to connect target BSSID: "
            f"{expected_bssid}"
        )

    def run_iperf3(
        self,
        server_ip,
        duration=10,
        reverse=False
    ):
        command = (
            f"iperf3 -c {server_ip} "
            f"-t {duration} "
            f"-J"
        )

        if reverse:
            command += " -R"

        return self.run_command(command)
