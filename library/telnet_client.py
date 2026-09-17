import telnetlib
import time


class TelnetClient:
    def __init__(self, host, username, password, port=23, timeout=10):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.tn = None

    def connect(self):
        print(f"[TELNET] Connecting to {self.host}:{self.port} ...")

        self.tn = telnetlib.Telnet(
            self.host,
            self.port,
            self.timeout
        )

        self.tn.read_until(b"login:", timeout=self.timeout)
        self.tn.write(self.username.encode("ascii") + b"\n")

        self.tn.read_until(b"Password:", timeout=self.timeout)
        self.tn.write(self.password.encode("ascii") + b"\n")

        time.sleep(1)

        output = self.tn.read_very_eager().decode(
            "utf-8",
            errors="ignore"
        )

        print("[TELNET] Connected")
        return output

    def execute(self, command, wait=1):
        if self.tn is None:
            raise RuntimeError("Telnet is not connected")

        self.tn.write(command.encode("ascii") + b"\n")

        time.sleep(wait)

        output = self.tn.read_very_eager().decode(
            "utf-8",
            errors="ignore"
        )

        return output

    def close(self):
        if self.tn:
            self.tn.close()
            self.tn = None
            print("[TELNET] Connection closed")
