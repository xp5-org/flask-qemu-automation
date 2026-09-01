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
    "instance_name": "qemu1",
    "function": "qemu",
    # C: -- shared with the owc_djgpp_allegro project rather than duplicating
    # a second 512MB copy of the same DJGPP+Allegro install. _prepare_hdd_overlay
    # only resolves hdd1_template against /testsrc/templates when the value has
    # no path separator, so an explicit path is used as-is, and the QCOW2
    # overlay below means this test never writes to it.
    "hdd1_template": "{projbasedir}owc_djgpp_allegro/c_drive_raw.img",
    "hdd1_overlay": "c_drive.qcow2",
    # D: -- per-project raw source/output drive, populated from src_dir.
    "srcdisk_img": "d_drive.img",
    "srcdisk_size_mb": 512,
    "floppy1_img": "newfloppy.img",
    "floppy1_size": "1440k",
    "config_file": "dosbox_template.conf",
    "src_dir": "src",
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {
        "project": {
            "_rel": "{projdir}",
            "config_path": "{config_file}",
            "floppy1_path": "{floppy1_img}",
            "hdd1_overlay_path": "{hdd1_overlay}",
            "out_dir": {
                "_rel": "output"
            },
            "sourcecode_dir": {
                "_rel": "src"
            },
            "srcdisk_path": "{srcdisk_img}"
        }
    },
    "steps": [
        {
            "action": "test_startqemu",
            "param": {
                "cpuarch": "i386",
                "floppy1_path": "{projbasedir}{projdir}/{floppy1_img}",
                "floppy1_size": "{floppy1_size}",
                "hdd1_qcow_path": "{projbasedir}{projdir}/{hdd1_overlay}",
                "hdd1_template": "{hdd1_template}",
                "hdd2_path": "{projbasedir}{projdir}/{srcdisk_img}",
                "name": "qemu1",
                "port": 55555,
                "sourcecode_dir": "{projbasedir}{projdir}/{src_dir}",
                "srcdisk_size_mb": "{srcdisk_size_mb}"
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
                "inputstring": "d:"
            },
            "subaction": ""
        },
        {
            "action": "test_sendkeyboardinput",
            "param": {
                "inputstring": "cd \\src"
            },
            "subaction": ""
        },
        {
            "action": "test_sendkeyboardinput",
            "param": {
                "inputstring": "compile"
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "5",
                "failphrase": "error",
                "numberofattempts": "50",
                "require_success": True,
                "startx": "0",
                "starty": "0",
                "stopx": "640",
                "stopy": "480",
                "successphrase": "executable",
                "takeascreenshot": True
            },
            "subaction": "",
            "description": "this takes forever gcc is slow idk"
        },
        {
            "action": "test_sendkeyboardinput",
            "param": {
                "inputstring": "blahaj"
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "failphrase": "need truecolor",
                "numberofattempts": "8",
                "require_success": "True",
                "startx": 0,
                "starty": 0,
                "stopx": 640,
                "stopy": 480,
                "successphrase": "blahaj ready"
            },
            "subaction": ""
        },
        {
            "action": "test_sendspecialkeys",
            "param": {
                "delay": "2.5",
                "keys": [
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
                "attemptdelay": "2",
                "failphrase": "",
                "numberofattempts": "5",
                "startx": 0,
                "starty": 0,
                "stopx": 640,
                "stopy": 480,
                "successphrase": "done"
            },
            "subaction": ""
        },
        {
            "action": "test_terminate_all",
            "param": {},
            "subaction": ""
        },
        {
            "action": "test_extract_from_hddimg",
            "param": {
                "dest_dir": "{projbasedir}{projdir}/{src_dir}",
                "hdd_img_path": "{projbasedir}{projdir}/{srcdisk_img}"
            },
            "subaction": "",
            "description": "pull the compiled executable off D: so it lands in the report's Build Artifacts table"
        }

    ],
    "test_startqemu.cpuarch": "",
    "test_startqemu.floppy1_path": "",
    "test_startqemu.hdd1_qcow_path": "",
    "test_startqemu.hdd2_path": "",
    "test_startqemu.name": "",
    "test_startqemu.port": "",
    "test_startqemu.sourcecode_dir": "",
    "test_startqemu.audio_backend": "",
    "test_startqemu.audio_out_path": "",
    "test_startqemu.bios_path": "",
    "test_startqemu.boot_order": "",
    "test_startqemu.cdrom2_path": "",
    "test_startqemu.cdrom_path": "",
    "test_startqemu.cpu": "",
    "test_startqemu.extra_args": "",
    "test_startqemu.extra_disks": "",
    "test_startqemu.floppy2_path": "",
    "test_startqemu.floppy2_size": "",
    "test_startqemu.hdd1_persist": "",
    "test_startqemu.hdd2_prepare": "",
    "test_startqemu.mac_address": "",
    "test_startqemu.machine": "",
    "test_startqemu.memory": "",
    "test_startqemu.net_device": "",
    "test_startqemu.prom_env": "",
    "test_startqemu.serial_path": "",
    "test_startqemu.sound_device": "",
    "test_startqemu.takeascreenshot": "",
    "test_startqemu.vga": "",
    "test_startqemu.vnc_port": "",
    "test_ocrwordsearch.attemptdelay": "",
    "test_ocrwordsearch.failphrase": "",
    "test_ocrwordsearch.numberofattempts": "",
    "test_ocrwordsearch.startx": "",
    "test_ocrwordsearch.starty": "",
    "test_ocrwordsearch.stopx": "",
    "test_ocrwordsearch.stopy": "",
    "test_ocrwordsearch.successphrase": "",
    "test_ocrwordsearch.require_success": "",
    "test_ocrwordsearch.takeascreenshot": "",
    "test_sendkeyboardinput.inputstring": "",
    "test_sendkeyboardinput.name": "",
    "test_sendkeyboardinput.takeascreenshot": "",
    "test_sendspecialkeys.delay": "",
    "test_sendspecialkeys.keys": "",
    "test_sendspecialkeys.name": "",
    "test_sendspecialkeys.takeascreenshot": "",
}

PATHS = init_test_env(CONFIG, __name__)
