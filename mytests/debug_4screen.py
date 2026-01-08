import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #auto import /testsrc/mytests dir as modules
TESTSRC_TESTLISTDIR = "/testsrc/mytests"    # individual test-cases
TESTSRC_BASEDIR = "/testsrc"                # root dir of git repo vice-specific test src
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"    # vicehelpers.py lives here

# make app helpers dir visible
if TESTSRC_HELPERDIR  not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR )

from apphelpers import register_buildtest, register_testfile
from qemuhelpers import copy_to_fat_image, copy_from_fat_image, ocr_word_find, ppdcompile, convert_raw_to_qcow2, make_floppy_image
from qemuhelpers import QemuInstance  # adjust path if needed
import time

testfailstatus = 0




register_testfile(
    id="Debug Fourscreens",
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
    return success, "\n".join(log)

@register_buildtest("Build 2 - convert hdd.img to 4xhdd1-4.qcow2")
def test2_diskconv(context):
    stdout_lines = []
    log = []
    count = 4
    for i in range(1, count + 1):
        qcow2_name = "4xhdd" + str(i) + ".qcow2"
        success, output = convert_raw_to_qcow2("hdd.img", qcow2_name)
        if not success:
            print(f"Failed to convert to {qcow2_name}: {output}")
    log.append(output)
    return success, "\n".join(log)


@register_buildtest("Build 3 - Start multiple QEMU instances")
def test3_start_multiple_qemu(context):
    base_port = 55555
    count = 4

    log = []
    context["qemu_instances"] = []

    for i in range(1, count + 1):
        name = f"qemu{i}"
        port = base_port + i - 1
        image_path = f"4xhdd{i}.qcow2"  # distinct image per instance
        log.append(f"Starting {name} on port {port} with image={image_path}")
        instance = QemuInstance(name, image_path, port)
        started = instance.start()
        context[name] = instance  # Add this line inside your for-loop
        if not started:
            success, logs_or_msg = instance.collect_qemu_logs(f"reports/{name}_stdout.log")
            log.append(f"Failed to start {name}.")
            log.append(logs_or_msg)
            context["abort"] = True
            return False, "\n".join(log)

        time.sleep(1)  # wait a bit before checking readiness

        if not instance.wait_for_ready():
            log.append(f"{name} did not become ready.")
            success, logs_or_msg = instance.collect_qemu_logs(f"reports/{name}_stdout.log")
            log.append(logs_or_msg)
            context["abort"] = True
            return False, "\n".join(log)

        context["qemu_instances"].append(instance)
        log.append(f"{name} is ready.")

    return True, "\n".join(log)







@register_buildtest("Build 5 - Boot to Dos")
def test5_bootdos(context):
    instance_name = "qemu1" 
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"

    log = []
    time.sleep(3)  # wait for DOS to boot

    searchphrase = "msdos ready"
    success, ocr_text, attempts, ocrlog = ocr_word_find(
        instance,
        searchphrase,
        timeout=10,
        startx=0,
        starty=0,
        stopx=160,
        stopy=480
    )

    ok, msg = instance.take_screenshot("reports/test4")
    if not ok:
        log.append(f"[{instance.name}] Screenshot failed: {msg}")
    else:
        log.append(f"[{instance.name}] Screenshot taken: {msg}")

    log.append("Checked DOS prompt")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)
    log.append("ocr'd text:")
    log.append(ocr_text)

    return True, "\n".join(log)






@register_buildtest("Build 5 - send test text")
def test5_startppd(context):
    instance_name = "qemu1"  
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"
    stdout_lines = []
    log = []

    searchphrase = "HI-TECH"
    instance.send_keyboardstring("cd pacific\n")
    log.append("cd pacific")
    instance.send_keyboardstring("cd bin\n")
    log.append("cd bin")
    instance.send_keyboardstring("ppd c:\\src\\bartest.c \n")
    success, ocr_text, attempts, ocrlog = ocr_word_find(instance, searchphrase, timeout=10, startx=0, starty=315, stopx=640, stopy=480)
    instance.take_screenshot("reports/test5")
    log.append("PPD Starting test")
    log.append(f"number of ocr attempts: {attempts}")
    log.append(ocr_text)
    log.append("ocr function log:")
    log.extend(ocrlog)
    return success, "\n".join(log)

