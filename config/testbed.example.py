# ========================================
# Control PC
# ========================================

CONTROL_DATA_IP = "192.168.1.2"


# ========================================
# DUT
# ========================================

DUT_IP = "192.168.1.1"

DUT_WIFI_INTERFACE = "wlan0"

# Reference SSID only: run_test.py discovers the actual SSID/BSSID from the DUT.
DUT_WIFI_SSID = "YOUR_WIFI_SSID"

# This file contains a WiFi secret: keep the local copy private (chmod 600).
# Set to None or "" for an open WiFi network.
DUT_WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"


# ========================================
# Golden STA
# ========================================

STA_MGMT_IP = "192.168.205.140"

STA_WIFI_INTERFACE = "wlp2s0"
