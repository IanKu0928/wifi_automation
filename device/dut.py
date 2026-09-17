from library.telnet_client import TelnetClient


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
