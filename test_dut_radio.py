from config.testbed import DUT_IP
from config.credentials import DUT_USERNAME, DUT_PASSWORD
from device.dut import DUT


dut = DUT(
    host=DUT_IP,
    username=DUT_USERNAME,
    password=DUT_PASSWORD
)

try:
    dut.connect()

    radio = dut.get_radio_info("wlan0")

    print("DUT Radio Information")
    print("---------------------")
    print(f"Interface : {radio['interface']}")
    print(f"SSID      : {radio['ssid']}")
    print(f"BSSID     : {radio['bssid']}")
    print(f"Frequency : {radio['frequency_ghz']} GHz")

finally:
    dut.close()
