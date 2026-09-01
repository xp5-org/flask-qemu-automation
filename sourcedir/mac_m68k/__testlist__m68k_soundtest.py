import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# M68K Sound Test — end-to-end Retro68 build+run test, cloned from
# __testlist__m68k_retro68.py's structure, with the same wav-capture +
# Goertzel tone verification pyhelpers/mediahelpers.py already provides for
# owc_sb16soundtest (see that project's testlist for the i386/SB16 version):
#   1. Cross-compile soundtest.c on the Linux host -> SoundTest.dsk (HFS)
#   2. Boot the q800 with that .dsk attached + the on-board ASC/EASC sound
#      chip's output captured to a .wav (audio_backend="wav") + serial capture
#   3. Open the mounted disk, then the app, from the Finder (keyboard, same
#      as __testlist__m68k_cuberotate.py)
#   4. Verify the run three independent ways:
#        - serial log contains the start+ok tokens (OCR-free)
#        - OCR reads the ok token off the on-screen status line
#        - the .wav capture actually contains all 3 distinct tones
#          (test_audio_tonesequence — detect_tone alone can't handle more
#          than one frequency, since only one can ever be "loudest overall")
# Paths are {tokens} resolved against CONFIG, not f-strings on a module
# constant: CONFIG has to stay a literal dict or the runner cannot read it
# statically (testbuilder, step validation, cloning). The app's tokens are
# RETRO68_SOUND_START / RETRO68_SOUND_OK and its tones are 440/660/880 Hz
# (must match `tones[]` in soundtest.c) — all spelled out in the steps below.
CONFIG = {
    "parent": "mac_m68k",
    "projdir": "mac_m68k",
    "instance_name": "qemu1",
    "function": "build4",
    "hdd1_qcow": "hdd.qcow2",
    "projbasedir": "/testsrc/sourcedir/",
    "app_dir": "soundtest",
    "app_disk": "SoundTest.dsk",
    "serial_path": "{projbasedir}{projdir}/{app_dir}/output/serial.log",
    # Audio — the q800 machine's on-board ASC/EASC chip is captured the same
    # way owc_sb16soundtest captures the SB16: QEMU's "wav" audiodev writes
    # straight to this file, no audio daemon needed. sound_device just needs
    # to be truthy here (unlike i386's "sb16", it does not name a QEMU
    # -device — the q800 branch of build_qemu_args binds the audiodev onto
    # the -M machine string's audiodev= property instead, since ASC is
    # on-board, not an addable card).
    "sound_device": "asc",
    "audio_backend": "wav",
    "audio_out_path": "{projbasedir}{projdir}/{app_dir}/output/sound_capture.wav",
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
            # 1. Host-side cross-compile -> SoundTest.dsk
            "action": "test_hostbuild",
            "param": {
                "command": "./build.sh",
                "cwd": "{projbasedir}{projdir}/{app_dir}",
                "timeout": "600"
            },
            "subaction": ""
        },
        {
            # 2. Boot q800 with the compiled disk (scsi-id 2) + audio + serial
            "action": "test_startqemu",
            "param": {
                "cpuarch": "m68k",
                "name": "qemu1",
                "port": 55555,
                "hdd2_path": "{projbasedir}{projdir}/{app_dir}/{app_disk}",
                "hdd2_prepare": "false",
                "serial_path": "{serial_path}",
                "sound_device": "asc",
                "audio_backend": "wav",
                "audio_out_path": "{audio_out_path}"
            },
            "subaction": ""
        },
        {
            # 3a. Wait for the READY DESKTOP -- specifically the "Trash" label,
            # which only appears once the Finder is up. Do NOT match "Mac OS"
            # here: that string is on the "Mac OS - Starting Up..." boot splash
            # too, so it passes while the machine is still loading extensions,
            # and the launch keystrokes below then fire into a system with no
            # Finder and are silently lost. Generous attempt budget because
            # 7.6.1 + extensions can take a while to reach the desktop.
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "numberofattempts": "10",
                "successphrase": "Trash"
            },
            "subaction": ""
        },
        {
            # 3b. Close any auto-opened Finder windows first. At boot the
            # "Untitled" boot-HD window (and possibly the CD's) is already open
            # and FRONTMOST -- so a type-selection would land inside that window
            # (it selected+opened SimpleText, whose name also starts with S,
            # instead of the SoundTest disk). Cmd-W closes the frontmost window;
            # several of them clear the stack so the desktop itself gets focus.
            "action": "test_sendspecialkeys",
            "param": {
                "keys": "meta_l-w, meta_l-w, meta_l-w, meta_l-w, meta_l-w",
                "delay": "1",
                "name": "qemu1"
            },
            "subaction": ""
        },
        {
            # 3c. Now the desktop has focus. Select + open the SoundTest disk by
            # TYPE-SELECTION: typing a letter selects the icon whose name starts
            # with it. Deterministic, unlike relying on auto-selection -- a SCSI
            # disk present at boot is shown but NOT auto-selected. "s" is unique
            # among desktop items (Mac OS.../Untitled/SoundTest/Trash) so it
            # picks "SoundTest"; Cmd-O opens its window.
            "action": "test_sendspecialkeys",
            "param": {
                "keys": "s, meta_l-o",
                "delay": "3",
                "name": "qemu1"
            },
            "subaction": ""
        },
        {
            # 3d. The disk window is now frontmost; type-select "SoundTest" (the
            # app, the only item in the window) and Cmd-O to launch it.
            "action": "test_sendspecialkeys",
            "param": {
                "keys": "s, meta_l-o",
                "delay": "3",
                "name": "qemu1"
            },
            "subaction": ""
        },
        {
            # 4a. OCR-free verification: a full 3-tone cycle finished and
            # wrote its status token to the serial port. Also paces the run
            # long enough for at least one full cycle (3s of tones) to land
            # in the .wav before teardown.
            "action": "test_filecontains",
            "param": {
                "file_path": "{serial_path}",
                "successphrase": "RETRO68_SOUND_OK",
                "timeout": "30"
            },
            "subaction": ""
        },
        {
            # 4b. OCR verification: the status line printed to the console
            # window once the first cycle completes.
            "action": "test_ocrwordsearch",
            "param": {
                "attemptdelay": "2",
                "numberofattempts": "5",
                "successphrase": "RETRO68_SOUND_OK",
                "require_success": "true"
            },
            "subaction": ""
        },
        {
            # test_terminate_all sleeps 3s before stopping the VM — gives the
            # wav audiodev a moment to flush any buffered PCM, and QEMU only
            # backfills the RIFF header on a clean exit either way.
            "action": "test_terminate_all",
            "param": {},
            "subaction": ""
        },
        {
            # 4c. All three tones are actually present in the capture.
            "action": "test_audio_tonesequence",
            "param": {
                "wav_path": "{audio_out_path}",
                "expect_hz_list": "440,660,880",
                "tolerance_hz": 60,
                "min_snr_db": 10,
                "require_success": "true"
            },
            "subaction": ""
        }
    ],
}

PATHS = init_test_env(CONFIG, __name__)
