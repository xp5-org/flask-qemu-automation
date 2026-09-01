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
    "function": "build2",
    "hdd1_qcow": "hdd.qcow2",
    "projbasedir": "/testsrc/sourcedir/",
    "app_dir": "cuberotate",
    "app_disk": "CubeRotate.dsk",
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
            "action": "test_hostbuild",
            "param": {
                "command": "./build.sh",
                "cwd": "{projbasedir}{projdir}/{app_dir}",
                "timeout": "600"
            },
            "subaction": ""
        },
        {
            "action": "test_startqemu",
            "param": {
                "cpuarch": "m68k",
                "hdd2_path": "{projbasedir}{projdir}/{app_dir}/{app_disk}",
                "hdd2_prepare": "false",
                "name": "qemu1",
                "port": 55555,
                "serial_path": "{serial_path}"
            },
            "subaction": ""
        },
        {
            "action": "test_start_gif_capture",
            "description": "",
            "param": {
                "interval": "0.5",
                "max_frames": "240",
                "max_seconds": "120",
                "name": "qemu1",
                "playback_speed": "1",
                "scale": "1"
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "numberofattempts": "15",
                "successphrase": "Special"
            },
            "subaction": ""
        },
        {
            "action": "test_sendspecialkeys",
            "param": {
                "delay": "3",
                "keys": "meta_l-o",
                "name": "qemu1"
            },
            "subaction": ""
        },
        {
            "action": "test_sendspecialkeys",
            "param": {
                "delay": "2",
                "keys": "meta_l-a, meta_l-o",
                "name": "qemu1"
            },
            "subaction": ""
        },
        {
            "action": "test_filecontains",
            "param": {
                "file_path": "{serial_path}",
                "successphrase": "RETRO68_CUBE_OK",
                "timeout": "30"
            },
            "subaction": ""
        },
        {
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "numberofattempts": "5",
                "require_success": "true",
                "successphrase": "RETRO68_CUBE_OK"
            },
            "subaction": ""
        },
        {
            "action": "test_wait_for_seconds",
            "param": {
                "reason": "extra time for gif capture",
                "seconds": "3"
            },
            "subaction": "",
            "description": ""
        },
        {
            "action": "test_stop_gif_capture",
            "description": "",
            "param": {},
            "subaction": ""
        },
        {
            "action": "test_terminate_all",
            "param": {},
            "subaction": ""
        }
    ],
    "test_hostbuild.command": "",
    "test_hostbuild.cwd": "",
    "test_hostbuild.timeout": "",
    "test_startqemu.cpuarch": "",
    "test_startqemu.hdd2_path": "",
    "test_startqemu.hdd2_prepare": "",
    "test_startqemu.name": "",
    "test_startqemu.port": "",
    "test_startqemu.audio_backend": "",
    "test_startqemu.audio_out_path": "",
    "test_startqemu.bios_path": "",
    "test_startqemu.boot_order": "",
    "test_startqemu.cdrom2_path": "",
    "test_startqemu.cdrom_path": "",
    "test_startqemu.cpu": "",
    "test_startqemu.extra_args": "",
    "test_startqemu.extra_disks": "",
    "test_startqemu.floppy1_path": "",
    "test_startqemu.floppy1_size": "",
    "test_startqemu.floppy2_path": "",
    "test_startqemu.floppy2_size": "",
    "test_startqemu.hdd1_persist": "",
    "test_startqemu.hdd1_qcow_path": "",
    "test_startqemu.hdd1_template": "",
    "test_startqemu.mac_address": "",
    "test_startqemu.machine": "",
    "test_startqemu.memory": "",
    "test_startqemu.net_device": "",
    "test_startqemu.prom_env": "",
    "test_startqemu.sound_device": "",
    "test_startqemu.sourcecode_dir": "",
    "test_startqemu.srcdisk_size_mb": "",
    "test_startqemu.takeascreenshot": "",
    "test_startqemu.vga": "",
    "test_startqemu.vnc_port": "",
    "test_ocrwordsearch.attemptdelay": "",
    "test_ocrwordsearch.numberofattempts": "",
    "test_ocrwordsearch.successphrase": "",
    "test_ocrwordsearch.failphrase": "",
    "test_ocrwordsearch.require_success": "",
    "test_ocrwordsearch.startx": "",
    "test_ocrwordsearch.starty": "",
    "test_ocrwordsearch.stopx": "",
    "test_ocrwordsearch.stopy": "",
    "test_ocrwordsearch.takeascreenshot": "",
    "test_sendspecialkeys.delay": "",
    "test_sendspecialkeys.keys": "",
    "test_sendspecialkeys.name": "",
    "test_sendspecialkeys.takeascreenshot": "",
    "test_filecontains.file_path": "",
    "test_filecontains.successphrase": "",
    "test_filecontains.timeout": "",
    "test_filecontains.failphrase": "",
    "test_start_gif_capture.interval": "",
    "test_start_gif_capture.max_frames": "",
    "test_start_gif_capture.max_seconds": "",
    "test_start_gif_capture.name": "",
    "test_start_gif_capture.playback_speed": "",
    "test_start_gif_capture.scale": "",
    "test_stop_gif_capture.name": "",
}

PATHS = init_test_env(CONFIG, __name__)
