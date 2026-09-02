import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# C: comes from the shared /testsrc/templates/dos622_pacific.img template
CONFIG = {
    "parent": "Pacific C Bartest",
    "projdir": "pacific_c",
    "instance_name": "qemu1",
    "function": "buildpac1",
    "pacific_c_template": "dos622_pacific.img",
    "hdd1_overlay": "c_drive.qcow2",
    "hdd1_img": "hdd.img",
    "hdd1_qcow": "hdd.qcow2",
    "floppy1_img": "newfloppy.img",
    "floppy1_size": "1440k",
    "config_file": "dosbox_template.conf",
    "src_dir": "src",
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {
        "project": {
            "_rel": "{projdir}",
            "hdd_img_path": "{hdd1_img}",
            "hdd_qcow_path": "{hdd1_qcow}",
            "hdd1_overlay_path": "{hdd1_overlay}",
            "floppy1_path": "{floppy1_img}",
            "config_path": "{config_file}",
            "out_dir": {"_rel": "output"},
            "sourcecode_dir": {"_rel": "src"}
        }
    },
    "steps": [
        {
            "action": "test_flatten_qcow_to_raw",
            "param": {
                "qcow_path": "{projbasedir}{projdir}/{hdd1_overlay}",
                "raw_path": "{projbasedir}{projdir}/{hdd1_img}",
                "hdd1_template": "{pacific_c_template}"
            },
            "subaction": ""
        },
        {
            "action": "test_dirandfilesto_hddimg",
            "param": {
                "hdd_img_path": "{projbasedir}{projdir}/{hdd1_img}",
                "sourcecode_dir": "{projbasedir}{projdir}/{src_dir}"
            },
            "subaction": ""
        },
        {
            "action": "test_convert_hddimg_to_hddqcow",
            "param": {
                "hdd_img_path": "{projbasedir}{projdir}/{hdd1_img}",
                "hdd_qcow_path": "{projbasedir}{projdir}/{hdd1_qcow}"
            },
            "subaction": ""
        },
        {
            "action": "test_startqemu",
            "param": {
                "cpuarch": "i386",
                "floppy1_path": "{projbasedir}{projdir}/{floppy1_img}",
                "floppy1_size": "{floppy1_size}",
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
                "successphrase": "msdos ready"
            },
            "subaction": ""
        },
        {
            "action": "test_sendkeyboardinput",
            "param": {
                "inputstring": "cd pacific"
            },
            "subaction": ""
        },
        {
            "action": "test_sendkeyboardinput",
            "param": {
                "inputstring": "cd bin"
            },
            "subaction": ""
        },
        {
            "action": "test_sendkeyboardinput",
            "param": {
                "inputstring": "ppd c:\\src\\bartest.c"
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "failphrase": "",
                "numberofattempts": "10",
                "require_success": "True",
                "startx": 0,
                "starty": 315,
                "stopx": 640,
                "stopy": 480,
                "successphrase": "HI-TECH"
            },
            "subaction": ""
        },
        {
            "action": "test_sendspecialkeys",
            "param": {
                "delay": "1",
                "keys": [
                    "f3",
                    "ret",
                    "f",
                    "ret",
                    "ret",
                    "ret"
                ]
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "failphrase": "error",
                "numberofattempts": "20",
                "require_success": "True",
                "startx": 0,
                "starty": 295,
                "stopx": 640,
                "stopy": 480,
                "successphrase": "success"
            },
            "subaction": ""
        },
        {
            "action": "test_sendspecialkeys",
            "param": {
                "delay": "0.5",
                "keys": [
                    "alt-f",
                    "q"
                ]
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
                "successphrase": "msdos"
            },
            "subaction": ""
        },
        {
            "action": "test_sendkeyboardinput",
            "param": {
                "inputstring": "cd c:\\src"
            },
            "subaction": ""
        },
        {
            "action": "test_sendkeyboardinput",
            "param": {
                "inputstring": "bartest"
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
