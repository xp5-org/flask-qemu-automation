import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# End-to-end Retro68 build+run test for the console-less q800 (System 7.5):
#   1. Cross-compile hello.c on the Linux host  -> Retro68Poc.dsk (HFS)
#   2. Boot the q800 with that .dsk attached as a SCSI volume + serial capture
#   3. Open the mounted disk, then the app, from the Finder (relative-mouse
#      closed-loop double-clicks)
#   4. Verify the run two independent ways:
#        - serial log contains the token (OCR-free, host-side stdout)
#        - OCR reads the token off the on-screen console window
#
# The disk/app icon templates under buttontest/ are captured from a live boot
# (screenshot + crop) — see the session notes; region= limits the search to the
# top-right where disks mount.
#
# Paths are {tokens} resolved against CONFIG, not f-strings on a module
# constant: CONFIG has to stay a literal dict or the runner cannot read it
# statically (testbuilder, step validation, cloning). The app's token is
# "RETRO68_POC_OK", spelled out in the verification steps — phrase params are
# matched literally, not resolved.
CONFIG = {
    "parent": "mac_m68k",
    "projdir": "mac_m68k",
    "instance_name": "qemu1",
    "function": "build3",
    "hdd1_qcow": "hdd.qcow2",
    "projbasedir": "/testsrc/sourcedir/",
    "app_dir": "retro68poc",
    "app_disk": "Retro68Poc.dsk",
    "serial_path": "{projbasedir}{projdir}/{app_dir}/output/serial.log",
    "structure": {
        "project": {
            "_rel": "{projdir}",
            "hdd_qcow_path": "{hdd1_qcow}",
            "out_dir": {
                "_rel": "output"
            }
        }
    },
    "steps": [
        {
            # 1. Host-side cross-compile -> Retro68Poc.dsk
            "action": "test_hostbuild",
            "param": {
                "command": "./build.sh",
                "cwd": "{projbasedir}{projdir}/{app_dir}",
                "timeout": "600"
            },
            "subaction": ""
        },
        {
            # 2. Boot q800 with the compiled disk (scsi-id 2) + serial capture
            "action": "test_startqemu",
            "param": {
                "cpuarch": "m68k",
                "name": "qemu1",
                "port": 55555,
                "hdd2_path": "{projbasedir}{projdir}/{app_dir}/{app_disk}",
                "hdd2_prepare": "false",
                "serial_path": "{serial_path}"
            },
            "subaction": ""
        },
        {
            # 3a. Wait for the desktop to come up
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "numberofattempts": "10",
                "successphrase": "Mac OS"
            },
            "subaction": ""
        },
        {
            # 3b. Open the mounted Retro68Poc disk (top-right of desktop)
            "action": "test_find_and_open_icon",
            "param": {
                "icon_path": "/testsrc/buttontest/retro68_disk_icon.png",
                "name": "qemu1",
                "clicks": "2",
                "region": "460,0,640,400"
            },
            "subaction": ""
        },
        {
            # 3c. Open the app inside the disk window
            "action": "test_find_and_open_icon",
            "param": {
                "icon_path": "/testsrc/buttontest/retro68_app_icon.png",
                "name": "qemu1",
                "clicks": "2"
            },
            "subaction": ""
        },
        {
            # 4a. OCR-free verification: token in the serial log
            "action": "test_filecontains",
            "param": {
                "file_path": "{serial_path}",
                "successphrase": "RETRO68_POC_OK",
                "timeout": "30"
            },
            "subaction": ""
        },
        {
            # 4b. OCR verification: token on the console window
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "numberofattempts": "5",
                "successphrase": "RETRO68_POC_OK",
                "require_success": "true"
            },
            "subaction": ""
        },
        {
            "action": "test_terminate_all",
            "param": {},
            "subaction": ""
        }
    ],
}

PATHS = init_test_env(CONFIG, __name__)
