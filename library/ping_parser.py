import re


def parse_ping_output(output):

    result = {
        "transmitted": None,
        "received": None,
        "errors": 0,
        "packet_loss_percent": None,
        "min_latency_ms": None,
        "avg_latency_ms": None,
        "max_latency_ms": None,
        "mdev_latency_ms": None,
    }

    packet_match = re.search(
        r"(\d+) packets transmitted,\s*"
        r"(\d+) received,"
        r"(?:\s*\+?(\d+) errors,)?\s*"
        r"([\d.]+)% packet loss",
        output
    )

    if packet_match:
        result["transmitted"] = int(
            packet_match.group(1)
        )

        result["received"] = int(
            packet_match.group(2)
        )

        if packet_match.group(3):
            result["errors"] = int(
                packet_match.group(3)
            )

        result["packet_loss_percent"] = float(
            packet_match.group(4)
        )

    latency_match = re.search(
        r"=\s*"
        r"([\d.]+)/"
        r"([\d.]+)/"
        r"([\d.]+)/"
        r"([\d.]+)\s*ms",
        output
    )

    if latency_match:
        result["min_latency_ms"] = float(
            latency_match.group(1)
        )

        result["avg_latency_ms"] = float(
            latency_match.group(2)
        )

        result["max_latency_ms"] = float(
            latency_match.group(3)
        )

        result["mdev_latency_ms"] = float(
            latency_match.group(4)
        )

    return result
