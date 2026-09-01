import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# First smoke test for the nova-llvm-backend (cullyrichard/nova-llvm-backend,
# a real LLVM/Clang backend for Data General Nova/Eclipse, extending the
# sibling eclipse-llvm-backend project) run through OUR OWN real Nova SIMH
# (dgnova) -- something neither upstream project's own README/porting-notes
# had available (they verified logic via eclipseemu + re-encoding, see
# nova-llvm-backend's NOVA_PORTING_NOTES.md "What this does NOT verify").
#
# Pipeline (see ../nova_c/NOTES.txt for how this differs from the PCC-for-Nova
# pipeline that directory/../nova_ctestsuite use):
#   src/smoke01.c
#     -> clang -cc1 (triple eclipse-dg-none) -> .ll
#     -> llvm-link (merge with rt/eclipse_rt.c) -> merged .ll
#     -> opt -passes=internalize,globaldce -> stripped .ll
#     -> llc -mcpu=nova3 -filetype=asm -> .s
#     -> reorder_asm.py -> reordered .s
#     -> dgasm -t nova3 -f simh -> gen/smoke01.simh ("dep ADDR VAL" lines)
#     -> this testlist appends "go 100" + "quit" itself (dgasm's -f simh
#        output is bare deposits only -- entry point is always address 0100
#        octal per the backend's fixed "org 0100"; confirmed empirically
#        assembling a trivial HALT-only program) to get gen/smoke01.ini,
#        the exact same "d ADDR VAL / go START / quit" shape
#        nova_c/build_c_test.py already produces for the PCC pipeline.
#
# smoke01.c deliberately mirrors nova_ctestsuite's ct00001.c shape (a
# testmain() returning 0, PASS/FAIL via putchar) rather than testing any
# real C feature -- the point of this first test is proving the toolchain
# and wiring work at all, not exercising codegen breadth. See the
# conversation this testlist came from for why: get ONE test onto the TTY
# before scaling to a c89 batch the way nova_ctestsuite does.

CONFIG = {
    "parent": "cully_llvm",
    "projdir": "cully_llvm",
    "instance_name": "nova1",
    "function": "smoke01",
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {
        "project": {
            "_rel": "{projdir}",
        }
    },
    "steps": [
        {
            "action": "test_startnovasimh",
            "description": "nova-llvm-backend (eclipse-clang, -t nova3) smoke01.c -- testmain() returning 0",
            "param": {
                "name": "nova1",
                "script_path": "{projbasedir}{projdir}/gen/smoke01.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "description": "Check smoke01 printed \"SMOKE01: PASS\" to its console",
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
            "action": "test_terminate_all",
            "description": "Tear down the Nova SIMH instance this test started",
            "param": {},
            "subaction": ""
        },
    ],
}

PATHS = init_test_env(CONFIG, __name__)
