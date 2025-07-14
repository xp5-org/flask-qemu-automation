import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers import register_testfile  # import the decorator
from helpers import register_buildtest
from helpers import copy_to_fat_image, copy_from_fat_image, ocr_word_find, send_monitor_string, ppdcompile, take_screenshot, send_monitor_key, save_snapshot, start_buildtest_qemu, convert_raw_to_qcow2, attach_floppy_to_qemu, detach_floppy_from_qemu



import time

testfailstatus = 0



register_testfile(
    id="DJGPP",
    types=["build"],
    system="qemu",
    platform="MSDOS i386",
)(sys.modules[__name__])


@register_buildtest("Build 1 - Copy files to hdd.img")
def test1_copy_files(context):
    stdout_lines = []
    log = []
    success,output = copy_to_fat_image("sourced", "hdd.img")
    log.append(output)
    # test code here, return (success, log_output)
    return success, "\n".join(log)

@register_buildtest("Build 2 - convert hdd.img to hdd.qcow2")
def test2_diskconv(context):
    stdout_lines = []
    log = []
    success, output = convert_raw_to_qcow2()
    log.append(output)
    # test code here, return (success, log_output)
    return success, "\n".join(log)



@register_buildtest("Build 3 - Start QEMU")
def test3_start_qemu(context):
    import threading
    import time
    import helpers

    log = []
    try:
        qemu_process = helpers.start_playtest_qemu()

        # stdout capture thread
        def read_stdout(proc, log_list):
            for line in iter(proc.stdout.readline, ''):
                log_list.append(line.rstrip())
            proc.stdout.close()

        # qemu in its own thread
        qemu_thread = threading.Thread(target=read_stdout, args=(qemu_process, log))
        qemu_thread.daemon = True
        qemu_thread.start()

        # wait for monitor socket
        sock = helpers.wait_for_monitor(timeout=5)
        if not sock:
            return False, "Failed to connect to QEMU monitor socket.\n" + "\n".join(log)

        context["sock"] = sock
        context["qemu_process"] = qemu_process
        return True, "QEMU started successfully.\n" + "\n".join(log)

    except Exception as e:
        log.append(f"Exception starting QEMU: {e}")
        return False, "\n".join(log)



