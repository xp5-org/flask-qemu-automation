from helpers import register_buildtest  # import the decorator
from helpers import copy_to_fat_image, copy_from_fat_image, ocr_word_find, send_monitor_string, ppdcompile, take_screenshot, send_monitor_key, save_snapshot
import time


@register_buildtest("Build 1 - Copy files to hdd.img")
def test1_copy_files(sock):
    stdout_lines = []
    log = []

    success,output = copy_to_fat_image("sourced", "hdd.img")
    log.append("Test1 message")
    print(output)
    print(success)
    # test code here, return (success, log_output)
    return success, "\n".join(log)

@register_buildtest("Build 2 - Boot to Dos")
def test2_bootdos(sock):
    stdout_lines = []
    log = []
    time.sleep(5) # wait for dos to boot

    searchphrase = "msdos ready"
    success, ocr_text, attempts, ocrlog = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=0, stopx=160, stopy=480)
    take_screenshot(sock, "reports/test2")
    log.append("Checked DOS prompt")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)
    return success, "\n".join(log)

@register_buildtest("Build 3 - Start PPD")
def test3_startppd(sock):
    stdout_lines = []
    log = []

    searchphrase = "HI-TECH"
    print("test2")
    send_monitor_string(sock, "cd pacific\n")
    log.append("cd pacific")
    send_monitor_string(sock, "cd bin\n")
    log.append("cd bin")
    send_monitor_string(sock, "ppd\n")
    success, ocr_text, attempts, ocrlog = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=315, stopx=640, stopy=480)
    take_screenshot(sock, "reports/test3")
    log.append("PPD Starting test")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)
    # test code here, return (success, log_output)
    return success, "\n".join(log)

@register_buildtest("Build 4 - PPD Compile")
def test4_ppdcompile(sock):
    searchphrase = "success"
    stdout_lines = []
    log = []

    log.append("PPD Compile test")
    ppdcompile(sock)
    time.sleep(5)
    success, ocr_text, attempts, ocrlog = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=315, stopx=640, stopy=480)
    take_screenshot(sock, "reports/test4")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)
    # test code here, return (success, log_output)
    return success, "\n".join(log)

@register_buildtest("Build 5 - Quit to DOS")
def test5_quitppd(sock):
    stdout_lines = []
    log = []
    searchphrase = "msdos"

    send_monitor_key(sock, "f", alt=True, delay=0.1)
    time.sleep(0.5)
    send_monitor_key(sock, "q", delay=0.1)
    time.sleep(0.5)
    success, ocr_text, attempts, ocrlog = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=0, stopx=160, stopy=480)
    take_screenshot(sock, "reports/test5")
    log.append(f"number of ocr attempts: {attempts}")
    log.append("ocr function log:")
    log.extend(ocrlog)
    # test code here, return (success, log_output)
    return success, "\n".join(log)

@register_buildtest("Test 6 - take snapshot")
def test6_takesnap(sock):
    stdout_lines = []
    log = []

    success, output = save_snapshot(sock)
    log.append(output)
    return success, "\n".join(log)

@register_buildtest("Test7 - copy output from hdd img")
def test7_copy_files(sock):
    stdout_lines = []
    log = []

    success, output = copy_from_fat_image("targetd", "hdd.img")
    log.append(output)
    # test code here, return (success, log_output)
    return success, "\n".join(log)