import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers import register_playtest, load_snapshot, send_monitor_string, take_screenshots_to_gif, take_screenshot, ocr_word_find, start_playtest_qemu, make_floppy_image, attach_floppy_to_qemu
import time





from helpers import register_testfile
register_testfile(
    id="Pacific C",
    types=["play"],
    system="qemu",
    platform="MSDOS i386",
)(sys.modules[__name__])




@register_playtest("Test1 - Start QEMU")
def test3_start_qemu(context):
    import threading
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
    

@register_playtest("Test2 - launch from snap1")
def test2_startvm(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"
    stdout_lines = []
    log = []
    # Load the snapshot by name
    success, output = load_snapshot(sock, "snap1")
    log.append(output)
    take_screenshot(sock, "reports/test1")
    return success, "\n".join(log)


@register_playtest("Test3 - start bartest")
def test3_startprog(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"
    stdout_lines = []
    log = []
    send_monitor_string(sock, "cd c:\\src \n")
    send_monitor_string(sock, "bartest\n")
    take_screenshot(sock, "reports/test3")
    return True, "\n".join(log) # assume it started


@register_playtest("Test4 - capture screen")
def test4_screencapture(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"
    stdout_lines = []
    log = []
    success, output = take_screenshots_to_gif(sock, 1, 5, gif_name="test4.gif")
    time.sleep(1)
    log.append(output)
    return success, "\n".join(log)

@register_playtest("Test5 - quit to dos prompt")
def test5_quittodos(context):
    sock = context.get("sock")
    if not sock:
        return False, "No QEMU monitor socket available"
    stdout_lines = []
    log = []
    send_monitor_string(sock, "qqq\n")
    send_monitor_string(sock, "qqq\n")
    searchphrase = "bad"
    success, ocr_text, attempts, ocrlog = ocr_word_find(sock, searchphrase, timeout=10)
    time.sleep(1)
    take_screenshot(sock, "reports/test5")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)
    log.append("OCR text detected:")
    log.append(ocr_text)
    return success, "\n".join(log)



