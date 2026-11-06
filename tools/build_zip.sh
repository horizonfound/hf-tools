#!/bin/sh
# Makes the file a photographer uploads in Claude (Settings, Customize, Plugins, + Add, Upload plugin).
# It refuses to build if the plugin would be rejected, or if there are changes that are not committed yet,
# so the file always matches what is on GitHub. The file lands in dist/ (not kept in git).
cd "$(dirname "$0")/.." || exit 1
python3 tools/check_plugin.py || { echo "Not built: fix the STOP lines above."; exit 1; }
if [ -n "$(git status --porcelain plugins/the-engine)" ]; then
  echo "Not built: plugins/the-engine has changes that are not committed. Commit first, so the file matches GitHub."; exit 1
fi
mkdir -p dist
OUT="dist/The-Assistant.zip"
rm -f "$OUT"
git archive --format=zip -o "$OUT" HEAD:plugins/the-engine || exit 1
# check the file itself, unpacked, the same way
TMP="$(mktemp -d)"
unzip -q "$OUT" -d "$TMP" && python3 tools/check_plugin.py "$TMP" >/dev/null || { echo "Not built: the zip itself fails the check."; rm -rf "$TMP" "$OUT"; exit 1; }
rm -rf "$TMP"
echo "Built $OUT from $(git log -1 --format='%h, %cd' --date=format:'%b %e %H:%M')"
ls -la "$OUT"
