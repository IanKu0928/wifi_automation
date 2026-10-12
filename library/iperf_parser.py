import json


def parse_iperf3_json(output):

    result = {
        "sender_mbps": None,
        "receiver_mbps": None,
        "retransmits": None,
        "duration_sec": None,
    }

    try:
        data = json.loads(output)

        end = data["end"]

        sum_sent = end["sum_sent"]
        sum_received = end["sum_received"]

        result["sender_mbps"] = (
            sum_sent["bits_per_second"]
            / 1_000_000
        )

        result["receiver_mbps"] = (
            sum_received["bits_per_second"]
            / 1_000_000
        )

        result["retransmits"] = (
            sum_sent.get("retransmits")
        )

        result["duration_sec"] = (
            sum_received["seconds"]
        )

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError
    ):
        return result

    return result
