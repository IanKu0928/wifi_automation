import time

from library.iperf_server import IperfServer


server = IperfServer()

try:

    print("[1] Start iperf3 server")

    server.start()

    print("[PASS] iperf3 server started")

    print("[2] Keep server running for 5 seconds")

    time.sleep(5)

finally:

    print("[3] Stop iperf3 server")

    server.stop()

print("[PASS] iperf3 server lifecycle")
