import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


CONFIG = {
    "parent": "DJGPP Allegro Blahaj Multilight",
    "projdir": "owc_blahaj_multilight",
    "instance_name": "dosbox1",
    "function": "dosbox",
    # C: -- shared with the owc_djgpp_allegro project rather than duplicating
    # a second 512MB copy of the same DJGPP+Allegro install. hdd1_template is
    # used only if hdd1_overlay doesn't exist yet (test_flatten_qcow_to_raw
    # builds it from this template first).
    "hdd1_template": "{projbasedir}owc_djgpp_allegro/c_drive_raw.img",
    "hdd1_overlay": "c_drive.qcow2",
    "src_dir": "src",
    "machine": "svga_s3",
    "memsize": 16,
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {
        "project": {
            "_rel": "{projdir}",
            "hdd1_overlay_path": "{hdd1_overlay}",
            "out_dir": {
                "_rel": "output"
            },
            "sourcecode_dir": {
                "_rel": "src"
            }
        }
    },
    "steps": [
        {
            "action": "test_flatten_qcow_to_raw",
            "param": {
                "hdd1_template": "{hdd1_template}",
                "qcow_path": "{projbasedir}{projdir}/{hdd1_overlay}",
                "raw_path": "{projbasedir}{projdir}/output/c_drive_raw.img"
            },
            "subaction": ""
        },
        {
            "action": "test_copy_tree",
            "param": {
                "clean": "True",
                "dest_dir": "{projbasedir}{projdir}/output/src_run",
                "src_dir": "{projbasedir}{projdir}/src"
            },
            "subaction": ""
        },
        {
            "action": "test_dosbox_conf",
            "param": {
                "autoexec": [
                    "imgmount c {projbasedir}{projdir}/output/c_drive_raw.img -t hdd -fs fat",
                    "mount d {projbasedir}{projdir}/output/src_run"
                ],
                "config_path": "{projbasedir}{projdir}/output/dosbox_owc.conf",
                "machine": "{machine}",
                "memsize": "{memsize}"
            },
            "subaction": ""
        },
        {
            "action": "test_start_dosbox",
            "param": {
                "config_path": "{projbasedir}{projdir}/output/dosbox_owc.conf",
                "name": "dosbox1",
                "timeout": 20
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "failphrase": "",
                "name": "dosbox1",
                "require_success": "True",
                "successphrase": "drive c is mounted",
                "timeout": 30
            },
            "subaction": ""
        },
        {
            "action": "test_sendcommand",
            "param": {
                "cmd_text": "d:",
                "delay": 1,
                "name": "dosbox1",
                "special_keys": "Return"
            },
            "subaction": ""
        },
        {
            "action": "test_sendcommand",
            "param": {
                "cmd_text": "compile",
                "name": "dosbox1",
                "special_keys": "Return"
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "description": "this takes forever gcc is slow idk",
            "param": {
                "failphrase": "errorr",
                "name": "dosbox1",
                "poll": "5",
                "require_success": True,
                "successphrase": "executable",
                "takeascreenshot": True,
                "timeout": "180"
            },
            "subaction": ""
        },
        {
            "action": "test_fileexists",
            "param": {
                "file_path": "{projbasedir}{projdir}/output/src_run/blahaj.exe",
                "timeout": 30
            },
            "subaction": ""
        },
        {
            "action": "test_sendcommand",
            "param": {
                "cmd_text": "blahaj",
                "name": "dosbox1",
                "special_keys": "Return"
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "failphrase": "need truecolor",
                "name": "dosbox1",
                "require_success": "True",
                "successphrase": "blahaj ready",
                "timeout": 15
            },
            "subaction": ""
        },
        {
            "action": "test_sendcommand",
            "param": {
                "delay": "2.5",
                "name": "dosbox1",
                "special_keys": [
                    "q",
                    "q",
                    "q"
                ]
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "failphrase": "",
                "name": "dosbox1",
                "require_success": False,
                "successphrase": "done",
                "timeout": 15
            },
            "subaction": ""
        },
        {
            "action": "test_terminate_all",
            "param": {},
            "subaction": ""
        }
    ],
    "test_flatten_qcow_to_raw.qcow_path": "",
    "test_flatten_qcow_to_raw.raw_path": "",
    "test_copy_tree.clean": "",
    "test_copy_tree.dest_dir": "",
    "test_dosbox_conf.autoexec": "",
    "test_dosbox_conf.config_path": "",
    "test_dosbox_conf.template_path": "",
    "test_start_dosbox.config_path": "",
    "test_start_dosbox.name": "",
    "test_start_dosbox.timeout": "",
    "test_start_dosbox.display": "",
    "test_start_dosbox.takeascreenshot": "",
    "test_ocrwordsearch.failphrase": "",
    "test_ocrwordsearch.name": "",
    "test_ocrwordsearch.require_success": "",
    "test_ocrwordsearch.successphrase": "",
    "test_ocrwordsearch.timeout": "",
    "test_ocrwordsearch.poll": "",
    "test_ocrwordsearch.takeascreenshot": "",
    "test_sendcommand.cmd_text": "",
    "test_sendcommand.delay": "",
    "test_sendcommand.name": "",
    "test_sendcommand.special_keys": "",
    "test_sendcommand.key_delay": "",
    "test_sendcommand.takeascreenshot": "",
    "test_fileexists.file_path": "",
    "test_fileexists.timeout": "",
    "test_fileexists.min_size": "",
}

PATHS = init_test_env(CONFIG, __name__)
