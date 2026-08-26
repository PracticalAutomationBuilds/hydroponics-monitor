#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo: sudo ./install.sh"
  exit 1
fi

EXPECTED_USER="hydroponics"
EXPECTED_HOSTNAME="hydro-monitor"
TARGET_USER="${SUDO_USER:-}"

if [[ -z "${TARGET_USER}" || "${TARGET_USER}" == "root" ]]; then
  echo "Unable to determine the normal Raspberry Pi username."
  echo "Log in as ${EXPECTED_USER} and run: sudo ./install.sh"
  exit 1
fi

if [[ "${TARGET_USER}" != "${EXPECTED_USER}" ]]; then
  echo "This project is assigned to Raspberry Pi user: ${EXPECTED_USER}"
  echo "Current sudo user: ${TARGET_USER}"
  echo "Log in with: ssh ${EXPECTED_USER}@${EXPECTED_HOSTNAME}.local"
  exit 1
fi

CURRENT_HOSTNAME="$(hostname)"
if [[ "${CURRENT_HOSTNAME}" != "${EXPECTED_HOSTNAME}" ]]; then
  echo "This project is assigned to hostname: ${EXPECTED_HOSTNAME}"
  echo "Current hostname: ${CURRENT_HOSTNAME}"
  echo "Correct the hostname before installing so mDNS and documentation stay consistent."
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="${PROJECT_DIR}/VERSION"
INSTALL_DIR="/opt/hydro-monitor"
LOG_DIR="/var/log/hydro-monitor"
STATE_DIR="/var/lib/hydro-monitor"
SECRETS_DIR="/etc/hydro-monitor"
SECRETS_FILE="${SECRETS_DIR}/pushover.json"
SECRETS_GROUP="hydro-monitor-secrets"
MONITOR_SERVICE="/etc/systemd/system/hydro-monitor.service"
DASHBOARD_SERVICE="/etc/systemd/system/hydro-dashboard.service"

if [[ ! -f "${VERSION_FILE}" ]]; then
  echo "Release VERSION file is missing; refusing to install an unidentified package."
  exit 1
fi

