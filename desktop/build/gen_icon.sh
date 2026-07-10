#!/bin/bash
# Generate build/icon.png (1024x1024) for the Director-bot desktop app:
# dark slate rounded square, gold diagonal clapper stripe, monospace "D".
# Pure ffmpeg lavfi — no other tooling.
set -euo pipefail
cd "$(dirname "$0")"

FFMPEG="${FFMPEG:-ffmpeg}"

# Gold-ish stripe band on dark slate
STRIPE="if(lt(Y,204),if(lt(mod(X+Y,150),75),212,20),12)"
ALPHA="if(lte(hypot(X-clip(X,160,W-161),Y-clip(Y,160,H-161)),160),255,0)"
BASE="geq=r='${STRIPE}':g='if(lt(Y,204),if(lt(mod(X+Y,150),75),168,20),13)':b='if(lt(Y,204),if(lt(mod(X+Y,150),75),75,20),16)':a='${ALPHA}',drawbox=x=0:y=204:w=1024:h=10:color=0x0b0b0b:t=fill"

INK="0xd4a84b"
if "$FFMPEG" -hide_banner -filters 2>/dev/null | grep -q " drawtext "; then
  FONT="/System/Library/Fonts/Menlo.ttc"
  [ -f "$FONT" ] || FONT="/System/Library/Fonts/SFNSMono.ttf"
  if [ ! -f "$FONT" ]; then
    echo "gen_icon.sh: no monospace system font found" >&2
    exit 1
  fi
  GLYPH="drawtext=fontfile='${FONT}':text='D':fontcolor=${INK}:fontsize=560:x=(w-text_w)/2:y=204+((h-204-text_h)/2)"
else
  # Blocky "D" from drawbox segments
  GLYPH="drawbox=x=300:y=340:w=96:h=420:color=${INK}:t=fill"
  GLYPH="${GLYPH},drawbox=x=300:y=340:w=300:h=96:color=${INK}:t=fill"
  GLYPH="${GLYPH},drawbox=x=300:y=664:w=300:h=96:color=${INK}:t=fill"
  GLYPH="${GLYPH},drawbox=x=540:y=420:w=96:h=260:color=${INK}:t=fill"
fi

"$FFMPEG" -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=0x0c0d10:s=1024x1024:d=1,format=rgba" \
  -vf "${BASE},${GLYPH}" \
  -frames:v 1 icon.png

echo "wrote $(pwd)/icon.png"
