#!/usr/bin/env bash
# Host-side Retro68 build for the M68K Cube Rotate demo.
#
# Cross-compiles cuberotate.c to a classic Mac GUI app and an HFS .dsk, then
# copies the .dsk next to this script as CubeRotate.dsk so the test list can
# attach it to QEMU. Idempotent: safe to re-run.
#
# Usage: ./build.sh   (or:  TOOLCHAIN=/path/to/retro68.toolchain.cmake ./build.sh)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLCHAIN="${TOOLCHAIN:-/opt/Retro68/toolchain/m68k-apple-macos/cmake/retro68.toolchain.cmake}"
BUILD_DIR="$HERE/build"

if [ ! -f "$TOOLCHAIN" ]; then
    echo "ERROR: Retro68 toolchain file not found: $TOOLCHAIN" >&2
    echo "Build the toolchain first (Retro68 build-toolchain.bash)." >&2
    exit 2
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
# Show the cmake configure and the FULL compiler command lines (VERBOSE=1) in
# the report — every -mcpu / -m*-float / -I / linker flag is then visible.
cmake .. -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN"
make VERBOSE=1

# Publish the artifacts the runner cares about next to the source.
cp -f "$BUILD_DIR/CubeRotate.dsk" "$HERE/CubeRotate.raw.dsk"
cp -f "$BUILD_DIR/CubeRotate.bin" "$HERE/CubeRotate.bin" 2>/dev/null || true

# Retro68 emits a RAW HFS image; classic Mac OS only auto-mounts a SCSI disk
# that carries an Apple Partition Map WITH a real disk driver (see
# wrap_hfs_apm.py's docstring — a driver-less HFS partition is silently
# skipped by the ROM's SCSI Manager). Wrap the raw volume,
# reusing the driver from the project's known-bootable maindisk.img, so the
# q800 mounts it on the desktop as "CubeRotate". This is the disk the test
# list attaches (hdd2_path).
python3 /testsrc/disk_artifacts/bin/wrap_hfs_apm.py \
    "$HERE/CubeRotate.raw.dsk" "$HERE/CubeRotate.dsk" CubeRotate
echo "OK: $HERE/CubeRotate.dsk (partitioned, auto-mounting)"
