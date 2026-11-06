#!/bin/sh
# Makes "The Assistant - Setup Guide.pdf" from install-guide.html with the Mac's Chrome, no window opened.
cd "$(dirname "$0")/.." || exit 1
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="The Assistant - Setup Guide.pdf" "file://$PWD/install-guide/install-guide.html" 2>/dev/null
ls -la "The Assistant - Setup Guide.pdf"
