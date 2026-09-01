import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Provisions _toolchain/ (dgasm, nova-llvm-backend, eclipse-llvm-backend,
# patched llvm-project + ninja build) from the public sources documented in
# NOTES.txt. Not part of the normal test battery -- run this manually once
# after a fresh checkout/restore, or whenever __testparent__.py's
# description flags _toolchain/ as missing.
#
# bootstrap_toolchain.sh is resumable: if this test times out or gets
# aborted partway, re-running it picks up from the last completed stage
# instead of starting over.

CONFIG = {
    "parent": "cully_llvm",
    "projdir": "cully_llvm",
    "function": "build_toolchain",
    "description": "Rebuilds _toolchain/ from public sources (dgasm, "
        "nova-llvm-backend, eclipse-llvm-backend, patched llvm-project). "
        "Long-running (LLVM build); safe to re-run if aborted -- resumes "
        "from the last completed stage.",
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {
        "project": {
            "_rel": "{projdir}",
        }
    },
    "steps": [
        {
            "action": "test_hostbuild",
            "description": "Run bootstrap_toolchain.sh (dgasm -> backend "
                "clones -> llvm-project checkout+patch -> ninja build)",
            "param": {
                "command": "./bootstrap_toolchain.sh",
                "cwd": "{projbasedir}{projdir}",
                "timeout": "10800",
            },
            "subaction": ""
        },
    ],
}

PATHS = init_test_env(CONFIG, __name__)
