import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from helpers import register_buildtest, register_testfile
from qemuhelpers import copy_to_fat_image, copy_from_fat_image, ocr_word_find, ppdcompile, convert_raw_to_qcow2
from qemuhelpers import QemuInstance  # adjust path if needed
import time

testfailstatus = 0




register_testfile(
    id="Pacific C",
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

@register_buildtest("Build 2 - convert hdd.img to hdd.qcow2")
def test2_diskconv(context):
    stdout_lines = []
    log = []
    success, output = convert_raw_to_qcow2()
    log.append(output)
    return success, "\n".join(log)





@register_buildtest("Build 3 - Start QEMU using class")
def test3_start_qemu(context):
    name = "qemu0"
    port = 55555
    image_path = "hdd.qcow2"
    floppy_path = "tmpfloppydisk.img"

    log = [f"Starting {name} on port {port} with image={image_path}"]

    instance = QemuInstance(name, image_path, port, floppy_path=floppy_path)

    if not instance.start():
        log.append(f"{name} failed to start or connect to monitor.")
        context["abort"] = True
        return False, "\n".join(log)

    if not instance.wait_for_ready():
        log.append(f"{name} did not become ready.")
        log.append(f"{name} stdout:\n{''.join(instance.get_output())}")
        return False, "\n".join(log)

    context[name] = instance
    log.append(f"{name} is ready.")
    log.append(f"{name} stdout:\n{''.join(instance.get_output())}")
    return True, "\n".join(log)





@register_buildtest("Build 4 - Boot to Dos")
def test4_bootdos(context):
    instance = context.get("qemu_instance")
    if not instance:
        return False, "No QEMU instance available in context"

    log = []
    time.sleep(3)  # wait for DOS to boot

    searchphrase = "msdos ready"
    success, ocr_text, attempts, ocrlog = ocr_word_find(
        instance.sock,
        searchphrase,
        timeout=10,
        startx=0,
        starty=0,
        stopx=160,
        stopy=480
    )

    ok, msg = instance.take_screenshot("reports/test4.png")
    if not ok:
        log.append(f"[{instance.name}] Screenshot failed: {msg}")
    else:
        log.append(f"[{instance.name}] Screenshot taken: {msg}")

    log.append("Checked DOS prompt")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)

    return success, "\n".join(log)





@register_buildtest("Build 5 - Start PPD")
def test5_startppd(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"
    stdout_lines = []
    log = []

    searchphrase = "HI-TECH"
    send_monitor_string(sock, "cd pacific\n")
    log.append("cd pacific")
    send_monitor_string(sock, "cd bin\n")
    log.append("cd bin")
    send_monitor_string(sock, "ppd c:\\src\\bartest.c \n")
    success, ocr_text, attempts, ocrlog = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=315, stopx=640, stopy=480)
    take_screenshot(sock, "reports/test5")
    log.append("PPD Starting test")
    log.append(f"number of ocr attempts: {attempts}")
    log.append(ocr_text)
    log.append("ocr function log:")
    log.extend(ocrlog)
    return success, "\n".join(log)

@register_buildtest("Build 6 - PPD Compile")
def test6_ppdcompile(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"
    searchphrase = "success"
    errorphrase = "error"
    stdout_lines = []
    log = []

    log.append("PPD Compile test")
    ppdcompile(sock)
    time.sleep(5)
    status, ocr_text, attempts, ocrlog = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=295, stopx=640, stopy=480, errorphrase=errorphrase)

    take_screenshot(sock, "reports/test6")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)
    log.append("OCR text detected:")
    log.append(ocr_text)
    if not status:
        context["abort"] = True
        # abandon other tests if this pdd compile fails

    return status, "\n".join(log)

@register_buildtest("Build 7 - Quit to DOS")
def test7_quitppd(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"
    stdout_lines = []
    log = []
    searchphrase = "msdos"

    send_monitor_key(sock, "f", alt=True, delay=0.1)
    time.sleep(0.5)
    send_monitor_key(sock, "q", delay=0.1)
    time.sleep(0.5)
    success, ocr_text, attempts, ocrlog = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=0, stopx=160, stopy=480)
    take_screenshot(sock, "reports/test7")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)
    return success, "\n".join(log)

#@register_buildtest("Build8 - mount floppy")
def test8_mountfloppy(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"

    log = []


    success, output = attach_floppy_to_qemu("tmpfloppydisk.img")
    log.append(output)
    if not success:
        return False, "\n".join(log)

    time.sleep(1)  # Allow QEMU to finish mounting before continuing
    return True, "\n".join(log)

#@register_buildtest("Build9 - format floppy")
def test9_formatfloppy(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"

    log = []

    send_monitor_string(sock, "format a: /q /s \n")
    time.sleep(2)
    send_monitor_string(sock, "\n")
    time.sleep(3)
    send_monitor_string(sock, "\n")
    time.sleep(3)
    send_monitor_string(sock, "N \n")
    output = "todo: ocr output here someday"
    log.append(output)
    time.sleep(5)  # replace this with OCR
    success = True # fake it, ocr output later
    if not success:
        return False, "\n".join(log)

    return True, "\n".join(log)


#@register_buildtest("Test10 - copy to floppy")
def test10_copy2floppy(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"

    log = []

    success, output = send_monitor_string(sock, "copy c:\\src\\*.* a:\\\n")
    log.append(output)
    success = True # fake it
    if not success:
        return False, "\n".join(log)

    time.sleep(3) # replace this with OCR
    return True, "\n".join(log)


@register_buildtest("Build 11 - detatch floppy")
def test8_removefloppy(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"

    log = []

    success, output = detach_floppy_from_qemu(sock)
    log.append(output)
    if not success:
        return False, "\n".join(log)
    return True, "\n".join(log)


@register_buildtest("Build 12 - take snapshot")
def test11_takesnap(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"
    stdout_lines = []
    log = []

    success, output = save_snapshot(sock)
    log.append(output)
    return success, "\n".join(log)

#@register_buildtest("Test10 - copy output from hdd img")
def test10_copy_files(context):
    stdout_lines = []
    log = []

    success, output = copy_from_fat_image("targetd", "hdd.img")
    log.append(output)
    return success, "\n".join(log)