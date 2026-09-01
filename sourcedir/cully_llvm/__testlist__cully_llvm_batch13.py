import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Batch 13 of the c-testsuite (github.com/c-testsuite/c-testsuite)
# single-exec battery run against cullyrichard's nova-llvm-backend (a real
# LLVM/Clang backend for the Data General Nova, extending the sibling
# eclipse-llvm-backend project). See ../cully_llvm/NOTES.txt for the full
# pipeline (vendor/ -> wrap_vendor_tests.py -> src/ -> regen_ctestsuite.py ->
# gen/ -> screen_runtime.py -> stable_pass.txt -> this file, via
# gen_testlists.py -- generated, not hand-maintained; re-run gen_testlists.py
# after re-screening rather than hand-editing this file).
# Only tests that built AND ran to a stable PASS (screen_runtime.py) are
# here -- see BUILD_STATUS.md / RUNTIME_STATUS.md for what got excluded and
# why (compile gaps in this LLVM backend, or a runtime FAIL/HANG).
#
# This is the LLVM-backend counterpart to ../nova_ctestsuite/ (same battery,
# the older PCC-for-Nova pipeline) -- the two are independent, see this
# directory's own NOTES.txt for why finishing one isn't a prerequisite for
# the other.

CONFIG = {
    "parent": "cully_llvm",
    "projdir": "cully_llvm",
    "instance_name": "nova1",
    "function": "batch_13",
    # Each step pair here is one independent test's build+run, not a
    # dependent chain -- one test's failure shouldn't skip the rest of the
    # chunk. See test_runner.py's continue_on_failure handling.
    "continue_on_failure": True,
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {
        "project": {
            "_rel": "{projdir}",
        }
    },
    "steps": [
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00127.c [portable, c89] -- int c;",
            "param": {
                "name": "nova1",
                "script_path": "{projbasedir}{projdir}/gen/ct00127.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00127 printed \"00127: PASS\" to its console",
            "param": {
                "name": "nova1",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00128.c [portable, c99] -- int a;",
            "param": {
                "name": "nova2",
                "script_path": "{projbasedir}{projdir}/gen/ct00128.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00128 printed \"00128: PASS\" to its console",
            "param": {
                "name": "nova2",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00129.c [portable, c89, needs-cpp] -- typedef struct s s;",
            "param": {
                "name": "nova3",
                "script_path": "{projbasedir}{projdir}/gen/ct00129.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00129 printed \"00129: PASS\" to its console",
            "param": {
                "name": "nova3",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00130.c [portable, c89] -- char arr[2][4], (*p)[4], *q;",
            "param": {
                "name": "nova4",
                "script_path": "{projbasedir}{projdir}/gen/ct00130.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00130 printed \"00130: PASS\" to its console",
            "param": {
                "name": "nova4",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00131.c [portable, c99, needs-libc, needs-cpp] -- #include <stdio.h>",
            "param": {
                "name": "nova5",
                "script_path": "{projbasedir}{projdir}/gen/ct00131.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00131 printed \"00131: PASS\" to its console",
            "param": {
                "name": "nova5",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00132.c [portable, c99, needs-libc, needs-cpp] -- #include <stdio.h>",
            "param": {
                "name": "nova6",
                "script_path": "{projbasedir}{projdir}/gen/ct00132.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00132 printed \"00132: PASS\" to its console",
            "param": {
                "name": "nova6",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00133.c [portable, c99] -- int i;",
            "param": {
                "name": "nova7",
                "script_path": "{projbasedir}{projdir}/gen/ct00133.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00133 printed \"00133: PASS\" to its console",
            "param": {
                "name": "nova7",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00134.c [portable, c99] -- long i;",
            "param": {
                "name": "nova8",
                "script_path": "{projbasedir}{projdir}/gen/ct00134.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00134 printed \"00134: PASS\" to its console",
            "param": {
                "name": "nova8",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00135.c [portable, c99] -- long long i;",
            "param": {
                "name": "nova9",
                "script_path": "{projbasedir}{projdir}/gen/ct00135.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00135 printed \"00135: PASS\" to its console",
            "param": {
                "name": "nova9",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "description": "upstream c-testsuite tests/single-exec/00136.c [portable, c89, needs-cpp] -- #define FOO",
            "param": {
                "name": "nova10",
                "script_path": "{projbasedir}{projdir}/gen/ct00136.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00136 printed \"00136: PASS\" to its console",
            "param": {
                "name": "nova10",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
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
