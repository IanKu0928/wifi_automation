from library.telnet_client import TelnetClient
import re

class DUT:
    def __init__(self, host, username, password, logger=None):
        self.host = host
        self.logger = logger

        self.client = TelnetClient(
            host=host,
            username=username,
            password=password
        )

    def connect(self):
        return self.client.connect()

    def run_command(self, command):
        output = self.client.execute(command)

        if self.logger:
            self.logger.log_dut(
                command=command,
                output=output
            )

        return output

    def get_version(self):
        return self.run_command("cat /etc/version")

    def get_ip_address(self):
        return self.run_command("ifconfig br0")

    def get_wifi_status(self):
        return self.run_command("iwconfig wlan0")

    def get_firewall_rules(self):
        return self.run_command(
            "iptables -L wifi_nosecurity_access -n -v --line-numbers"
        )

    def prepare_test_firewall(self, sta_ip, control_ip):
        print(
            f"[DUT] Prepare firewall: "
            f"{sta_ip} -> {control_ip}"
        )

        check_command = (
            f"iptables -C wifi_nosecurity_access "
            f"-s {sta_ip} "
            f"-d {control_ip} "
            f"-j ACCEPT"
        )

        output = self.run_command(check_command)

        # telnet does not currently provide a reliable shell exit code,
        # so verify the actual rule list before deciding.
        rules = self.get_firewall_rules()

        expected_source = sta_ip
        expected_destination = control_ip

        for line in rules.splitlines():
            if (
                "ACCEPT" in line
                and expected_source in line
                and expected_destination in line
            ):
                print("[DUT] Firewall rule already exists")
                return

        print("[DUT] Firewall rule not found, adding rule")

        add_command = (
            f"iptables -I wifi_nosecurity_access 1 "
            f"-s {sta_ip} "
            f"-d {control_ip} "
            f"-j ACCEPT"
        )

        self.run_command(add_command)

        # Verify again after adding.
        rules = self.get_firewall_rules()

        for line in rules.splitlines():
            if (
                "ACCEPT" in line
                and expected_source in line
                and expected_destination in line
            ):
                print("[DUT] Firewall rule verification PASS")
                return

        raise RuntimeError(
            "Failed to configure DUT firewall rule"
        )

    def close(self):
        self.client.close()

    def get_radio_info(self, interface="wlan0"):
        output = self.run_command(f"iwconfig {interface}")

        ssid_match = re.search(r'ESSID:"([^"]+)"', output)
        bssid_match = re.search(
            r'Access Point:\s*([0-9A-Fa-f:]{17})',
            output
        )
        freq_match = re.search(
            r'Frequency:([0-9.]+)\s*GHz',
            output
        )

        if not ssid_match:
            raise RuntimeError(
                f"Failed to get SSID from DUT {interface}"
            )

        if not bssid_match:
            raise RuntimeError(
                f"Failed to get BSSID from DUT {interface}"
            )

        if not freq_match:
            raise RuntimeError(
                f"Failed to get frequency from DUT {interface}"
            )

        return {
            "interface": interface,
            "ssid": ssid_match.group(1),
            "bssid": bssid_match.group(1).lower(),
            "frequency_ghz": float(freq_match.group(1)),
        }

    def get_ap_status(self, interface="wlan0"):
        return self.run_command(
            f"hostapd_cli -i {interface} status"
        )

    def disable_ap(self, interface="wlan0"):
        print(f"[DUT] Disable AP: {interface}")

        return self.run_command(
            f"hostapd_cli -i {interface} disable"
        )


    def enable_ap(self, interface="wlan0"):
        print(f"[DUT] Enable AP: {interface}")

        return self.run_command(
            f"hostapd_cli -i {interface} enable"
        )

    def is_ap_enabled(self, interface="wlan0"):
        output = self.get_ap_status(interface)

        return "state=ENABLED" in output

    def reboot(self):
        print("[DUT] Reboot DUT")

        try:
            self.run_command(
                "reboot"
            )
        except (EOFError, OSError):
            # Telnet disconnect after reboot is expected.
            pass

        # Current Telnet session is no longer usable.
        try:
            self.client.close()
        except Exception:
            pass
