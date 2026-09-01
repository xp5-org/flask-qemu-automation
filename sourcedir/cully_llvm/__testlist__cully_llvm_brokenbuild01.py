import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Broken-build batch 1 of the c-testsuite battery: tests that
# never produced a gen/*.ini at all -- nova-cc (clang/llvm-link/opt/llc/
# reorder_asm.py/dgasm) rejected them outright (see BUILD_STATUS.md for
# each one's actual error -- an LLVM backend codegen gap, a missing libc
# function this runtime doesn't implement, or a header it doesn't have).
# There is no SimH .ini to run for these, so each step here re-invokes
# nova-cc LIVE against src/{base}.c via test_hostbuild and asserts it
# still fails -- that is the expected, currently-correct state, not a
# testlist bug.
#
# SAME continue_on_failure AS THE knownissues TESTLISTS (see gen_testlists.py's
# own header) -- every step here is expected to fail on its own, so one
# test_hostbuild's abort flag no longer skips the rest of the chunk.
#
# This is the LLVM-backend counterpart to ../nova_ctestsuite/ -- see this
# directory's own NOTES.txt.

CONFIG = {
    "parent": "cully_llvm",
    "projdir": "cully_llvm",
    "instance_name": "nova1",
    "function": "broken_build_01",
    "continue_on_failure": True,
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {
        "project": {
            "_rel": "{projdir}",
        }
    },
    "steps": [
        {
            "action": "test_hostbuild",
            "description": "BROKEN BUILD -- expect this to keep failing to compile/assemble (/testsrc/sourcedir/cully_llvm/src/ct00104.c:7:2: error: use of undeclared identifier 'int64_t') -- upstream c-testsuite tests/single-exec/00104.c [portable, c99, needs-libc, needs-cpp] -- #include <stdint.h> -- if it now builds, move ct00104 from build_failures.txt to stable_pass.txt/known_issues.txt (via regen_ctestsuite.py + screen_runtime.py) and re-run gen_testlists.py",
            "param": {
                "command": "LLVM_BUILD={projbasedir}{projdir}/_toolchain/llvm-build PATH={projbasedir}{projdir}/_toolchain/dgasm/build:$PATH {projbasedir}{projdir}/_toolchain/nova-llvm-backend/nova-toolchain/nova-cc -t nova3 -o /tmp/cully_llvm_brokenbuild_ct00104.simh {projbasedir}{projdir}/src/ct00104.c",
                "timeout": 60
            },
            "subaction": ""
        },
        {
            "action": "test_hostbuild",
            "description": "BROKEN BUILD -- expect this to keep failing to compile/assemble (/testsrc/sourcedir/cully_llvm/src/ct00174.c:2:10: fatal error: 'math.h' file not found) -- upstream c-testsuite tests/single-exec/00174.c [portable, c99, needs-libc, needs-cpp] -- #include <stdio.h> -- if it now builds, move ct00174 from build_failures.txt to stable_pass.txt/known_issues.txt (via regen_ctestsuite.py + screen_runtime.py) and re-run gen_testlists.py",
            "param": {
                "command": "LLVM_BUILD={projbasedir}{projdir}/_toolchain/llvm-build PATH={projbasedir}{projdir}/_toolchain/dgasm/build:$PATH {projbasedir}{projdir}/_toolchain/nova-llvm-backend/nova-toolchain/nova-cc -t nova3 -o /tmp/cully_llvm_brokenbuild_ct00174.simh {projbasedir}{projdir}/src/ct00174.c",
                "timeout": 60
            },
            "subaction": ""
        },
        {
            "action": "test_hostbuild",
            "description": "BROKEN BUILD -- expect this to keep failing to compile/assemble (/testsrc/sourcedir/cully_llvm/src/ct00187.c:5:14: error: call to undeclared library function 'fopen' with type 'FILE *(const char *, const char *)' (aka 'struct FILE *(const char *, const char *)'); ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]) -- upstream c-testsuite tests/single-exec/00187.c [portable, c89, needs-libc, needs-cpp] -- #include <stdio.h> -- if it now builds, move ct00187 from build_failures.txt to stable_pass.txt/known_issues.txt (via regen_ctestsuite.py + screen_runtime.py) and re-run gen_testlists.py",
            "param": {
                "command": "LLVM_BUILD={projbasedir}{projdir}/_toolchain/llvm-build PATH={projbasedir}{projdir}/_toolchain/dgasm/build:$PATH {projbasedir}{projdir}/_toolchain/nova-llvm-backend/nova-toolchain/nova-cc -t nova3 -o /tmp/cully_llvm_brokenbuild_ct00187.simh {projbasedir}{projdir}/src/ct00187.c",
                "timeout": 60
            },
            "subaction": ""
        },
        {
            "action": "test_hostbuild",
            "description": "BROKEN BUILD -- expect this to keep failing to compile/assemble (/testsrc/sourcedir/cully_llvm/src/ct00204.c:394:9: error: integer literal is too large to be represented in any integer type) -- upstream c-testsuite tests/single-exec/00204.c [portable, c99, needs-libc, needs-cpp] -- // This program is designed to test some arm64-specific things, such as the -- if it now builds, move ct00204 from build_failures.txt to stable_pass.txt/known_issues.txt (via regen_ctestsuite.py + screen_runtime.py) and re-run gen_testlists.py",
            "param": {
                "command": "LLVM_BUILD={projbasedir}{projdir}/_toolchain/llvm-build PATH={projbasedir}{projdir}/_toolchain/dgasm/build:$PATH {projbasedir}{projdir}/_toolchain/nova-llvm-backend/nova-toolchain/nova-cc -t nova3 -o /tmp/cully_llvm_brokenbuild_ct00204.simh {projbasedir}{projdir}/src/ct00204.c",
                "timeout": 60
            },
            "subaction": ""
        },
        {
            "action": "test_hostbuild",
            "description": "BROKEN BUILD -- expect this to keep failing to compile/assemble (/tmp/tmp.DVg1H3tghb/out_r.s:8 - Address out of range. Got 393, should be 0 - 255: JSR @main_SLOT,0) -- upstream c-testsuite tests/single-exec/00216.c [portable, needs-libc, needs-cpp] -- typedef unsigned char u8; -- if it now builds, move ct00216 from build_failures.txt to stable_pass.txt/known_issues.txt (via regen_ctestsuite.py + screen_runtime.py) and re-run gen_testlists.py",
            "param": {
                "command": "LLVM_BUILD={projbasedir}{projdir}/_toolchain/llvm-build PATH={projbasedir}{projdir}/_toolchain/dgasm/build:$PATH {projbasedir}{projdir}/_toolchain/nova-llvm-backend/nova-toolchain/nova-cc -t nova3 -o /tmp/cully_llvm_brokenbuild_ct00216.simh {projbasedir}{projdir}/src/ct00216.c",
                "timeout": 60
            },
            "subaction": ""
        },
        {
            "action": "test_terminate_all",
            "description": "Tear down every Nova SIMH instance this batch started",
            "param": {},
            "subaction": ""
        },
    ],
}

PATHS = init_test_env(CONFIG, __name__)
