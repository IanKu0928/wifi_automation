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
echo " Control PC Dependency Setup"
echo "================================"

if [[ ! -f /etc/os-release ]]; then
    echo "[FAIL] Cannot identify operating system"
    exit 1
fi

source /etc/os-release

if [[ "$ID" != "ubuntu" || "$VERSION_ID" != "24.04" ]]; then
    echo "[FAIL] Supported deployment target: Ubuntu 24.04"
    exit 1
fi

echo "[INFO] Installing dependencies..."

sudo apt-get update

sudo apt-get install -y \
    python3 \
    python3-paramiko \
    iperf3 \
    iputils-ping \
    iproute2 \
    openssh-client

echo "[INFO] Verifying installation..."

python3 - <<'PY'
import sys

if sys.version_info[:2] != (3, 12):
    raise SystemExit("[FAIL] Python 3.12 is required for validated deployment")
try:
    import paramiko
    import telnetlib
except (ImportError, OSError):
    raise SystemExit("[FAIL] Cannot import Paramiko or Python 3.12 telnetlib") from None

print("Python:", sys.version.split()[0])
print("Paramiko:", paramiko.__version__)
print("[PASS] Python dependencies")
PY

for cmd in iperf3 ping ip ssh; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "[FAIL] Missing command: $cmd"
        exit 1
    fi
done

echo
echo "[PASS] Control PC dependencies installed"
echo "[INFO] Configure config/credentials.py and config/testbed.py before testing."

