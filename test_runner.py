import os
import time
import subprocess
import socket
import tempfile
import re
import threading
import datetime
from PIL import Image
import pytesseract
import shutil

QEMU_IMAGE = "hdd.qcow2"
MONITOR_PORT = 55555
PROGRESS_FILE = "progress.txt"
REPORT_DIR = "reports"
qemu_process = None
compile_logs_dir = "compile_logs"


def flush_monitor_banner(sock):
    sock.settimeout(1.0)
    try:
        banner = sock.recv(1024)
        print("[monitor banner]", banner.decode("utf-8", errors="replace").strip())
    except socket.timeout:
        print("[monitor banner] no banner received")
    except Exception as e:
        print(f"[monitor banner error] {e}")

def take_screenshot(sock, name="screenshot"):
    name = name.replace(" ", "_")  # replace spaces in filename
    ppm_path = os.path.abspath(name + ".ppm")
    png_path = os.path.abspath(name + ".png")
    time.sleep(0.5)
    sock.sendall(f"screendump {ppm_path}\n".encode("utf-8"))
    time.sleep(0.5)
    start = time.time()
    while not os.path.exists(ppm_path):
        if time.time() - start > 5:
            raise RuntimeError(f"Timed out waiting for screendump {ppm_path}")
        time.sleep(0.1)
    try:
        img = Image.open(ppm_path)
        img.save(png_path)
    except Exception as e:
        raise RuntimeError(f"Failed to convert {ppm_path} to PNG: {e}")

