import json
import math
from pathlib import Path


class ConfigLoader:

    REQUIRED_FIELDS = {
        "connectivity": (
            "ping_count",
            "max_packet_loss_percent"
        ),
        "wifi_signal": (
            "min_signal_dbm",
        ),
        "throughput": (
            "duration_sec",
            "upload_min_mbps",
            "download_min_mbps"
        )
    }

    def __init__(self, config_path):
        self.config_path = Path(config_path)

    @staticmethod
    def validate_number(value, field, minimum, maximum=None):

        if isinstance(value, bool) or not isinstance(
            value, (int, float)
        ):
            raise ValueError(
                f"{field} must be numeric"
            )

        if not math.isfinite(value):
            raise ValueError(
                f"{field} must be finite"
            )

        if value < minimum:
            raise ValueError(
                f"{field} must be >= {minimum}"
            )

        if maximum is not None and value > maximum:
            raise ValueError(
                f"{field} must be <= {maximum}"
            )

    @staticmethod
    def validate_positive_integer(value, field):

        if type(value) is not int or value <= 0:
            raise ValueError(
                f"{field} must be a positive integer"
            )

    def validate(self, config):

        if not isinstance(config, dict):
            raise ValueError(
                "Test configuration must be a JSON object"
            )

        for section, fields in self.REQUIRED_FIELDS.items():

            if section not in config:
                raise ValueError(
                    f"Missing configuration section: {section}"
                )

            values = config[section]

            if not isinstance(values, dict):
                raise ValueError(
                    f"Invalid configuration section: {section}"
                )

            for field in fields:
                if field not in values:
                    raise ValueError(
                        f"Missing configuration field: "
                        f"{section}.{field}"
                    )

        connectivity = config["connectivity"]
        wifi_signal = config["wifi_signal"]
        throughput = config["throughput"]

        self.validate_positive_integer(
            connectivity["ping_count"],
            "connectivity.ping_count"
        )

        self.validate_number(
            connectivity["max_packet_loss_percent"],
            "connectivity.max_packet_loss_percent",
            0,
            100
        )

        self.validate_number(
            wifi_signal["min_signal_dbm"],
            "wifi_signal.min_signal_dbm",
            -120,
            0
        )

        self.validate_positive_integer(
            throughput["duration_sec"],
            "throughput.duration_sec"
        )

        self.validate_number(
            throughput["upload_min_mbps"],
            "throughput.upload_min_mbps",
            0
        )

        self.validate_number(
            throughput["download_min_mbps"],
            "throughput.download_min_mbps",
            0
        )

        return config

    def load(self):

        if not self.config_path.is_file():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}"
            )

        with self.config_path.open(
            "r", encoding="utf-8"
        ) as file:
            config = json.load(file)

        return self.validate(config)
