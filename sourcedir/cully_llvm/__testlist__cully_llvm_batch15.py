import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Batch 15 of the c-testsuite (github.com/c-testsuite/c-testsuite)
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
    "function": "batch_15",
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
            "description": "upstream c-testsuite tests/single-exec/00147.c [portable, c99] -- int arr[3] = {[2] = 2, [0] = 0, [1] = 1};",
            "param": {
                "name": "nova1",
                "script_path": "{projbasedir}{projdir}/gen/ct00147.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00147 printed \"00147: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00148.c [portable, c99] -- struct S {int a; int b;};",
            "param": {
                "name": "nova2",
                "script_path": "{projbasedir}{projdir}/gen/ct00148.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00148 printed \"00148: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00149.c [portable, c99] -- struct S { int a; int b; };",
            "param": {
                "name": "nova3",
                "script_path": "{projbasedir}{projdir}/gen/ct00149.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00149 printed \"00149: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00150.c [portable, c99] -- struct S1 {{",
            "param": {
                "name": "nova4",
                "script_path": "{projbasedir}{projdir}/gen/ct00150.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00150 printed \"00150: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00151.c [portable, c99] -- int arr[][3][5] = {{",
            "param": {
                "name": "nova5",
                "script_path": "{projbasedir}{projdir}/gen/ct00151.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00151 printed \"00151: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00152.c [portable, c89, needs-cpp] -- #undef  line",
            "param": {
                "name": "nova6",
                "script_path": "{projbasedir}{projdir}/gen/ct00152.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00152 printed \"00152: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00153.c [portable, c89, needs-cpp] -- #define x f",
            "param": {
                "name": "nova7",
                "script_path": "{projbasedir}{projdir}/gen/ct00153.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00153 printed \"00153: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00154.c [portable, c89, needs-libc, needs-cpp] -- #include <stdio.h>",
            "param": {
                "name": "nova8",
                "script_path": "{projbasedir}{projdir}/gen/ct00154.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00154 printed \"00154: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00155.c [portable, c89] -- sizeof((int) 1);",
            "param": {
                "name": "nova9",
                "script_path": "{projbasedir}{projdir}/gen/ct00155.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00155 printed \"00155: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00156.c [portable, c99, needs-libc, needs-cpp] -- #include <stdio.h>",
            "param": {
                "name": "nova10",
                "script_path": "{projbasedir}{projdir}/gen/ct00156.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00156 printed \"00156: PASS\" to its console",
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
