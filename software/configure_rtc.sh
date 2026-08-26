#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 && "${HYDRO_RTC_TEST_MODE:-0}" != "1" ]]; then
  echo "Run with sudo: sudo ./configure_rtc.sh"
  exit 1
fi

if [[ -n "${BOOT_CONFIG_PATH:-}" ]]; then
  CONFIG_FILE="${BOOT_CONFIG_PATH}"
elif [[ -f /boot/firmware/config.txt ]]; then
  CONFIG_FILE="/boot/firmware/config.txt"
elif [[ -f /boot/config.txt ]]; then
  CONFIG_FILE="/boot/config.txt"
else
  echo "Could not locate Raspberry Pi boot config.txt."
  exit 1
fi

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "Boot configuration file does not exist: ${CONFIG_FILE}"
  exit 1
fi

DESIRED_OVERLAY="dtoverlay=i2c-rtc,ds3231"

# Refuse to stack a second, conflicting I2C RTC overlay.
OTHER_RTC_LINES="$(
  grep -E '^[[:space:]]*dtoverlay=i2c-rtc,' "${CONFIG_FILE}" 2>/dev/null \
    | grep -v -F "${DESIRED_OVERLAY}" || true
)"
if [[ -n "${OTHER_RTC_LINES}" ]]; then
  echo "A different active I2C RTC overlay already exists:"
  echo "${OTHER_RTC_LINES}"
  echo "Inspect ${CONFIG_FILE} manually before continuing."
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${CONFIG_FILE}.pre-hydro-rtc-${STAMP}"
cp -a "${CONFIG_FILE}" "${BACKUP}"
echo "Backed up boot configuration to ${BACKUP}"

# Enable I2C using Raspberry Pi's supported utility when available.
if [[ "${HYDRO_RTC_TEST_MODE:-0}" != "1" ]] && command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_i2c 0
fi

NEED_I2C=1
if grep -Eq '^[[:space:]]*dtparam=(i2c|i2c_arm)=on([,[:space:]]|$)' "${CONFIG_FILE}"; then
  NEED_I2C=0
fi

NEED_OVERLAY=1
if grep -Eq '^[[:space:]]*dtoverlay=i2c-rtc,ds3231([,[:space:]]|$)' "${CONFIG_FILE}"; then
  NEED_OVERLAY=0
fi

if [[ "${NEED_I2C}" -eq 1 || "${NEED_OVERLAY}" -eq 1 ]]; then
  {
    echo
    echo "[all]"
    echo "# Hydroponic monitor: Jaycar XC9044 / DS3231 RTC"
    if [[ "${NEED_I2C}" -eq 1 ]]; then
      echo "dtparam=i2c_arm=on"
    fi
    if [[ "${NEED_OVERLAY}" -eq 1 ]]; then
      echo "${DESIRED_OVERLAY}"
    fi
  } >> "${CONFIG_FILE}"
fi

echo
echo "RTC boot configuration is present in ${CONFIG_FILE}:"
grep -E '^[[:space:]]*(dtparam=(i2c|i2c_arm)=on|dtoverlay=i2c-rtc,ds3231)' \
  "${CONFIG_FILE}" || true
echo
echo "Reboot is required. After reboot run:"
echo "  sudo /opt/hydro-monitor/verify_rtc.sh"
echo
echo "Once the Pi's system time is correct and network-synchronised, initialise"
echo "the RTC with:"
echo "  sudo /opt/hydro-monitor/verify_rtc.sh --sync-from-system"
