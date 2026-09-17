import paramiko


class SSHClient:
    def __init__(self, host, username, password, port=22, timeout=10):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.client = None

    def connect(self):
        print(f"[SSH] Connecting to {self.host}:{self.port} ...")

        self.client = paramiko.SSHClient()

        self.client.set_missing_host_key_policy(
            paramiko.AutoAddPolicy()
        )

        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
            look_for_keys=False,
            allow_agent=False
        )

        print("[SSH] Connected")

    def execute(self, command):
        if self.client is None:
            raise RuntimeError("SSH is not connected")

        stdin, stdout, stderr = self.client.exec_command(command)

        output = stdout.read().decode(
            "utf-8",
            errors="ignore"
        )

        error = stderr.read().decode(
            "utf-8",
            errors="ignore"
        )

        exit_code = stdout.channel.recv_exit_status()

        return {
            "command": command,
            "stdout": output,
            "stderr": error,
            "exit_code": exit_code
        }

    def close(self):
        if self.client:
            self.client.close()
            self.client = None
            print("[SSH] Connection closed")
