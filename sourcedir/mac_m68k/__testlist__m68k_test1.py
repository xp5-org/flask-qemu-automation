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
    "instance_name": "qemu1",
    "function": "build5",
    "hdd1_qcow": "hdd.qcow2",
    "projbasedir": "/testsrc/sourcedir/",
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
            "action": "test_startqemu",
            "param": {
                "cpuarch": "m68k",
                "hdd1_qcow_path": "{projbasedir}{projdir}/{hdd1_qcow}",
                "name": "qemu1",
                "port": 55555
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "failphrase": "",
                "numberofattempts": "10",
                "startx": 0,
                "starty": 0,
                "stopx": 160,
                "stopy": 480,
                "successphrase": "Mac OS"
            },
            "subaction": ""
        },
        {
            "action": "test_closeallwindows",
            "param": {
                "button_path": "/testsrc/buttontest/finder_window_closebutton.png",
                "max_windows": "8",
                "name": "qemu1"
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
