#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
RELEASE_VERSION="$(tr -d '\r\n' < VERSION)"

TEST_COUNT=14

echo "[1/${TEST_COUNT}] Python syntax"
python3 -m py_compile \
  hydro_version.py merge_config.py hydro_monitor.py hydro_dashboard.py \
  configure_pushover.py configure_temperature_probes.py \
  test_logic.py test_dashboard.py test_notifications.py \
  test_temperature_configuration.py test_power_loss_recovery.py \
  test_upgrade_installation.py test_release_structure.py test_continuity.py

echo "[2/${TEST_COUNT}] Monitor and dual-probe logic"
python3 test_logic.py

echo "[3/${TEST_COUNT}] Dashboard, history, RTC and backup logic"
python3 test_dashboard.py

echo "[4/${TEST_COUNT}] Pushover mock tests"
python3 test_notifications.py

echo "[5/${TEST_COUNT}] Probe assignment utility"
python3 test_temperature_configuration.py

echo "[6/${TEST_COUNT}] Power-loss resilience"
python3 test_power_loss_recovery.py

echo "[7/${TEST_COUNT}] Upgrade preservation"
python3 test_upgrade_installation.py

echo "[8/${TEST_COUNT}] Release structure"
python3 test_release_structure.py

echo "[9/${TEST_COUNT}] Project identity and continuity"
python3 test_continuity.py

echo "[10/${TEST_COUNT}] JSON and shell syntax"
python3 -m json.tool config.json >/dev/null
python3 -m json.tool pushover_secrets.example.json >/dev/null
bash -n install.sh uninstall.sh configure_rtc.sh verify_rtc.sh run_release_tests.sh

echo "[11/${TEST_COUNT}] Dashboard JavaScript syntax"
if command -v node >/dev/null 2>&1; then
  node --check dashboard.js
else
  echo "Node.js is not installed; JavaScript syntax check skipped on this machine."
fi

echo "[12/${TEST_COUNT}] VERSION single-source check"
python3 - <<'PY'
from pathlib import Path
from hydro_version import VERSION
value = Path("VERSION").read_text(encoding="utf-8").strip()
assert VERSION == value
for name in ("hydro_monitor.py", "hydro_dashboard.py", "configure_pushover.py"):
    text = Path(name).read_text(encoding="utf-8")
    assert "from hydro_version import VERSION" in text, name
print(f"Single-source VERSION check passed: {VERSION}")
PY

echo "[13/${TEST_COUNT}] Offline systemd unit syntax"
if command -v systemd-analyze >/dev/null 2>&1; then
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "${tmpdir}"' EXIT
  sed \
    -e 's/REPLACE_WITH_YOUR_USERNAME/root/g' \
    -e "s#WorkingDirectory=/opt/hydro-monitor#WorkingDirectory=${PROJECT_DIR}#" \
    -e "s#/opt/hydro-monitor/venv/bin/python /opt/hydro-monitor/hydro_monitor.py --config /opt/hydro-monitor/config.json#/usr/bin/python3 ${PROJECT_DIR}/hydro_monitor.py --config ${PROJECT_DIR}/config.json#" \
    -e 's#ReadWritePaths=/var/log/hydro-monitor /var/lib/hydro-monitor#ReadWritePaths=/tmp#' \
    -e '/SupplementaryGroups=/d' \
    hydro-monitor.service > "${tmpdir}/hydro-monitor.service"
  sed \
    -e 's/REPLACE_WITH_YOUR_USERNAME/root/g' \
    -e "s#WorkingDirectory=/opt/hydro-monitor#WorkingDirectory=${PROJECT_DIR}#" \
    -e "s#/opt/hydro-monitor/venv/bin/python /opt/hydro-monitor/hydro_dashboard.py --config /opt/hydro-monitor/config.json#/usr/bin/python3 ${PROJECT_DIR}/hydro_dashboard.py --config ${PROJECT_DIR}/config.json#" \
    -e 's#ReadWritePaths=/var/log/hydro-monitor /var/lib/hydro-monitor#ReadWritePaths=/tmp#' \
    hydro-dashboard.service > "${tmpdir}/hydro-dashboard.service"
  export TERM="${TERM:-xterm}"
  systemd-analyze verify \
    "${tmpdir}/hydro-monitor.service" \
    "${tmpdir}/hydro-dashboard.service"
  rm -rf "${tmpdir}"
  trap - EXIT
else
  echo "systemd-analyze is unavailable; offline unit check skipped on this machine."
fi

echo "[14/${TEST_COUNT}] Package checksums"
sha256sum -c SHA256SUMS

echo "Hydro Monitor ${RELEASE_VERSION} packaged release tests passed."
