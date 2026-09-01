#!/bin/bash
# Rebuilds _toolchain/ from the public sources documented in NOTES.txt.
# Run via the "build_toolchain" test (__testlist__cully_llvm_build_toolchain.py),
# not directly.
#
# Safe to re-run: each stage is skipped if its own completion marker under
# _toolchain/.stage_* already exists, so a killed/timed-out run resumes
# instead of starting over.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLCHAIN="$HERE/_toolchain"

mkdir -p "$TOOLCHAIN"

stage_done() { [ -f "$TOOLCHAIN/.stage_$1" ]; }
mark_stage() { touch "$TOOLCHAIN/.stage_$1"; }

if ! stage_done dgasm; then
    echo "--- building dgasm ---"
    rm -rf "$TOOLCHAIN/dgasm"
    git clone https://github.com/CWood1/dgasm "$TOOLCHAIN/dgasm"
    mkdir -p "$TOOLCHAIN/dgasm/build"
    (cd "$TOOLCHAIN/dgasm/build" && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j"$(nproc)")
    mark_stage dgasm
fi

if ! stage_done backend_clones; then
    echo "--- cloning nova-llvm-backend + eclipse-llvm-backend ---"
    rm -rf "$TOOLCHAIN/nova-llvm-backend" "$TOOLCHAIN/eclipse-llvm-backend"
    git clone https://github.com/cullyrichard/nova-llvm-backend "$TOOLCHAIN/nova-llvm-backend"
    git clone https://github.com/cullyrichard/eclipse-llvm-backend "$TOOLCHAIN/eclipse-llvm-backend"
    mark_stage backend_clones
fi

if ! stage_done llvm_checkout; then
    echo "--- fetching pinned llvm-project commit + applying patch ---"
    rm -rf "$TOOLCHAIN/llvm-project"
    mkdir -p "$TOOLCHAIN/llvm-project"
    (
        cd "$TOOLCHAIN/llvm-project"
        git init
        git remote add origin https://github.com/llvm/llvm-project.git
        git fetch --depth 1 origin 8307b46d3ad5ace00c21e1fec6ef4ef4284290e9
        git checkout FETCH_HEAD
        git apply ../nova-llvm-backend/nova-backend.patch
    )
    mark_stage llvm_checkout
fi

if ! stage_done llvm_build; then
    echo "--- configuring + building clang llc llvm-link opt (this is the slow part) ---"
    rm -rf "$TOOLCHAIN/llvm-build"
    mkdir -p "$TOOLCHAIN/llvm-build"
    (
        cd "$TOOLCHAIN/llvm-build"
        cmake -G Ninja ../llvm-project/llvm \
            -DLLVM_ENABLE_PROJECTS=clang \
            -DLLVM_TARGETS_TO_BUILD=X86 \
            -DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=Eclipse \
            -DCMAKE_BUILD_TYPE=Release \
            -DBUILD_SHARED_LIBS=ON
        ninja clang llc llvm-link opt
    )
    mark_stage llvm_build
fi

touch "$TOOLCHAIN/.bootstrap_complete"
echo "=== toolchain build complete ==="
