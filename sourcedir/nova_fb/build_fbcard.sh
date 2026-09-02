#!/usr/bin/env bash
# Rebuilds bin/dgnova-fb with src/fb_card.v's RTL linked in, for the
# Verilator-bridged text-mode rendering path (see BUILD.txt's "VERILATOR
# BRIDGE" section for the full design).
#
# THIS is where editing the framebuffer comes into play in the testlist: a
# change to src/fb_card.v (the RTL) or src/nova_charrom.h (the font, via
# gen_charrom.py) is picked up here and produces a new bin/dgnova-fb, same
# as editing gen_modeswitch.py already picks up a Nova-program change in the
# testlist's other build step. src/fb_bridge.cpp (the C++ seam nova_fb.c
# calls into) is compiled here too, but it is plumbing, not test content --
# nothing about routine RTL/Nova-program iteration should need to touch it.
#
# The SIMH source + the base device patch (nova_fb_device.patch) are
# vendored into temp_simh_src/ on first run and reused after that -- cloning
# is the slow part, not this script's own compile step. Same "vendored,
# falls back to fetching" shape as simhhelpers.py's DGNOVA_BIN, and
# temp_simh_src/ matches this repo's existing /sourcedir/*/temp_*/ gitignore
# convention for pulled-from-GitHub build trees.
#
# Usage: ./build_fbcard.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

SIMH_SRC="$HERE/temp_simh_src"
SIMH_COMMIT="a1f57fa3738ed31148d31126ba1a7278ff845c6d"   # pinned, see BUILD.txt
GEN_DIR="$HERE/temp_fbcard_gen"

if ! command -v verilator >/dev/null 2>&1; then
    echo "ERROR: verilator not found on PATH." >&2
    exit 2
fi

if ! grep -q "nova_fb.c" "$SIMH_SRC/makefile" 2>/dev/null; then
    echo "== vendoring open-simh @ $SIMH_COMMIT (first run only) =="
    rm -rf "$SIMH_SRC"
    git clone https://github.com/open-simh/simh "$SIMH_SRC"
    (cd "$SIMH_SRC" && git fetch --depth 1 origin "$SIMH_COMMIT" && git checkout "$SIMH_COMMIT")
    (cd "$SIMH_SRC" && git apply "$HERE/src/nova_fb_device.patch")
fi

echo "== regenerating the font ROM (C header + RTL hex) =="
python3 gen_charrom.py
python3 gen_charrom_hex.py

echo "== Verilating fb_card.v =="
rm -rf "$GEN_DIR"
verilator --cc src/fb_card.v --top-module fb_card -Isrc -Mdir "$GEN_DIR"

echo "== compiling the RTL model + fb_bridge.cpp into libfbcard.a =="
VROOT="$(verilator --getenv VERILATOR_ROOT)"
(
    cd "$GEN_DIR"
    g++ -std=c++17 -Os -I. -I"$VROOT/include" -I"$VROOT/include/vltstd" \
        -DVM_COVERAGE=0 -DVM_SC=0 -DVM_TIMING=0 \
        -c Vfb_card.cpp Vfb_card___024root__DepSet_*.cpp \
           Vfb_card___024root__Slow.cpp Vfb_card__Syms.cpp \
           "$VROOT/include/verilated.cpp" \
           "$VROOT/include/verilated_threads.cpp" \
           "$HERE/src/fb_bridge.cpp" \
        -I"$HERE/src"
    ar rcs libfbcard.a *.o
)

echo "== pointing the simh build at libfbcard.a =="
sed -i "s|^NOVA_OPT = -I \${NOVAD}.*|NOVA_OPT = -I \${NOVAD} $GEN_DIR/libfbcard.a -lstdc++ -lpthread -latomic|" \
    "$SIMH_SRC/makefile"

echo "== copying the bridge-aware sources into the simh checkout =="
cp src/nova_fb.c "$SIMH_SRC/NOVA/nova_fb.c"
cp src/nova_charrom.h "$SIMH_SRC/NOVA/nova_charrom.h"
cp src/fb_bridge.h "$SIMH_SRC/NOVA/fb_bridge.h"

echo "== make nova =="
(cd "$SIMH_SRC" && make nova)

strip "$SIMH_SRC/BIN/nova"
cp "$SIMH_SRC/BIN/nova" bin/dgnova-fb
echo "OK: bin/dgnova-fb rebuilt with fb_card.v linked in"
