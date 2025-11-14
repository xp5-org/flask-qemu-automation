import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from helpers import register_buildtest, register_testfile
from qemuhelpers import copy_to_fat_image, copy_from_fat_image, ocr_word_find, ppdcompile, convert_raw_to_qcow2, make_floppy_image
from qemuhelpers import QemuInstance  # adjust path if needed
import time

testfailstatus = 0




register_testfile(
    id="Pacific C",
    types=["build"],
    system="qemu",
    platform="MSDOS i386",
)(sys.modules[__name__])


#@register_buildtest("Build 1 - Copy files to hdd.img")
def test1_copy_files(context):
    stdout_lines = []
    log = []
    success,output = copy_to_fat_image("sourced", "hdd.img")
    log.append(output)
    return success, "\n".join(log)

#@register_buildtest("Build 2 - convert hdd.img to hdd.qcow2")
def test2_diskconv(context):
    stdout_lines = []
    log = []
    success, output = convert_raw_to_qcow2("hdd.img", "hdd.qcow2")
    log.append(output)
    return success, "\n".join(log)





@register_buildtest("Build 3 - Start QEMU using class")
def test3_start_qemu(context):
    name = "qemu0"
    cpuarch = "i386"
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






@register_buildtest("Build 5 - Start PPD")
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

@register_buildtest("Build 6 - PPD Compile")
def test6_ppdcompile(context):
    instance_name = "qemu1"  
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"
    searchphrase = "success"
    errorphrase = "error"
    stdout_lines = []
    log = []

    log.append("PPD Compile test")
    start_time = time.time()
    instance.send_specialkeys("f3")
    time.sleep(1)
    instance.send_specialkeys("ret")
    time.sleep(1)
    instance.send_specialkeys("F")
    time.sleep(1)
    instance.send_specialkeys("ret")
    time.sleep(1)
    instance.send_specialkeys("ret")
    time.sleep(1)
    instance.send_specialkeys("ret")
    time.sleep(1)
    time.sleep(5)
    status, ocr_text, attempts, ocrlog = ocr_word_find(instance, searchphrase, timeout=10, startx=0, starty=295, stopx=640, stopy=480, errorphrase=errorphrase)

    instance.take_screenshot("reports/test6")
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
    instance_name = "qemu1"  
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"
    stdout_lines = []
    log = []
    searchphrase = "msdos"

    instance.send_specialkeys("f", alt=True, delay=0.1)
    time.sleep(0.5)
    instance.send_specialkeys("q", delay=0.1)
    time.sleep(0.5)
    success, ocr_text, attempts, ocrlog = ocr_word_find(instance, searchphrase, timeout=10, startx=0, starty=0, stopx=160, stopy=480)
    instance.take_screenshot("reports/test7")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)
    log.append("OCR text detected:")
    log.append(ocr_text)
    return success, "\n".join(log)

#@register_buildtest("Build8 - create & mount floppy")
def test8_mountfloppy(context):
    instance_name = "qemu1"  
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"

    log = []
    floppyimage = "tmpfloppydisk.img"

    make_floppy_image(floppyimage)

    success, output = QemuInstance.attach_floppy()
    log.append(output)
    if not success:
        print('Error attaching floppy disk image: ', floppyimage)
        return False, "\n".join(log)

    time.sleep(1)  # Allow QEMU to finish mounting before continuing
    return True, "\n".join(log)

#@register_buildtest("Build9 - format floppy")
def test9_formatfloppy(context):
    instance_name = "qemu1"  
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"

    log = []

    instance.send_keyboardstring("format a: /q /s \n")
    time.sleep(2)
    instance.send_keyboardstring("\n")
    time.sleep(3)
    instance.send_keyboardstring("\n")
    time.sleep(3)
    instance.send_keyboardstring("N \n")
    output = "todo: ocr output here someday"
    log.append(output)
    time.sleep(5)  # replace this with OCR
    success = True # fake it, ocr output later
    if not success:
        return False, "\n".join(log)

    return True, "\n".join(log)


#@register_buildtest("Test10 - copy to floppy")
def test10_copy2floppy(context):
    instance_name = "qemu1"  
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"

    log = []

    success, output = instance.send_keyboardstring("copy c:\\src\\*.* a:\\\n")
    log.append(output)
    success = True # fake it
    if not success:
        return False, "\n".join(log)

    time.sleep(3) # replace this with OCR
    return True, "\n".join(log)


@register_buildtest("Build 11 - detatch floppy")
def test8_removefloppy(context):
    instance_name = "qemu1"  
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"

    log = []

    success, output = instance.detatch_floppy()
    log.append(output)
    if not success:
        return False, "\n".join(log)
    return True, "\n".join(log)


@register_buildtest("Build 12 - take snapshot")
def test11_takesnap(context):
    instance_name = "qemu1"  
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"
    stdout_lines = []
    log = []

    success, output = instance.save_snapshot()
    log.append(output)
    return success, "\n".join(log)

#@register_buildtest("Test10 - copy output from hdd img")
def test10_copy_files(context):
    stdout_lines = []
    log = []

    success, output = copy_from_fat_image("targetd", "hdd.img")
    log.append(output)
    return success, "\n".join(log)