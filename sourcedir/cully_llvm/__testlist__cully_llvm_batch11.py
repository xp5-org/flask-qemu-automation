import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Batch 11 of the c-testsuite (github.com/c-testsuite/c-testsuite)
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
    "function": "batch_11",
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
            "description": "upstream c-testsuite tests/single-exec/00107.c [portable, c89] -- typedef int myint;",
            "param": {
                "name": "nova1",
                "script_path": "{projbasedir}{projdir}/gen/ct00107.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00107 printed \"00107: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00108.c [portable, c89, needs-cpp] -- int foo(void);",
            "param": {
                "name": "nova2",
                "script_path": "{projbasedir}{projdir}/gen/ct00108.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00108 printed \"00108: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00109.c [portable, c89] -- int x = 0;",
            "param": {
                "name": "nova3",
                "script_path": "{projbasedir}{projdir}/gen/ct00109.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00109 printed \"00109: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00110.c [portable, c89] -- extern int x;",
            "param": {
                "name": "nova4",
                "script_path": "{projbasedir}{projdir}/gen/ct00110.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00110 printed \"00110: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00111.c [portable, c89] -- short s = 1;",
            "param": {
                "name": "nova5",
                "script_path": "{projbasedir}{projdir}/gen/ct00111.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00111 printed \"00111: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00112.c [portable, c89] -- return \"abc\" == (void *)0;",
            "param": {
                "name": "nova6",
                "script_path": "{projbasedir}{projdir}/gen/ct00112.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00112 printed \"00112: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00113.c [portable, c89] -- int a = 0;",
            "param": {
                "name": "nova7",
                "script_path": "{projbasedir}{projdir}/gen/ct00113.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00113 printed \"00113: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00114.c [portable, c89] -- int main(void);",
            "param": {
                "name": "nova8",
                "script_path": "{projbasedir}{projdir}/gen/ct00114.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00114 printed \"00114: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00115.c [portable, c89, needs-cpp] -- #define B \"b\"",
            "param": {
                "name": "nova9",
                "script_path": "{projbasedir}{projdir}/gen/ct00115.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00115 printed \"00115: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00116.c [portable, c89] -- f(int f)",
            "param": {
                "name": "nova10",
                "script_path": "{projbasedir}{projdir}/gen/ct00116.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00116 printed \"00116: PASS\" to its console",
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
