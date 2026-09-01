import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Batch 9 of the c-testsuite (github.com/c-testsuite/c-testsuite)
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
    "function": "batch_09",
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
            "description": "upstream c-testsuite tests/single-exec/00086.c [portable, c89] -- short x;",
            "param": {
                "name": "nova1",
                "script_path": "{projbasedir}{projdir}/gen/ct00086.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00086 printed \"00086: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00087.c [portable, c89] -- struct S",
            "param": {
                "name": "nova2",
                "script_path": "{projbasedir}{projdir}/gen/ct00087.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00087 printed \"00087: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00088.c [portable, c89] -- int (*fptr)() = 0;",
            "param": {
                "name": "nova3",
                "script_path": "{projbasedir}{projdir}/gen/ct00088.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00088 printed \"00088: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00089.c [portable, c89] -- zero()",
            "param": {
                "name": "nova4",
                "script_path": "{projbasedir}{projdir}/gen/ct00089.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00089 printed \"00089: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00090.c [portable, c89] -- int a[3] = {0, 1, 2};",
            "param": {
                "name": "nova5",
                "script_path": "{projbasedir}{projdir}/gen/ct00090.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00090 printed \"00090: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00091.c [portable, c89] -- typedef struct {",
            "param": {
                "name": "nova6",
                "script_path": "{projbasedir}{projdir}/gen/ct00091.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00091 printed \"00091: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00092.c [portable, c99] -- int a[] = {5, [2] = 2, 3};",
            "param": {
                "name": "nova7",
                "script_path": "{projbasedir}{projdir}/gen/ct00092.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00092 printed \"00092: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00093.c [portable, c89] -- int a[] = {1, 2, 3, 4};",
            "param": {
                "name": "nova8",
                "script_path": "{projbasedir}{projdir}/gen/ct00093.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00093 printed \"00093: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00094.c [portable, c89] -- extern int x;",
            "param": {
                "name": "nova9",
                "script_path": "{projbasedir}{projdir}/gen/ct00094.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00094 printed \"00094: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00095.c [portable, c89] -- int x;",
            "param": {
                "name": "nova10",
                "script_path": "{projbasedir}{projdir}/gen/ct00095.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00095 printed \"00095: PASS\" to its console",
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
