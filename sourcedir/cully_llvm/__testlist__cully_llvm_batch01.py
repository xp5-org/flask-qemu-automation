import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Batch 1 of the c-testsuite (github.com/c-testsuite/c-testsuite)
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
    "function": "batch_01",
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
            "description": "upstream c-testsuite tests/single-exec/00001.c [portable, c89] -- return 0;",
            "param": {
                "name": "nova1",
                "script_path": "{projbasedir}{projdir}/gen/ct00001.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00001 printed \"00001: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00002.c [portable, c89] -- return 3-3;",
            "param": {
                "name": "nova2",
                "script_path": "{projbasedir}{projdir}/gen/ct00002.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00002 printed \"00002: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00003.c [portable, c89] -- int x;",
            "param": {
                "name": "nova3",
                "script_path": "{projbasedir}{projdir}/gen/ct00003.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00003 printed \"00003: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00004.c [portable, c89] -- int x;",
            "param": {
                "name": "nova4",
                "script_path": "{projbasedir}{projdir}/gen/ct00004.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00004 printed \"00004: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00005.c [portable, c89] -- int x;",
            "param": {
                "name": "nova5",
                "script_path": "{projbasedir}{projdir}/gen/ct00005.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00005 printed \"00005: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00006.c [portable, c89] -- int x;",
            "param": {
                "name": "nova6",
                "script_path": "{projbasedir}{projdir}/gen/ct00006.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00006 printed \"00006: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00007.c [portable, c89] -- int x;",
            "param": {
                "name": "nova7",
                "script_path": "{projbasedir}{projdir}/gen/ct00007.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00007 printed \"00007: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00008.c [portable, c89] -- int x;",
            "param": {
                "name": "nova8",
                "script_path": "{projbasedir}{projdir}/gen/ct00008.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00008 printed \"00008: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00009.c [portable, c89] -- int x;",
            "param": {
                "name": "nova9",
                "script_path": "{projbasedir}{projdir}/gen/ct00009.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00009 printed \"00009: PASS\" to its console",
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
            "description": "upstream c-testsuite tests/single-exec/00010.c [portable, c89] -- start:",
            "param": {
                "name": "nova10",
                "script_path": "{projbasedir}{projdir}/gen/ct00010.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check ct00010 printed \"00010: PASS\" to its console",
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
