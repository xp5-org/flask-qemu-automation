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
    log = []

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
            log.append(f"Crop completed in {crop_duration:.2f} seconds")

            ocr_start = time.time()
            text = pytesseract.image_to_string(img)
            ocr_duration = time.time() - ocr_start
            log.append(f"OCR completed in {ocr_duration:.2f} seconds")

        except Exception as e:
            log.append(f"OCR failed on {png_path}: {e}")
            text = ""

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        iter_total = time.time() - iter_start
        log.append(f"Total time this pass: {iter_total:.2f} seconds\n")

        text_lower = text.lower()
        if phrase_lower in text_lower:
            return True, text, attempts, log
        if "error" in text_lower:
            return False, text, attempts, log

        time.sleep(2)

    return False, text, attempts, log

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

import socket
import time
MONITOR_PORT = 55555

def load_snapshot(sock, snapshot_name):
    print(f"[sending loadvm] 'loadvm {snapshot_name}'")
    response = send_and_receive(sock, f"loadvm {snapshot_name}")
    print(f"[monitor response]\n{response}\n--- end response ---")

    if "error" not in response.lower():
        print("[load_snapshot] Snapshot loaded successfully.")
        return True, response
    else:
        print("[load_snapshot] Failed to load snapshot.")
        return False, response





def start_playtest_qemu():
    global qemu_process
    qemu_process = subprocess.Popen([
        "qemu-system-i386",
        "-hda", QEMU_IMAGE,
        "-m", "4M",
        "-monitor", f"tcp:127.0.0.1:{MONITOR_PORT},server,nowait",
        "-vga", "std"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return qemu_process

def start_buildtest_qemu():
    global qemu_process
    qemu_process = subprocess.Popen([
        "qemu-system-i386",
        "-hda", QEMU_IMAGE,
        "-m", "4M",
        "-monitor", f"tcp:127.0.0.1:{MONITOR_PORT},server,nowait",
        "-vga", "std"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return qemu_process


def wait_for_monitor(timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return socket.create_connection(("127.0.0.1", MONITOR_PORT), timeout=1)
        except:
            time.sleep(0.2)
    raise RuntimeError("QEMU monitor timeout")



buildtest_registry = []
playtest_registry = []
def register_playtest(description):
    def decorator(func):
        func.test_description = description
        playtest_registry.append(func)
        return func
    return decorator

def register_buildtest(description):
    def decorator(func):
        func.test_description = description
        buildtest_registry.append(func)
        return func
    return decorator