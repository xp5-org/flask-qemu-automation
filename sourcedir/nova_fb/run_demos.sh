#!/bin/bash
# Run the standalone nova_fb demos and verify the resulting PNGs.
# Everything is relative to this directory, so it works from any cwd.
#
# NOTE: the variable below is CHECKS, not GROUPS -- GROUPS is a bash builtin
# array of the user's group ids, so assigning to it is silently ignored.
#
# demo/rdos_fbdraw.ini is deliberately EXCLUDED: it boots RDOS and needs the
# console driven (XFER / ASM / RLDR / run), which is the flask testlist's job
# (__testlist__nova_fb_rdosdraw.py). Running it here would just hang at the
# "Filename?" prompt. Its output/rdos*.png is left alone for the same reason.
set -e
cd "$(dirname "$0")"

NOVA=./bin/dgnova-fb
CHECKS="stripes toprow full bank autoinc pixels pixel_ops cursor cursor_xor
text80 text30 text_font"

mkdir -p output
for g in $CHECKS; do rm -f output/${g}*.png; done
rm -f output/stripes_autoinc*.png output/bank*.png

for f in demo/*.ini; do
    case "$f" in
        */rdos_*.ini) echo "=== $f (skipped: needs the testlist) ==="; continue;;
    esac
    echo "=== $f ==="
    "$NOVA" "$f" 2>&1 | grep -vE '^$|Goodbye|^NOVA simulator' || true
done

echo
echo "=== frames written ==="
ls -la output/*.png
echo
python3 verify_frames.py $CHECKS
