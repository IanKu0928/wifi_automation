from library.ping_parser import parse_ping_output


pass_output = """
PING 192.168.1.2 (192.168.1.2) from 192.168.1.6 wlp2s0: 56(84) bytes of data.
64 bytes from 192.168.1.2: icmp_seq=1 ttl=64 time=2.20 ms
64 bytes from 192.168.1.2: icmp_seq=2 ttl=64 time=2.47 ms
64 bytes from 192.168.1.2: icmp_seq=3 ttl=64 time=2.91 ms

--- 192.168.1.2 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 2.201/2.526/2.907/0.290 ms
"""


fail_output = """
PING 192.168.1.2 (192.168.1.2) from 192.168.1.6 wlp2s0: 56(84) bytes of data.
From 192.168.1.1 icmp_seq=1 Destination Port Unreachable
From 192.168.1.1 icmp_seq=2 Destination Port Unreachable
From 192.168.1.1 icmp_seq=3 Destination Port Unreachable

--- 192.168.1.2 ping statistics ---
3 packets transmitted, 0 received, +3 errors, 100% packet loss, time 2003ms
"""


print("=== PASS CASE ===")

result = parse_ping_output(pass_output)

for key, value in result.items():
    print(f"{key:22}: {value}")


print()
print("=== FAIL CASE ===")

result = parse_ping_output(fail_output)

for key, value in result.items():
    print(f"{key:22}: {value}")
