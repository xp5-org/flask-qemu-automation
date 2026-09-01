import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


CONFIG = {
    "parent": "mac_m68k",
    "projdir": "mac_m68k",
    "instance_name": "basilisk1",
    "function": "build1",
    "projbasedir": "/testsrc/sourcedir/",
    "app_dir": "retro68poc",
    "app_disk": "Retro68Poc.raw.dsk",
    "serial_path": "{projbasedir}{projdir}/{app_dir}/output/serial_bsk.log",
    "basilisk_rom": "/testsrc/m68k/Quadra-650.ROM",
    "basilisk_boot_disk": "/testsrc/m68k/system76boot.dsk",
    "structure": {"project": {"_rel": "{projdir}", "out_dir": {"_rel": "output"}}},
    "steps": [
        {
            "action": "test_hostbuild",
            "param": {"command": "./build.sh",
                      "cwd": "{projbasedir}{projdir}/{app_dir}",
                      "timeout": "600"},
            "subaction": ""
        },
        {
            "action": "test_start_basilisk",
            "param": {
                "name": "basilisk1",
                "extra_disk": "{projbasedir}{projdir}/{app_dir}/{app_disk}",
                "serial_path": "{serial_path}",
                "ramsize_mb": "64",
                "modelid": "14"
            },
            "subaction": ""
        },
        {
            # Wait for the Finder desktop to come up
            "action": "test_ocrwordsearch",
            "param": {"attemptdelay": "2", "numberofattempts": "8",
                      "successphrase": "Trash"},
            "subaction": ""
        },
        {
            # Open the mounted app disk (auto-selected) then launch the app.
            # Mac Command maps to host Super in Basilisk's default X keymap;
            # if the app doesn't launch, try 'alt+o'/'ctrl+o' instead.
            "action": "test_sendspecialkeys",
            "param": {"keys": "super+o, super+a, super+o", "delay": "2",
                      "name": "basilisk1"},
            "subaction": ""
        },
        {
            # OCR-free verification: token in the serial log
            "action": "test_filecontains",
            "param": {"file_path": "{serial_path}",
                      "successphrase": "RETRO68_POC_OK", "timeout": "30"},
            "subaction": ""
        },
        {
            # OCR verification: token on the console window
            "action": "test_ocrwordsearch",
            "param": {"attemptdelay": "2", "numberofattempts": "5",
                      "successphrase": "RETRO68_POC_OK", "require_success": "true"},
            "subaction": ""
        },
        {"action": "test_terminate_all", "param": {}, "subaction": ""},
    ],
}

PATHS = init_test_env(CONFIG, __name__)
