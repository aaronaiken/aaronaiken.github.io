# Off-PA backups — the local (Mac) leg

This is one of **two** legs that get the Cockpit's gitignored server-state
off PythonAnywhere:

| Leg | Runs on | Where it lands | Set up via |
|---|---|---|---|
| **Bunny** | PA (cron) | Bunny storage-only zone | `backup_offsite.py` + `BUNNY_BACKUP_*` env |
| **Local** (this dir) | your Mac (launchd) | `~/pa-backups/` | `pull-backups.sh` + the plist |

Together with PA's own `~/db-backups/` sweep (`backup_all.py`), every at-risk
file exists in **three** places. Canonical plan: `.kt/BACKUP_AND_RECOVERY.md` §5.

## Why the Mac *pulls* instead of PA *pushing*

PA is always up and reachable; a laptop isn't. A PA→Mac push would silently
miss every window the Mac is asleep or on another network. A Mac→PA **pull**
grabs the backups whenever the Mac is awake, using the passwordless SSH key
the Cockpit deploy flow already relies on. PA is the always-on side, so it's
the side you reach *toward*.

## One-time setup

1. **Confirm SSH works** (paid PA accounts have SSH; the key is already
   installed if `git pull` on PA works passwordlessly):

   ```bash
   ssh aaronaiken@ssh.pythonanywhere.com 'ls db-backups/ | tail -3'
   ```

   If that prints recent `*.YYYYMMDD-HHMMSS` files, you're good. If it prompts
   for a password, add your key: `ssh-copy-id aaronaiken@ssh.pythonanywhere.com`.

2. **Test the pull manually:**

   ```bash
   ./pull-backups.sh
   ls -la ~/pa-backups/ | tail
   ```

3. **Schedule it** (daily 10:00 local + at load):

   ```bash
   cp com.aaronaiken.pa-backups.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.aaronaiken.pa-backups.plist
   ```

   Verify it's registered: `launchctl list | grep pa-backups`.

## Config (env overrides — all optional)

| Var | Default | Meaning |
|---|---|---|
| `PA_SSH` | `aaronaiken@ssh.pythonanywhere.com` | SSH target |
| `PA_REMOTE_DIR` | `db-backups/` | remote dir (relative to PA home) |
| `LOCAL_DIR` | `$HOME/pa-backups` | where the copy lands |

## Notes

- **No `--delete`.** The Mac keeps a *deeper* history than PA's 30-per-file
  prune — old snapshots are the point of a backup. Trim `~/pa-backups/` by
  hand if it ever grows large (`du -sh ~/pa-backups`).
- **Logs:** `~/pa-backups/pull.log` (script) + `launchd.{out,err}.log` (agent).
- **Uninstall:** `launchctl unload ~/Library/LaunchAgents/com.aaronaiken.pa-backups.plist && rm ~/Library/LaunchAgents/com.aaronaiken.pa-backups.plist`
- **Moved the repo?** Update the script path inside the plist and reload.

## Restore

To restore a file from the local copy, it's just a normal file — pick the
timestamp you want and copy it back (stop Flask on PA first). Full procedure:
`.kt/BACKUP_AND_RECOVERY.md` §4.
