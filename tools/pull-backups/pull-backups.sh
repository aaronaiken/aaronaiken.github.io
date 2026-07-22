#!/usr/bin/env bash
#
# pull-backups.sh — the LOCAL leg of the off-PA backup plan.
#
# The Mac PULLS ~/db-backups/ from PythonAnywhere over SSH. Pull (not push)
# on purpose: PA is always up and reachable, this Mac is not — a laptop that's
# asleep or on a different network can't receive a push, but it can reach out
# and grab whenever it happens to be awake. Passwordless SSH Mac->PA is
# assumed (key already installed; the Cockpit deploy flow uses it).
#
# Pairs with backup_offsite.py (the Bunny leg, which runs ON PA). Between the
# two, every gitignored server-state file exists in three places: PA disk,
# Bunny storage, and this Mac.
#
# rsync runs WITHOUT --delete on purpose: the Mac keeps a DEEPER history than
# PA's 30-per-file prune. Local disk is cheap; old snapshots are the whole
# point of a backup. Prune ~/pa-backups/ by hand if it ever gets large.
#
# Config via env (all optional — defaults target a standard PA paid account):
#   PA_SSH        SSH target                (default aaronaiken@ssh.pythonanywhere.com)
#   PA_REMOTE_DIR remote dir, relative home (default db-backups/)
#   LOCAL_DIR     where to land the copy    (default $HOME/pa-backups)
#
# Manual run:   ./pull-backups.sh
# Scheduled:    see com.aaronaiken.pa-backups.plist + README.md

set -euo pipefail

PA_SSH="${PA_SSH:-aaronaiken@ssh.pythonanywhere.com}"
PA_REMOTE_DIR="${PA_REMOTE_DIR:-db-backups/}"
LOCAL_DIR="${LOCAL_DIR:-$HOME/pa-backups}"
LOG_FILE="$LOCAL_DIR/pull.log"

mkdir -p "$LOCAL_DIR"

stamp() { date '+%Y-%m-%dT%H:%M:%S'; }
log() { echo "$(stamp) $*" | tee -a "$LOG_FILE"; }

log "pull start: ${PA_SSH}:${PA_REMOTE_DIR} -> ${LOCAL_DIR}"

# -a archive, -z compress, --partial resume, -h human sizes.
# BatchMode + short timeout so a sleeping/offline Mac fails fast + quietly
# instead of hanging a scheduled run.
if rsync -azh --partial --stats \
    -e "ssh -o BatchMode=yes -o ConnectTimeout=20" \
    "${PA_SSH}:${PA_REMOTE_DIR}" "${LOCAL_DIR}/" >>"$LOG_FILE" 2>&1; then
    count=$(find "$LOCAL_DIR" -type f ! -name 'pull.log' | wc -l | tr -d ' ')
    log "pull complete: ${count} files now in ${LOCAL_DIR}"
    exit 0
else
    rc=$?
    log "pull FAILED (rsync exit ${rc}) — PA unreachable or SSH not set up? See above."
    exit "$rc"
fi
