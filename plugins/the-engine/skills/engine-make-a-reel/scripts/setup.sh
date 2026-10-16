#!/usr/bin/env bash
# The Engine: one-time install of the free tools the reel builder uses.
# Mac: uses Homebrew. Windows: run in Git Bash; uses winget.
set -e
echo "This installs ffmpeg, Whisper and pycapcut. It can take 10-30 minutes and a few GB. Keep the laptop plugged in."
case "$(uname -s)" in
  Darwin)
    command -v brew >/dev/null 2>&1 || { echo "Installing Homebrew first..."; /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; }
    brew install ffmpeg python@3.12
    python3 -m pip install --upgrade pip
    python3 -m pip install openai-whisper pycapcut
    ;;
  MINGW*|MSYS*|CYGWIN*)
    winget install -e --id Gyan.FFmpeg
    winget install -e --id Python.Python.3.12
    python -m pip install --upgrade pip
    python -m pip install openai-whisper pycapcut
    ;;
  *) echo "Unsupported OS"; exit 1;;
esac
echo "Done. Now install CapCut from capcut.com (not the app store), open it once, close it, and run check-setup.sh."
