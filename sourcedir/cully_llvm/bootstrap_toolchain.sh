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

# only one instance lock
exec 200>"$TOOLCHAIN/.bootstrap.lock"
if ! flock -n 200; then
    echo "another bootstrap_toolchain.sh is already running against this _toolchain/ -- waiting for it to finish..."
    flock 200
fi

stage_done() { [ -f "$TOOLCHAIN/.stage_$1" ]; }
mark_stage() { touch "$TOOLCHAIN/.stage_$1"; }

# dgasm is pinned the same way llvm-project already was -- fetched by exact
# commit rather than a plain `git clone` of whatever HEAD happens to be.
# Commits below are the combination verified to build a working nova-cc
# (nova-cc's own SAVE/dgasm incompatibility -- see backend_clones below --
# is exactly what an unpinned nova-llvm-backend clone silently ran into).
DGASM_COMMIT="2e6fa34b78b573ccf8a886b2caf052ef5d10bd6b"

if ! stage_done dgasm; then
    echo "--- building dgasm (pinned) ---"
    rm -rf "$TOOLCHAIN/dgasm"
    mkdir -p "$TOOLCHAIN/dgasm"
    (
        cd "$TOOLCHAIN/dgasm"
        git init
        git remote add origin https://github.com/CWood1/dgasm
        git fetch --depth 1 origin "$DGASM_COMMIT"
        git checkout FETCH_HEAD
    )
    mkdir -p "$TOOLCHAIN/dgasm/build"
    (cd "$TOOLCHAIN/dgasm/build" && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j"$(nproc)")
    mark_stage dgasm
fi

if ! stage_done backend_clones; then
    echo "--- extracting vendored nova-llvm-backend + eclipse-llvm-backend ---"
    # These two are vendored (vendor/*.tar.gz), not git-fetched like dgasm/
    # llvm-project above/below: the exact commits needed are not reachable
    # from origin at all, confirmed via `git ls-remote` -- nova-llvm-backend
    # e3a35fe2fb340c9e675affd520a80ae3ecb22517 is a local fix (for the SAVE
    # instruction dgasm's opcode table only allows for CPU_ECLIPSE_S140, not
    # the nova3 this project targets -- current upstream emits it
    # unconditionally again) that was never pushed, and origin's
    # eclipse-llvm-backend HEAD has since moved to an unrelated commit.
    # `git fetch --depth 1 origin <sha>` for either fails with
    # "not our ref" -- there is nothing upstream left to fetch.
    rm -rf "$TOOLCHAIN/nova-llvm-backend" "$TOOLCHAIN/eclipse-llvm-backend"
    tar xzf "$HERE/vendor/nova-llvm-backend-e3a35fe2.tar.gz" -C "$TOOLCHAIN"
    tar xzf "$HERE/vendor/eclipse-llvm-backend-b7e3f846.tar.gz" -C "$TOOLCHAIN"
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