RELEASE_VERSION="$(tr -d '\r\n' < "${VERSION_FILE}")"
if [[ ! "${RELEASE_VERSION}" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
  echo "Invalid Semantic Version in ${VERSION_FILE}: ${RELEASE_VERSION}"
  exit 1
fi

INSTALL_MODE="fresh"
INSTALLED_VERSION=""
if [[ -d "${INSTALL_DIR}" ]] && [[ -f "${INSTALL_DIR}/config.json" || -f "${INSTALL_DIR}/hydro_monitor.py" || -f "${INSTALL_DIR}/VERSION" ]]; then
  INSTALL_MODE="upgrade"
  if [[ -f "${INSTALL_DIR}/VERSION" ]]; then
    INSTALLED_VERSION="$(tr -d '\r\n' < "${INSTALL_DIR}/VERSION")"
  elif [[ -f "${INSTALL_DIR}/hydro_monitor.py" ]]; then
    # Legacy development installers did not always copy VERSION into /opt.
    INSTALLED_VERSION="$(sed -nE 's/^VERSION[[:space:]]*=[[:space:]]*["'\'' ]([^"'\'' ]+)["'\'' ].*/\1/p' "${INSTALL_DIR}/hydro_monitor.py" | head -n 1 || true)"
  fi
  INSTALLED_VERSION="${INSTALLED_VERSION:-legacy/unknown}"
fi

printf '\nHydro Monitor %s installer\n' "${RELEASE_VERSION}"
if [[ "${INSTALL_MODE}" == "upgrade" ]]; then
  echo "Mode: upgrade (${INSTALLED_VERSION} -> ${RELEASE_VERSION})"
  echo "Existing configuration, history, logs and Pushover secrets will be preserved."
else
  echo "Mode: fresh installation"
fi
printf '\n'

echo "Stopping and disabling any existing Hydro Monitor services..."
systemctl disable --now hydro-dashboard.service hydro-monitor.service >/dev/null 2>&1 || true

echo "Installing OS packages..."
apt-get update
apt-get install -y python3-gpiozero python3-venv python3-pip avahi-daemon i2c-tools util-linux

if ! apt-get install -y libgpiod2; then
  echo "libgpiod2 was unavailable; trying libgpiod3..."
  apt-get install -y libgpiod3
fi

echo "Creating protected notification group and directories..."
if ! getent group "${SECRETS_GROUP}" >/dev/null 2>&1; then
  groupadd --system "${SECRETS_GROUP}"
fi
usermod -a -G "${SECRETS_GROUP}" "${TARGET_USER}"
mkdir -p "${INSTALL_DIR}" "${LOG_DIR}" "${STATE_DIR}" "${SECRETS_DIR}"

STAMP="$(date +%Y%m%d-%H%M%S)"
if [[ -f "${INSTALL_DIR}/config.json" ]]; then
  CONFIG_BACKUP="${INSTALL_DIR}/config.json.pre-${RELEASE_VERSION}-${STAMP}"
  cp -a "${INSTALL_DIR}/config.json" "${CONFIG_BACKUP}"
  echo "Existing configuration backed up to: ${CONFIG_BACKUP}"
fi

MERGED_CONFIG_TMP="$(mktemp)"
cleanup() {
  rm -f "${MERGED_CONFIG_TMP}"
}
trap cleanup EXIT

MERGE_ARGS=(
  --defaults "${PROJECT_DIR}/config.json"
  --output "${MERGED_CONFIG_TMP}"
)
if [[ -f "${INSTALL_DIR}/config.json" ]]; then
  MERGE_ARGS+=(--existing "${INSTALL_DIR}/config.json")
fi

# Build and validate the replacement configuration before changing the installed copy.
python3 "${PROJECT_DIR}/merge_config.py" "${MERGE_ARGS[@]}"
python3 -m json.tool "${MERGED_CONFIG_TMP}" >/dev/null

echo "Installing project files..."
install -m 0755 "${PROJECT_DIR}/hydro_monitor.py" "${INSTALL_DIR}/hydro_monitor.py"
install -m 0755 "${PROJECT_DIR}/hydro_dashboard.py" "${INSTALL_DIR}/hydro_dashboard.py"
install -m 0644 "${PROJECT_DIR}/hydro_version.py" "${INSTALL_DIR}/hydro_version.py"
install -m 0644 "${PROJECT_DIR}/VERSION" "${INSTALL_DIR}/VERSION"
install -m 0644 "${PROJECT_DIR}/dashboard.html" "${INSTALL_DIR}/dashboard.html"
install -m 0644 "${PROJECT_DIR}/dashboard.css" "${INSTALL_DIR}/dashboard.css"
install -m 0644 "${PROJECT_DIR}/dashboard.js" "${INSTALL_DIR}/dashboard.js"
install -m 0644 "${MERGED_CONFIG_TMP}" "${INSTALL_DIR}/config.json"
install -m 0644 "${PROJECT_DIR}/requirements.txt" "${INSTALL_DIR}/requirements.txt"
install -m 0755 "${PROJECT_DIR}/configure_rtc.sh" "${INSTALL_DIR}/configure_rtc.sh"
install -m 0755 "${PROJECT_DIR}/verify_rtc.sh" "${INSTALL_DIR}/verify_rtc.sh"
install -m 0755 "${PROJECT_DIR}/configure_pushover.py" "${INSTALL_DIR}/configure_pushover.py"
install -m 0755 "${PROJECT_DIR}/configure_temperature_probes.py" "${INSTALL_DIR}/configure_temperature_probes.py"
install -m 0755 "${PROJECT_DIR}/merge_config.py" "${INSTALL_DIR}/merge_config.py"
install -m 0644 "${PROJECT_DIR}/pushover_secrets.example.json" "${INSTALL_DIR}/pushover_secrets.example.json"

if [[ ! -e "${SECRETS_FILE}" ]]; then
  install -o root -g "${SECRETS_GROUP}" -m 0640 \
    "${PROJECT_DIR}/pushover_secrets.example.json" "${SECRETS_FILE}"
else
  chown root:"${SECRETS_GROUP}" "${SECRETS_FILE}"
  chmod 0640 "${SECRETS_FILE}"
fi

echo "Creating Python virtual environment..."
rm -rf "${INSTALL_DIR}/venv"
python3 -m venv --system-site-packages "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/python" -m pip install --upgrade pip
"${INSTALL_DIR}/venv/bin/python" -m pip install -r "${INSTALL_DIR}/requirements.txt"

echo "Installing systemd services..."
sed "s/REPLACE_WITH_YOUR_USERNAME/${TARGET_USER}/g" \
  "${PROJECT_DIR}/hydro-monitor.service" > "${MONITOR_SERVICE}"
sed "s/REPLACE_WITH_YOUR_USERNAME/${TARGET_USER}/g" \
  "${PROJECT_DIR}/hydro-dashboard.service" > "${DASHBOARD_SERVICE}"

# The Pi user writes logs/state; the dashboard reads them.
if getent group gpio >/dev/null 2>&1; then
  chown -R "${TARGET_USER}:gpio" "${INSTALL_DIR}" "${LOG_DIR}" "${STATE_DIR}"
else
  chown -R "${TARGET_USER}:${TARGET_USER}" "${INSTALL_DIR}" "${LOG_DIR}" "${STATE_DIR}"
fi

# Pushover credentials remain root-owned and are never copied into dashboard backups.
chown root:"${SECRETS_GROUP}" "${SECRETS_FILE}"
chmod 0640 "${SECRETS_FILE}"

echo "Configuring I2C and the DS3231 RTC overlay..."
"${INSTALL_DIR}/configure_rtc.sh"

systemctl daemon-reload

# The monitor/dashboard were disabled before files were changed and remain
# disabled until hardware commissioning is complete.
systemctl enable --now avahi-daemon.service

cat <<EOF2

Installation complete: Hydro Monitor ${RELEASE_VERSION}

The monitor and dashboard services have been installed but deliberately left
stopped and disabled until commissioning is complete.
EOF2

if [[ "${INSTALL_MODE}" == "upgrade" ]]; then
  cat <<EOF2

Upgrade notes:
- Existing config.json was preserved and merged with current release defaults.
- Assigned DS18B20 hardware IDs are preserved.
- Pushover configuration and secrets are preserved.
- Historical readings, event logs and runtime state are preserved.
- Probe reassignment is not normally required after this upgrade, but verify the
  detected probes before commissioning.
EOF2
fi

cat <<EOF2

Before starting the monitor:
1. Enable 1-Wire with: sudo raspi-config   (if it is not already enabled)
2. Reboot so the 1-Wire and DS3231 RTC configuration loads.
3. Verify the RTC:
   sudo ${INSTALL_DIR}/verify_rtc.sh
4. Once network time is correct, initialise the RTC if required:
   sudo ${INSTALL_DIR}/verify_rtc.sh --sync-from-system
5. Verify the two DS18B20 probes:
   sudo ${INSTALL_DIR}/configure_temperature_probes.py --list
EOF2

if [[ "${INSTALL_MODE}" == "fresh" ]]; then
  cat <<EOF2
6. Assign the two DS18B20 hardware IDs:
   sudo ${INSTALL_DIR}/configure_temperature_probes.py
7. Run the hardware test:
EOF2
else
  cat <<EOF2
6. If the saved probe assignments are not correct, reassign them with:
   sudo ${INSTALL_DIR}/configure_temperature_probes.py
7. Run the hardware test:
EOF2
fi

cat <<EOF2
   ${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/hydro_monitor.py \\
     --config ${INSTALL_DIR}/config.json --test
8. After the hardware test passes, enable and start both services:
   sudo systemctl enable --now hydro-monitor.service hydro-dashboard.service
9. Open the dashboard from another device on the same home network:
   http://hydro-monitor.local:8080/
   or http://<Pi-IP-address>:8080/

Installed version:
   ${INSTALL_DIR}/VERSION = ${RELEASE_VERSION}

Established Raspberry Pi identity:
   username: hydroponics
   hostname: hydro-monitor
   SSH: ssh hydroponics@hydro-monitor.local

No cloud account or Internet connection is required for the dashboard or local alarms.
Pushover phone notifications are installed but disabled until configured.
After creating a Pushover account and application token, run:
   sudo ${INSTALL_DIR}/configure_pushover.py

EOF2
