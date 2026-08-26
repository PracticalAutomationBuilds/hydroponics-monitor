#!/usr/bin/env bash
set -euo pipefail

SYNC=0
if [[ "${1:-}" == "--sync-from-system" ]]; then
  SYNC=1
elif [[ $# -gt 0 ]]; then
  echo "Usage: sudo $0 [--sync-from-system]"
  exit 1
fi

echo "Hydroponic monitor RTC verification"
echo "------------------------------------"

if [[ -e /dev/rtc0 ]]; then
  echo "RTC device: /dev/rtc0 present"
else
  echo "ERROR: /dev/rtc0 is missing."
  echo "Confirm the module orientation, I2C enablement and DS3231 overlay, then reboot."
  exit 1
fi

if [[ -r /sys/class/rtc/rtc0/name ]]; then
  echo "RTC driver: $(cat /sys/class/rtc/rtc0/name)"
fi

if command -v i2cdetect >/dev/null 2>&1; then
  echo
  echo "I2C bus 1 scan:"
  i2cdetect -y 1 || true
  echo "At address 0x68, 'UU' normally means the kernel RTC driver owns the device."
fi

echo
echo "Current system time:"
date --iso-8601=seconds

echo
echo "Current RTC time (UTC):"
hwclock --show --utc

if [[ "${SYNC}" -eq 1 ]]; then
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run the sync operation with sudo."
    exit 1
  fi

  NTP_SYNCED=""
  if command -v timedatectl >/dev/null 2>&1; then
    NTP_SYNCED="$(timedatectl show -p NTPSynchronized --value 2>/dev/null || true)"
  fi

  if [[ "${NTP_SYNCED}" != "yes" ]]; then
    echo
    echo "Refusing to overwrite the RTC because systemd does not report"
    echo "network time as synchronised."
    echo "Connect the Pi to the network, wait for the system time to become correct,"
    echo "then run this command again."
    exit 1
  fi

  echo
  echo "Writing the correct system time to the RTC in UTC..."
  hwclock --systohc --utc
  echo "RTC after synchronisation:"
  hwclock --show --utc
fi

if systemctl list-unit-files fake-hwclock.service >/dev/null 2>&1; then
  echo
  echo "NOTICE: fake-hwclock.service exists on this OS image."
  echo "After the DS3231 is confirmed working, disable it with:"
  echo "  sudo systemctl disable --now fake-hwclock.service"
fi
