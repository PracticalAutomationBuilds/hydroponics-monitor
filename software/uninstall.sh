#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/hydro-monitor"
LOG_DIR="/var/log/hydro-monitor"
STATE_DIR="/var/lib/hydro-monitor"
SECRETS_DIR="/etc/hydro-monitor"
MONITOR_SERVICE="/etc/systemd/system/hydro-monitor.service"
DASHBOARD_SERVICE="/etc/systemd/system/hydro-dashboard.service"

PURGE=false
ASSUME_YES=false

usage() {
  cat <<'EOF2'
Usage:
  sudo ./uninstall.sh
  sudo ./uninstall.sh --purge
  sudo ./uninstall.sh --purge --yes

Default mode removes Hydro Monitor software and systemd services while preserving
configuration, logs/history, runtime state and Pushover secrets.

--purge  Also deletes all Hydro Monitor configuration, logs/history, state and secrets.
--yes    With --purge, skip the interactive PURGE confirmation.

The uninstaller does not remove shared Raspberry Pi OS packages, disable I2C or
1-Wire, remove Avahi, or alter the Raspberry Pi hostname/user account.
EOF2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge)
      PURGE=true
      ;;
    --yes)
      ASSUME_YES=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 2
      ;;
  esac
  shift
done

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this uninstaller with sudo: sudo ./uninstall.sh"
  exit 1
fi

if [[ "${ASSUME_YES}" == true && "${PURGE}" != true ]]; then
  echo "--yes is only valid together with --purge."
  exit 2
fi

INSTALLED_VERSION="unknown"
if [[ -f "${INSTALL_DIR}/VERSION" ]]; then
  INSTALLED_VERSION="$(tr -d '\r\n' < "${INSTALL_DIR}/VERSION")"
elif [[ -f "${INSTALL_DIR}/hydro_monitor.py" ]]; then
  INSTALLED_VERSION="$(sed -nE 's/^VERSION[[:space:]]*=[[:space:]]*["'\'' ]([^"'\'' ]+)["'\'' ].*/\1/p' "${INSTALL_DIR}/hydro_monitor.py" | head -n 1 || true)"
  INSTALLED_VERSION="${INSTALLED_VERSION:-legacy/unknown}"
fi

echo "Hydro Monitor uninstaller"
echo "Installed version: ${INSTALLED_VERSION}"

if [[ "${PURGE}" == true ]]; then
  cat <<EOF2

WARNING: --purge permanently deletes:
  ${INSTALL_DIR}
  ${LOG_DIR}
  ${STATE_DIR}
  ${SECRETS_DIR}

This includes sensor assignments, user configuration, historical readings,
event logs and Pushover credentials.
EOF2

  if [[ "${ASSUME_YES}" != true ]]; then
    if [[ ! -t 0 ]]; then
      echo "Interactive confirmation is unavailable. Re-run with --purge --yes if intended."
      exit 1
    fi
    read -r -p 'Type PURGE to continue: ' confirmation
    if [[ "${confirmation}" != "PURGE" ]]; then
      echo "Purge cancelled."
      exit 1
    fi
  fi
fi

echo "Stopping and disabling Hydro Monitor services..."
systemctl disable --now hydro-dashboard.service hydro-monitor.service >/dev/null 2>&1 || true
rm -f "${MONITOR_SERVICE}" "${DASHBOARD_SERVICE}"
systemctl daemon-reload
systemctl reset-failed hydro-monitor.service hydro-dashboard.service >/dev/null 2>&1 || true

if [[ "${PURGE}" == true ]]; then
  echo "Removing Hydro Monitor software and data..."
  rm -rf "${INSTALL_DIR}" "${LOG_DIR}" "${STATE_DIR}" "${SECRETS_DIR}"
  echo "Hydro Monitor has been purged."
else
  echo "Removing installed Hydro Monitor software while preserving user data..."
  rm -rf \
    "${INSTALL_DIR}/venv" \
    "${INSTALL_DIR}/__pycache__"

  for name in \
    hydro_monitor.py \
    hydro_dashboard.py \
    hydro_version.py \
    VERSION \
    dashboard.html \
    dashboard.css \
    dashboard.js \
    requirements.txt \
    configure_rtc.sh \
    verify_rtc.sh \
    configure_pushover.py \
    configure_temperature_probes.py \
    merge_config.py \
    pushover_secrets.example.json
  do
    rm -f "${INSTALL_DIR}/${name}"
  done

  cat <<EOF2

Software removed. Preserved data remains in:
  ${INSTALL_DIR}/config.json and configuration backups
  ${LOG_DIR}
  ${STATE_DIR}
  ${SECRETS_DIR}

A later installation can reuse the preserved configuration.
EOF2
fi

cat <<'EOF2'

The following shared/system facilities were deliberately left unchanged:
- Raspberry Pi OS packages installed as dependencies
- Avahi/mDNS
- I2C configuration and DS3231 RTC overlay
- 1-Wire configuration
- Raspberry Pi hostname and user account
- hydro-monitor-secrets system group
EOF2
