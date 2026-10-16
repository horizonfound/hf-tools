#!/usr/bin/env bash
# The Engine: checks the tools the reel builder needs. Prints one line per item.
ok(){ echo "OK       $1"; }
miss(){ echo "MISSING  $1"; }

command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg ($(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}'))" || miss "ffmpeg"
command -v whisper >/dev/null 2>&1 && ok "whisper" || miss "whisper"
python3 -c "import pycapcut" >/dev/null 2>&1 && ok "pycapcut" || miss "pycapcut"

case "$(uname -s)" in
  Darwin)
    ROOT="$HOME/Movies/CapCut/User Data/Projects/com.lveditor.draft"
    [ -d "$ROOT" ] && ok "CapCut draft folder: $ROOT" || miss "CapCut draft folder (install CapCut and open it once)"
    if [ -d "/Applications/CapCut.app" ]; then
      V=$(defaults read /Applications/CapCut.app/Contents/Info.plist CFBundleShortVersionString 2>/dev/null)
      ok "CapCut app ${V:-installed}"
    else miss "CapCut app"; fi
    CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
    echo "INFO     chip: $CHIP"
    echo "INFO     macOS: $(sw_vers -productVersion 2>/dev/null)"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    echo "INFO     Windows: read the draft folder from CapCut settings > Draft location"
    ;;
  *) echo "INFO     $(uname -s): unsupported for CapCut drafts";;
esac
df -h "$HOME" 2>/dev/null | awk 'NR==2{print "INFO     free space: "$4}'
