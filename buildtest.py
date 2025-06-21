from helpers import register_buildtest  # import the decorator
from helpers import copy_to_fat_image, copy_from_fat_image, ocr_word_find, send_monitor_string, ppdcompile, take_screenshot, send_monitor_key, save_snapshot, start_buildtest_qemu, convert_raw_to_qcow2, attach_floppy_to_qemu, detach_floppy_from_qemu
import time

testfailstatus = 0




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
        qemu_process = helpers.start_buildtest_qemu()

        # Thread to read stdout continuously and append to log
        def read_stdout(proc, log_list):
            for line in iter(proc.stdout.readline, ''):
                log_list.append(line.rstrip())
            proc.stdout.close()

        qemu_thread = threading.Thread(target=read_stdout, args=(qemu_process, log))
        qemu_thread.daemon = True
        qemu_thread.start()

        # Wait for monitor socket to become available
        sock = helpers.wait_for_monitor(timeout=30)  # Add timeout if possible
        if not sock:
            return False, "Failed to connect to QEMU monitor socket.\n" + "\n".join(log)

        # Extra delay to let QEMU settle
        time.sleep(0.1)

        context["sock"] = sock
        context["qemu_process"] = qemu_process
        return True, "QEMU started successfully.\n" + "\n".join(log)

    except Exception as e:
        log.append(f"Exception starting QEMU: {e}")
        return False, "\n".join(log)




@register_buildtest("Build 4 - Boot to Dos")
def test4_bootdos(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"
    stdout_lines = []
    log = []
    time.sleep(3) # wait for dos to boot before starting OCR

    searchphrase = "msdos ready"
    success, ocr_text, attempts, ocrlog = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=0, stopx=160, stopy=480)
    take_screenshot(sock, "reports/test4")
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