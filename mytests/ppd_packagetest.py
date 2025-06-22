import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers import register_packagetest, load_snapshot, send_monitor_string, take_screenshots_to_gif, take_screenshot, ocr_word_find, start_playtest_qemu, make_floppy_image, attach_floppy_to_qemu
import time





from helpers import register_testfile
register_testfile(
    id="Pacific C",
    types=["package"],
    system="qemu",
    platform="MSDOS i386",
)(sys.modules[__name__])


@register_packagetest("Test1 - Start QEMU")
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
    

@register_packagetest("Test2 - print something")
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

