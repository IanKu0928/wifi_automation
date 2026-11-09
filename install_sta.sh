#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[FAIL] Dependency setup failed at line $LINENO" >&2' ERR

for cmd in sudo apt-get; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "[FAIL] Missing installer prerequisite: $cmd" >&2
        exit 1
    fi
done

echo "================================"
echo " WiFi Automation Framework"
echo " Golden STA Dependency Setup"
echo "================================"

if [[ ! -f /etc/os-release ]]; then
    echo "[FAIL] Cannot identify operating system"
    exit 1
fi

source /etc/os-release

if [[ "$ID" != "ubuntu" || "$VERSION_ID" != "20.04" ]]; then
    echo "[FAIL] Validated Golden STA target: Ubuntu 20.04"
    exit 1
fi

echo "[INFO] Installing Golden STA dependencies..."

sudo apt-get update

sudo apt-get install -y \
    network-manager \
    iw \
    iproute2 \
    iputils-ping \
    iperf3 \
    openssh-server

echo "[INFO] Verifying required commands..."

for cmd in nmcli iw ip ping iperf3 systemctl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "[FAIL] Missing command: $cmd"
        exit 1
    fi
done

if ! command -v sshd >/dev/null 2>&1 && [[ ! -x /usr/sbin/sshd ]]; then
    echo "[FAIL] Missing SSH server executable: sshd"
    exit 1
fi

echo "[INFO] Checking NetworkManager..."

if ! systemctl is-active --quiet NetworkManager; then
    echo "[FAIL] NetworkManager is not running"
    exit 1
fi

echo "[INFO] Checking SSH server..."

if ! systemctl is-active --quiet ssh; then
    echo "[FAIL] SSH server is not running"
    echo "[INFO] Enable it after reviewing the STA network configuration."
    exit 1
fi

echo
echo "[PASS] Golden STA dependencies verified"
echo "[INFO] Configure WiFi interface and SSH access before testing."

