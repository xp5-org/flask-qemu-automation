import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Pacific C TSR. Same batch-driven shape as pacific_c_bat: the build is one
# BUILD.BAT invocation of the PACC command line driver, 8086 + small model.

CONFIG = {
    "parent": "Pacific C TSR Counter",
    "projdir": "pacific_c_tsr",
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
                "name": "qemu1",
                "cpuarch": "i386",
                "port": 55555,
                "floppy1_path": "{projbasedir}{projdir}/{floppy1_img}",
                "floppy1_size": "{floppy1_size}",
                "hdd1_qcow_path": "{projbasedir}{projdir}/{hdd1_qcow}"
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "successphrase": "msdos ready", "failphrase": "",
                "attemptdelay": "2", "numberofattempts": "10",
                "startx": 0, "starty": 0, "stopx": 160, "stopy": 480
            },
            "subaction": ""
        },

        {"action": "test_sendkeyboardinput", "param": {"inputstring": "c:"}, "subaction": ""},
        {"action": "test_sendkeyboardinput", "param": {"inputstring": "cd \\src"}, "subaction": ""},
        {"action": "test_sendkeyboardinput", "param": {"inputstring": "build"}, "subaction": ""},
        {
            "action": "test_ocrwordsearch",
            "param": {
                "successphrase": "buildpass", "failphrase": "buildfail",
                "attemptdelay": "2", "numberofattempts": "25", "require_success": "True",
                "startx": 0, "starty": 0, "stopx": 640, "stopy": 480
            },
            "subaction": ""
        },

        # Install. The loader prints its banner and then INT 21h AH=31h hands
        # control back to COMMAND.COM with the counter running behind it.
        {"action": "test_sendkeyboardinput", "param": {"inputstring": "tsrtest"}, "subaction": ""},
        {
            "action": "test_ocrwordsearch",
            "param": {
                "successphrase": "tsr installed", "failphrase": "",
                "attemptdelay": "2", "numberofattempts": "8", "require_success": "True",
                "startx": 0, "starty": 0, "stopx": 640, "stopy": 480
            },
            "subaction": ""
        },

        # Recompile with the TSR resident. Two things at once: it is the
        # heaviest external program on the disk, so a clean BUILDPASS proves
        # AH=31h left DOS enough free memory to load anything (the -E8192 cap
        # doing its job), and it takes long enough for the counter to run
        # several full 0..10 cycles underneath it.
        {"action": "test_sendkeyboardinput", "param": {"inputstring": "build"}, "subaction": ""},
        {
            "action": "test_ocrwordsearch",
            "param": {
                "successphrase": "buildpass", "failphrase": "buildfail",
                "attemptdelay": "2", "numberofattempts": "25", "require_success": "True",
                "startx": 0, "starty": 0, "stopx": 640, "stopy": 480
            },
            "subaction": ""
        },

        # ESC: the INT 09h hook sees scan code 01h, the next timer tick
        # unhooks both vectors and overwrites the counter with TSR STOPPED.
        {
            "action": "test_sendspecialkeys",
            "param": {"keys": ["esc"], "delay": "2"},
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "successphrase": "tsr stopped", "failphrase": "",
                "attemptdelay": "2", "numberofattempts": "6", "require_success": "True",
                "startx": 0, "starty": 0, "stopx": 640, "stopy": 480
            },
            "subaction": ""
        },

        {"action": "test_terminate_all", "param": {}, "subaction": ""}
    ],
}

PATHS = init_test_env(CONFIG, __name__)
