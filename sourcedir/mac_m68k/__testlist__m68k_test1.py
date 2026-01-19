import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #auto import /testsrc/mytests dir as modules
#TESTSRC_TESTLISTDIR = "/testsrc/mytests"    # individual test-cases
TESTSRC_BASEDIR = "/testsrc"                # root dir of git repo vice-specific test src
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"    # vicehelpers.py lives here

# make app helpers dir visible
if TESTSRC_HELPERDIR  not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR )

from apphelpers import register_buildtest, register_testfile
from qemuhelpers import ocr_word_find
from qemuhelpers import QemuInstance
from qemuhelpers import MouseAction




register_testfile(
    id="m68k mac",
    types=["build"],
    system="qemu",
    platform="mac m68k", # this makes new webpage category
)(sys.modules[__name__])

@register_buildtest("Build 1 - Start QEMU using class")
def test1_start_qemu(context):
    name = "qemu0"
    cpuarch = "m68k"
    port = 55555
    image_path = "hdd.qcow2"
    #floppy_path = "tmpfloppydisk.img"

    log = [f"Starting {name} on port {port} with image={image_path}"]

    instance = QemuInstance(name, cpuarch, image_path, port)

    # Give QEMU some time to initialize and generate output
    time.sleep(3)

    if not instance.start():
        # Collect whatever logs we can get immediately after failed start
        success, logs_or_msg = instance.collect_qemu_logs("reports/qemu_stdout.log")
        log.append("Failed to start QEMU.")
        log.append(logs_or_msg)
        context["abort"] = True
        return False, "\n".join(log)

    success, logs_or_msg = instance.collect_qemu_logs("reports/qemu_stdout.log")
    log.append(logs_or_msg)

    if not instance.wait_for_ready():
        log.append(f"{name} did not become ready.")
        # Add logs collected so far
        log.append(logs_or_msg)
        return False, "\n".join(log)

    context[name] = instance
    log.append(f"{name} is ready.")
    context["qemu1"] = instance
    log.append(logs_or_msg)
    return True, "\n".join(log)


@register_buildtest("Build 2 - Boot to System7")
def test2_bootdos(context):
    instance_name = "qemu1" 
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"

    log = []
    time.sleep(3)  # wait for DOS to boot

    searchphrase = "Mac OS"
    success, ocr_text, attempts, ocrlog = ocr_word_find(
        instance,
        searchphrase,
        timeout=10,
        startx=0,
        starty=0,
        stopx=160,
        stopy=480
    )

    success, msg = instance.take_screenshot(test_step=2)
    if not success:
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


@register_buildtest("Build 3 - find mac close box window by image match")
def test3_startmac(context):
    instance_name = "qemu1"
    instance = context.get(instance_name)

    success, log = MouseAction.closedialogbutton(instance, test_step=3)
    if not success:
        context["abort"] = True

    return success, log


@register_buildtest("Build 4 - find mac title bar window by image match")
def test4_mac(context):
    instance_name = "qemu1"
    instance = context.get(instance_name)

    success, log = MouseAction.findandclicktitlebar(instance, test_step=4)
    if not success:
        context["abort"] = True

    return success, log


@register_buildtest("Build 6 - terminate all")
def test6_stopall(context):
    log = []
    print("waiting 3s before teardown")
    time.sleep(3)
    instance_name = "qemu1"  
    instance = context.get(instance_name)
    log.append(f"Stopping {instance_name}")
    instance.stop()
    log.append(f"{instance_name} has exited.")
    if not log:
        log.append("No QEMU instances found to stop.")
    return True, "\n".join(log)
