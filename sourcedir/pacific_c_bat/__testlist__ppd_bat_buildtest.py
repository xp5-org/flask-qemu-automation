import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Clone of pacific_c/__testlist__ppd_buildtest.py with the GUI removed.
#
# The original drove the PPD IDE: open the editor on BARTEST.C, OCR the HI-TECH
# banner, F3 to compile, walk the modal dialogs with ret/ret/ret, OCR "success",
# alt-f q to quit. Every one of those steps was an OCR/keystroke race.
#
# Here the whole build is C:\SRC\BUILD.BAT, driven by the PACC command line
# driver, so the test is: boot -> run BUILD.BAT -> OCR one token -> run the EXE.
# The compiler options that reproduce the IDE's defaults are:
#
#   8086 code   - the default. -1 / -2 / -7 would select 80186 / 80286 / 8087.
#   small model - -Bs (also the default; stated explicitly so the testlist
#                 documents the build params rather than relying on a default).
#                 -Bs makes PACC link 86--dsc.lib + RT86--DS.OBJ; -Bl would
#                 pick the large-model 86--dlc.lib + RT86--DL.OBJ instead.
#   -O -Zg      - post-pass optimizer + code generator global optimization,
#                 the same pair PACIFIC\EXAMPLES\MAKEALL.BAT ships with.
#   -Q          - quiet (no signon banner); must be the first option.
#
# Option reference: C:\PACIFIC\HELP\DOS-0PAC.TBL on the hdd image (PACC -HELP).
CONFIG = {
    "parent": "Pacific C Bartest (batch build)",
    "projdir": "pacific_c_bat",
    "instance_name": "qemu1",
    "function": "buildpac1",
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
            "floppy1_path": "{floppy1_img}",
            "config_path": "{config_file}",
            "out_dir": {"_rel": "output"},
            "sourcecode_dir": {"_rel": "src"}
        }
    },
    "steps": [
        # src/ (BARTEST.C + BUILD.BAT) -> C:\SRC on the raw image, then convert
        # to the QCOW2 QEMU actually boots.
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

        # The entire build. One command, no dialogs.
        {"action": "test_sendkeyboardinput", "param": {"inputstring": "c:"}, "subaction": ""},
        {"action": "test_sendkeyboardinput", "param": {"inputstring": "cd \\src"}, "subaction": ""},
        {"action": "test_sendkeyboardinput", "param": {"inputstring": "build"}, "subaction": ""},
        {
            # BUILDPASS / BUILDFAIL are single tokens on purpose: no failphrase
            # like "error" can be used here because PACC's own summary line
            # contains the word even on a clean build.
            "action": "test_ocrwordsearch",
            "param": {
                "successphrase": "buildpass", "failphrase": "buildfail",
                "attemptdelay": "2", "numberofattempts": "20", "require_success": "True",
                "startx": 0, "starty": 0, "stopx": 640, "stopy": 480
            },
            "subaction": ""
        },

        # Run it. BARTEST sets mode 13h and animates until a key is pressed,
        # so a keystroke returns it to text mode before we tear down.
        {"action": "test_sendkeyboardinput", "param": {"inputstring": "bartest"}, "subaction": ""},
        {
            # 640x400, not 320x200: QEMU's std VGA reports mode 13h doubled in
            # both axes. This is the "it really switched to graphics" check.
            "action": "test_assert_screen_size",
            "param": {"expected_width": 640, "expected_height": 400},
            "subaction": ""
        },
        {
            "action": "test_sendspecialkeys",
            "param": {"keys": ["ret"], "delay": "2"},
            "subaction": ""
        },

        {"action": "test_terminate_all", "param": {}, "subaction": ""}
    ],
}

PATHS = init_test_env(CONFIG, __name__)
