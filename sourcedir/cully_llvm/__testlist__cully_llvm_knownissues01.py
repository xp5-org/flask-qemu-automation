import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Known-issues batch 1 of the c-testsuite battery: tests that
# BUILT but did not run cleanly (screen_runtime.py classified them FAIL or
# HANG -- see RUNTIME_STATUS.md for which is which). Wired in as a visible
# to-fix backlog rather than left out, same convention as
# ../nova_ctestsuite/gen_testlists.py.
#
# Every test here is expected to fail/hang on its own -- that's the whole
# point of a known-issues list -- so "continue_on_failure" is on: each
# test_novascreensearch's abort flag no longer cascades into skipping every
# later step in this file, and all of them show a real result on every run
# instead of only the first one reached. (Formerly this skip-cascaded --
# see test_runner.py's continue_on_failure handling for the toggle.)
#
# This is the LLVM-backend counterpart to ../nova_ctestsuite/ -- see this
# directory's own NOTES.txt.

CONFIG = {
    "parent": "cully_llvm",
    "projdir": "cully_llvm",
    "instance_name": "nova1",
    "function": "known_issues_01",
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
            "description": "KNOWN ISSUE (FAIL) -- upstream c-testsuite tests/single-exec/00032.c [portable, c89] -- int arr[2];",
            "param": {
                "name": "nova1",
                "script_path": "{projbasedir}{projdir}/gen/ct00032.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "KNOWN ISSUE (FAIL): expect this to print FAIL -- if it now PASSes, move ct00032 from known_issues.txt to stable_pass.txt and re-run gen_testlists.py",
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
            "description": "KNOWN ISSUE (FAIL) -- upstream c-testsuite tests/single-exec/00037.c [portable, c89] -- int x[2];",
            "param": {
                "name": "nova2",
                "script_path": "{projbasedir}{projdir}/gen/ct00037.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "KNOWN ISSUE (FAIL): expect this to print FAIL -- if it now PASSes, move ct00037 from known_issues.txt to stable_pass.txt and re-run gen_testlists.py",
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
            "description": "KNOWN ISSUE (FAIL) -- upstream c-testsuite tests/single-exec/00072.c [portable, c89] -- int arr[2];",
            "param": {
                "name": "nova3",
                "script_path": "{projbasedir}{projdir}/gen/ct00072.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "KNOWN ISSUE (FAIL): expect this to print FAIL -- if it now PASSes, move ct00072 from known_issues.txt to stable_pass.txt and re-run gen_testlists.py",
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
            "description": "KNOWN ISSUE (FAIL) -- upstream c-testsuite tests/single-exec/00073.c [portable, c89] -- int arr[2];",
            "param": {
                "name": "nova4",
                "script_path": "{projbasedir}{projdir}/gen/ct00073.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "KNOWN ISSUE (FAIL): expect this to print FAIL -- if it now PASSes, move ct00073 from known_issues.txt to stable_pass.txt and re-run gen_testlists.py",
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
            "description": "KNOWN ISSUE (FAIL) -- upstream c-testsuite tests/single-exec/00203.c [portable, c89, needs-libc, needs-cpp] -- #include <stdio.h>",
            "param": {
                "name": "nova5",
                "script_path": "{projbasedir}{projdir}/gen/ct00203.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "KNOWN ISSUE (FAIL): expect this to print FAIL -- if it now PASSes, move ct00203 from known_issues.txt to stable_pass.txt and re-run gen_testlists.py",
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
            "description": "KNOWN ISSUE (HANG) -- upstream c-testsuite tests/single-exec/00040.c [portable, c89, needs-libc] -- #include <stdlib.h>",
            "param": {
                "name": "nova6",
                "script_path": "{projbasedir}{projdir}/gen/ct00040.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "KNOWN ISSUE (HANG): expect this to hang/timeout -- if it now PASSes, move ct00040 from known_issues.txt to stable_pass.txt and re-run gen_testlists.py",
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
            "action": "test_terminate_all",
            "description": "Tear down every Nova SIMH instance this batch started",
            "param": {},
            "subaction": ""
        },
    ],
}

PATHS = init_test_env(CONFIG, __name__)