def copy_to_fat_image(src_dir, image_path):
    log = []
    mtools_config = f'drive h: file="{image_path}" offset=32256\n'
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write(mtools_config)
        config_path = tmp.name

    try:
        try:
            result = subprocess.run(
                f'MTOOLSRC={config_path} mcopy -n -o -s {src_dir}/* h:/src/',
                shell=True,
                check=True,
                executable="/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            output = result.stdout.decode('utf-8', errors='replace')
            log.append(output)
            return True, output
        except subprocess.CalledProcessError as e:
            output = e.stdout.decode('utf-8', errors='replace') if e.stdout else ''
            log.append(output)
            return False, output
    finally:
        os.unlink(config_path)

def copy_from_fat_image(dst_dir, image_path):
    log = []
    os.makedirs(dst_dir, exist_ok=True)
    mtools_config = f'drive h: file="{image_path}" offset=32256\n'
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write(mtools_config)
        config_path = tmp.name

    try:
        try:
            result = subprocess.run(
                f'MTOOLSRC={config_path} mcopy -n -o -s h:/src/ {dst_dir}/',
                shell=True,
                check=True,
                executable="/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            output = result.stdout.decode('utf-8', errors='replace')
            log.append(output)           
            return True, output
        except subprocess.CalledProcessError as e:
            output = e.stdout.decode('utf-8', errors='replace') if e.stdout else ''
            log.append(output)
            return False, output
    finally:
        os.unlink(config_path)

def send_monitor_key(sock, keyname, ctrl=False, alt=False, shift=False, delay=0.1):
    mods = []
    if ctrl: mods.append("ctrl")
    if alt: mods.append("alt")
    if shift: mods.append("shift")
    combo = "-".join(mods + [keyname]) if mods else keyname
    sock.sendall(f"sendkey {combo}\n".encode("utf-8"))
    time.sleep(delay)

def send_monitor_string(sock, text, delay=0.05):
    keymap = {
        'a': 'a', 'b': 'b', 'c': 'c', 'd': 'd', 'e': 'e', 'f': 'f',
        'g': 'g', 'h': 'h', 'i': 'i', 'j': 'j', 'k': 'k', 'l': 'l',
        'm': 'm', 'n': 'n', 'o': 'o', 'p': 'p', 'q': 'q', 'r': 'r',
        's': 's', 't': 't', 'u': 'u', 'v': 'v', 'w': 'w', 'x': 'x',
        'y': 'y', 'z': 'z', '0': '0', '1': '1', '2': '2', '3': '3',
        '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
        ' ': 'spc', '.': 'dot', ',': 'comma', '-': 'minus',
        '\\': 'backslash', ':': 'colon', ';': 'semicolon',
        '\n': 'ret', '\r': 'ret'
    }
    for ch in text:
        if ch.lower() in keymap:
            key = keymap[ch.lower()]
            if ch.isupper():
                send_monitor_key_with_modifiers(sock, key, shift=True)
            else:
                send_monitor_key(sock, key)
        else:
            print(f"Unsupported char: {repr(ch)}")



sock_lock = threading.Lock()
def send_and_receive(sock, command):
    with sock_lock:
        # Flush old output
        try:
            sock.settimeout(0.2)
            while True:
                if not sock.recv(4096):
                    break
        except socket.timeout:
            pass
        except Exception:
            pass

        # Send the command
        sock.sendall((command + "\n").encode("utf-8"))
        sock.settimeout(2.0)

        data = ""
        start = time.time()
        prompt_count = 0

        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                decoded = chunk.decode("utf-8", errors="replace")
                data += decoded
                prompt_count += decoded.count("(qemu)")
                if prompt_count >= 1 and data.strip().endswith("(qemu)"):
                    break
            except socket.timeout:
                break
            if time.time() - start > 5:
                break

        return data.strip()




def save_snapshot(sock):
    print(f"[sending savevm] 'savevm snap1'")
    response = send_and_receive(sock, "savevm snap1")
    print(f"[monitor response]\n{response}\n--- end response ---")

    print(f"[sending info snapshots]")
    snapshot_list = send_and_receive(sock, "info snapshots")
    print(f"[snapshot list response]\n{snapshot_list}\n--- end snapshot list ---")

    if "snap1" in snapshot_list:
        print("[save_snapshot] Snapshot verified via monitor.")
        return True, snapshot_list
    else:
        print("[save_snapshot] Snapshot not found in monitor.")
        return False, snapshot_list



def ocr_word_find(sock, phrase, timeout=10, startx=None, starty=None, stopx=None, stopy=None):
    log_dir = "./compile_logs"
    os.makedirs(log_dir, exist_ok=True)

    start_time = time.time()
    phrase_lower = phrase.lower()
    attempts = 0
    for i in range(timeout):
        attempts += 1
        iter_start = time.time()

        elapsed = int(iter_start - start_time)
        safe_phrase = phrase.replace(" ", "_")
        filename_base = f"{safe_phrase}_{elapsed}"
        screenshot_path = os.path.join(log_dir, filename_base)

        take_screenshot(sock, name=screenshot_path)

        png_path = screenshot_path + ".png"
        txt_path = screenshot_path + ".txt"

        try:
            print('processing screenshot OCR...')
            crop_start = time.time()

            img = Image.open(png_path)
            if None not in (startx, starty, stopx, stopy):
                img = img.crop((startx, starty, stopx, stopy))

            crop_duration = time.time() - crop_start
            print(f"Crop completed in {crop_duration:.2f} seconds")

            ocr_start = time.time()
            text = pytesseract.image_to_string(img)
            ocr_duration = time.time() - ocr_start
            print(f"OCR completed in {ocr_duration:.2f} seconds")

        except Exception as e:
            print(f"OCR failed on {png_path}: {e}")
            text = ""

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        iter_total = time.time() - iter_start
        print(f"Total time this pass: {iter_total:.2f} seconds")

        text_lower = text.lower()
        if phrase_lower in text_lower:
            return True, text, attempts
        if "error" in text_lower:
            return False, text, attempts

        time.sleep(2)

    return False, text, attempts

def ppdcompile(sock):
    log_dir = "./compile_logs"
    os.makedirs(log_dir, exist_ok=True)

    start_time = time.time()
    send_monitor_key(sock, "f3")
    time.sleep(1)
    send_monitor_key(sock, "ret")
    time.sleep(1)
    send_monitor_key(sock, "F")
    time.sleep(1)
    send_monitor_key(sock, "ret")
    time.sleep(1)
    send_monitor_key(sock, "ret")
    time.sleep(1)
    send_monitor_key(sock, "ret")
    time.sleep(1)

    return False

def start_qemu():
    global qemu_process
    qemu_process = subprocess.Popen([
        "qemu-system-i386",
        "-hda", QEMU_IMAGE,
        "-m", "4M",
        "-monitor", f"tcp:127.0.0.1:{MONITOR_PORT},server,nowait",
        "-vga", "std"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def wait_for_monitor(timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return socket.create_connection(("127.0.0.1", MONITOR_PORT), timeout=1)
        except:
            time.sleep(0.2)
    raise RuntimeError("QEMU monitor timeout")




def runbuildtests(name, results, index, total, sock):
    stdout_lines = []
    log = []
    try:
        if name == "Test1 - Copy files to hdd.img":
            print("test1")
            print("Copying files to FAT image...")
            success,output = copy_to_fat_image("sourced", "hdd.img")
            log.append("copied data into hdd.img")
            log.append(output)
            if success:
                print("test1success")
                status = "PASS"
                color = "green"
            else:
                print("test1fail")
                status = "FAIL"
                color = "red"
            results.append((name, status, color, "\n".join(log), ""))
            return
    
        
        if name == "Test2 - Boot to Dos":
            searchphrase = "msdos ready"
            print("test2")
            time.sleep(1)
            success, ocr_text, attempts = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=0, stopx=160, stopy=480)
            log.append("Checked DOS prompt")
            log.append(f"number of ocr attempts: {attempts}")
            log.append(ocr_text)
            print("running snap save")
            
            if success:
                print("test2success")
                status = "PASS"
                color = "green"
                take_screenshot(sock, "reports/test2")
            else:
                print("test2fail")
                status = "FAIL"
                color = "red"
            results.append((name, status, color, "\n".join(log), ""))
            return

        elif name == "Test3 - Start PPD":
            searchphrase = "HI-TECH"
            print("test2")
            send_monitor_string(sock, "cd pacific\n")
            log.append("cd pacific")
            send_monitor_string(sock, "cd bin\n")
            log.append("cd bin")
            send_monitor_string(sock, "ppd\n")
            log.append("ppd")
            time.sleep(3)
            success, ocr_text, attempts = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=315, stopx=640, stopy=480)
            log.append(f"number of ocr attempts: {attempts}")
            log.append(ocr_text)
            take_screenshot(sock, "reports/test3")
            if success:
                print("test3success")
                status = "PASS"
                color = "green"    
            else:
                print("test3fail")
                status = "FAIL"
                color = "red"
            results.append((name, status, color, "\n".join(log), ""))
            return

        elif name == "Test4 - PPD Compile":
            searchphrase = "success"
            print("test4")
            ppdcompile(sock)
            time.sleep(5)
            success, ocr_text, attempts = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=315, stopx=500, stopy=480)
            log.append(ocr_text)
            log.append(f"number of ocr attempts: {attempts}")
            take_screenshot(sock, "reports/test4")
            if success:
                print("test4success")
                status = "PASS"
                color = "green"           
            else:
                print("test4fail")
                status = "FAIL"
                color = "red"
            results.append((name, status, color, "\n".join(log), ""))
            return
        
        elif name == "Test5 - quit to dos prompt":
            searchphrase = "msdos"
            print("test5")
            send_monitor_key(sock, "f", alt=True, delay=0.1)
            time.sleep(0.5)
            send_monitor_key(sock, "q", delay=0.1)
            success, ocr_text, attempts = ocr_word_find(sock, searchphrase, timeout=10, startx=0, starty=0, stopx=160, stopy=480)
            
            log.append('quit to dos prompt:')
            log.append(f"number of ocr attempts: {attempts}")
            log.append(ocr_text)
            
            if success:
                print("test5success")
                status = "PASS"
                color = "green"
            else:
                print("test5fail")
                status = "FAIL"
                color = "red"
            results.append((name, status, color, "\n".join(log), ""))
            return 

        elif name == "Test6 - save snapshot state":
            print("test6")
            success, output = save_snapshot(sock)
            log.append('snapshot state saved')
            log.append(output)
            if success:
                print("test6success")
                status = "PASS"
                color = "green"
            else:
                print("test6fail")
                status = "FAIL"
                color = "red"
            results.append((name, status, color, "\n".join(log), ""))
            return 
        

        elif name == "Test7 - Copy output from hdd img":
            print("test7")
            success, output = copy_from_fat_image("targetd", "hdd.img")
            log.append('copied data from hdd.img')
            log.append(output)
            if success:
                print("test7success")
                status = "PASS"
                color = "green"
            else:
                print("test7fail")
                status = "FAIL"
                color = "red"
            results.append((name, status, color, "\n".join(log), ""))
            return


        print('no status set for prev test - defaulting to FAIL')
        status = "FAIL"
        color = "red"

    except Exception as e:
        print('caught exception for prev test - defaulting to FAIL')
        status = "FAIL"
        color = "red"
        log = ["Exception: {}".format(str(e))]


    results.append((name, status, color, "\n".join(log), ""))


def run_mybuildtests(report_path):
    test_cases = [
        "Test1 - Copy files to hdd.img",
        "Test2 - Boot to Dos",
        "Test3 - Start PPD",
        "Test4 - PPD Compile",
        "Test5 - quit to dos prompt",
        "Test6 - save snapshot state",
        "Test7 - Copy output from hdd img"

    ]
    results = []
    total = len(test_cases)

    with open(PROGRESS_FILE + ".tmp", "w") as pf:
        pf.write(f"0/{total}")
    os.replace(PROGRESS_FILE + ".tmp", PROGRESS_FILE)

    start_qemu()
    qemu_thread = threading.Thread(target=lambda: qemu_process.communicate())
    qemu_thread.daemon = True
    qemu_thread.start()

    sock = wait_for_monitor()
    time.sleep(5)

    for index, name in enumerate(test_cases, start=1):
        with open(PROGRESS_FILE + ".tmp", "w") as pf:
            pf.write(f"{index-1}/{total}")
        os.replace(PROGRESS_FILE + ".tmp", PROGRESS_FILE)

        start_time = time.time()
        runbuildtests(name, results, index, total, sock)
        end_time = time.time()
        duration = end_time - start_time

        if results:
            last = results[-1]
            results[-1] = last + (duration,)

        with open(PROGRESS_FILE + ".tmp", "w") as pf:
            pf.write(f"{index}/{total}")
        os.replace(PROGRESS_FILE + ".tmp", PROGRESS_FILE)

    print(f"Completed {index}/{total}")
    time.sleep(1)

    print("Closing QEMU - test run finished")
    sock.close()
    if qemu_process:
        qemu_process.terminate()
        try:
            qemu_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            qemu_process.kill()

    print('creating html report')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    subdir_path = os.path.join(REPORT_DIR, timestamp)
    os.makedirs(subdir_path, exist_ok=True)
    report_filename = f"test_report_{timestamp}.html"
    report_path = os.path.join(subdir_path, report_filename)

    # move everything from compile_logs to report id subdir
    if os.path.exists(compile_logs_dir):
        for filename in os.listdir(compile_logs_dir):
            src_path = os.path.join(compile_logs_dir, filename)
            dst_path = os.path.join(subdir_path, filename)
            shutil.move(src_path, dst_path)

    # move any .png or .ppm files from REPORT_DIR to the same subdir
    for filename in os.listdir(REPORT_DIR):
        if filename.endswith(".png") or filename.endswith(".ppm"):
            src_path = os.path.join(REPORT_DIR, filename)
            dst_path = os.path.join(subdir_path, filename)
            shutil.move(src_path, dst_path)


    with open(report_path, "w") as f:
        f.write("""<html>
        <head>
        <title>Test Report</title>
        <style>
        body { font-family: sans-serif; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        .green { background-color: #c8f7c5; }
        .red { background-color: #f7c5c5; }
        .gray { background-color: #eeeeee; }
        pre { background-color: #eee; padding: 10px; white-space: pre-wrap; }
        hr { margin: 40px 0; }
        </style>
        </head>
        <body>
        <h1>Test Report</h1>
        <table>
        <tr><th>Test Name</th><th>Result</th><th>Duration (s)</th></tr>
        """)

        for name, status, color, _, _, duration in results:
            f.write(f'<tr><td>{name}</td><td>{duration:.2f}</td><td class="{color}">{status}</td></tr>\n')

        f.write("</table><h2>Detailed Output</h2>\n")

        screenshot_map = {}
        for fname in os.listdir(subdir_path):
            m = re.match(r"test(\d+)\.png$", fname)
            if m:
                screenshot_map[int(m.group(1))] = fname

        for idx, (name, status, color, output, stdout, duration) in enumerate(results):
            img_index = idx + 1 #offset by 1 
            if img_index in screenshot_map:
                img_tag = f'<img src="{screenshot_map[img_index]}" alt="{screenshot_map[img_index]}" style="max-width: 100%; border: 1px solid #ccc;">'
            else:
                img_tag = "<p>No screenshot available.</p>"

            f.write(f"""
    <hr>
    <div style="display: flex; gap: 20px;">
        <div style="flex: 1; background-color: #f0f0f0; padding: 10px;">
            <h3>{name}</h3>
            <p><strong>Duration:</strong> {duration:.2f} seconds</p>
            <pre>{output}\n\nSTDOUT:\n{stdout}</pre>
        </div>
        <div style="flex: 1;">
            <h4>Screenshot</h4>
            {img_tag}
        </div>
    </div>
    """)

        f.write("</body></html>")
        print('wrote to', report_path)

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
