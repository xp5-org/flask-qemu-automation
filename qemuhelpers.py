import subprocess
import socket
import threading
import os
import time
from PIL import Image
import tempfile
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


BASE_DIR = os.path.dirname(os.path.abspath(__file__))




class QemuInstance:
    def __init__(self, name, image_path, monitor_port, floppy_path=None, memory="4M"):
        self.name = name
        self.image_path = os.path.join(BASE_DIR, image_path)
        self.monitor_port = monitor_port
        self.memory = memory
        self.process = None
        self.sock = None
        self.stdout_lines = []
        self.stdout_thread = None

        if floppy_path is not None:
            self.floppy_path = os.path.join(BASE_DIR, floppy_path)
        else:
            self.floppy_path = None    


    def wait_for_ready(self, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            # Check if process is still running
            if self.process.poll() is not None:
                self.stdout_lines.append(f"QEMU process exited unexpectedly with code {self.process.returncode}")
                return False
            try:
                sock = socket.create_connection(("127.0.0.1", self.monitor_port), timeout=1)
                sock.close()
                return True
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(0.3)
        self.stdout_lines.append(f"Timeout waiting for QEMU monitor on port {self.monitor_port}")
        return False
    

    def _read_stdout(self):
        if self.process and self.process.stdout:
            for line in self.process.stdout:
                self.stdout_lines.append(line.strip())

    def start(self):
        print('disk path: ', self.image_path)
        env = os.environ.copy()
        args = [
            "qemu-system-i386",
            "-hda", self.image_path,
            "-m", self.memory,
            "-monitor", f"tcp:127.0.0.1:{self.monitor_port},server,nowait",
            "-vga", "std"
        ]
        if self.floppy_path:
            args.extend(["-fda", self.floppy_path])

        print("Starting QEMU with:", " ".join(args))

        try:
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
        except OSError as e:
            self.stdout_lines = [f"Failed to start QEMU: {e}"]
            return False

        # Wait briefly to see if process exits immediately
        time.sleep(0.1)
        retcode = self.process.poll()

        if retcode is not None:
            # Process exited immediately - capture all output
            output, _ = self.process.communicate(timeout=1)
            self.stdout_lines = [output] if output else ["[no output captured]"]
            return False

        # Process is still running - start thread for async read
        self.stdout_thread = threading.Thread(target=self._read_stdout, name="QEMU-stdout-reader")
        self.stdout_thread.daemon = True
        self.stdout_thread.start()

        # Wait some time for output to appear
        start_time = time.time()
        while time.time() - start_time < 5:
            if self.stdout_lines:
                break
            time.sleep(0.1)

        if not self._wait_for_monitor():
            return False

        try:
            self.sock = socket.create_connection(("127.0.0.1", self.monitor_port), timeout=2)
        except Exception as e:
            self.stdout_lines.append(f"[monitor socket error] {e}")
            return False

        return True


    def take_screenshot(self, name="screenshot"):
        ppm_path_abs = os.path.join(BASE_DIR, name + ".ppm")
        png_path_abs = os.path.join(BASE_DIR, name + ".png")
        name = name.replace(" ", "_")  # sanitize filename


        try:
            time.sleep(0.5)
            if not self.sock:
                return False, "Monitor socket not connected"

            self.sock.sendall(f"screendump {ppm_path_abs}\n".encode("utf-8"))
            time.sleep(0.5)

            start = time.time()
            while not os.path.exists(ppm_path_abs):
                if time.time() - start > 5:
                    return False, f"Timed out waiting for screendump {ppm_path_abs}"
                time.sleep(0.1)

            img = Image.open(ppm_path_abs)
            img.save(png_path_abs)
        except Exception as e:
            return False, f"Failed to take screenshot or convert image: {e}"

        return True, png_path_abs



    def _wait_for_monitor(self, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            try:
                sock = socket.create_connection(("127.0.0.1", self.monitor_port), timeout=1)
                sock.close()
                print(f"[{self.name}] Monitor connected on port {self.monitor_port}")
                return True
            except (ConnectionRefusedError, socket.timeout) as e:
                print(f"[{self.name}] Monitor connect attempt failed: {e}")
                time.sleep(0.3)
        self.stdout_lines.append(f"QEMU monitor timeout on port {self.monitor_port}")
        print(f"[{self.name}] Monitor timeout on port {self.monitor_port}")
        return False


    def send_command(self, cmd):
        with self.lock:
            self.sock.sendall((cmd + "\n").encode("utf-8"))
            data = ""
            while True:
                try:
                    chunk = self.sock.recv(4096).decode("utf-8", errors="replace")
                    data += chunk
                    if "(qemu)" in chunk:
                        break
                except socket.timeout:
                    break
            return data.strip()

    lock = threading.Lock()  # shared per-instance

    def send_key(self, keyname, ctrl=False, alt=False, shift=False, delay=0.1):
        if not self.sock:
            print(f"[{self.name}] No monitor socket connected")
            return

        mods = []
        if ctrl: mods.append("ctrl")
        if alt: mods.append("alt")
        if shift: mods.append("shift")
        combo = "-".join(mods + [keyname]) if mods else keyname
        try:
            self.sock.sendall(f"sendkey {combo}\n".encode("utf-8"))
        except Exception as e:
            print(f"[{self.name}] Failed to send key: {e}")
        time.sleep(delay)


    def send_keyboardstring(self, text, delay=0.05):
        keymap = {
            'a': 'a', 'b': 'b', 'c': 'c', 'd': 'd', 'e': 'e', 'f': 'f',
            'g': 'g', 'h': 'h', 'i': 'i', 'j': 'j', 'k': 'k', 'l': 'l',
            'm': 'm', 'n': 'n', 'o': 'o', 'p': 'p', 'q': 'q', 'r': 'r',
            's': 's', 't': 't', 'u': 'u', 'v': 'v', 'w': 'w', 'x': 'x',
            'y': 'y', 'z': 'z', '0': '0', '1': '1', '2': '2', '3': '3',
            '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
            ' ': 'spc', '.': 'dot', ',': 'comma', '-': 'minus',
            '/': 'slash', '\\': 'backslash', ':': 'semicolon',
            ';': 'semicolon', '\n': 'ret', '\r': 'ret',
            '*': '8'
        }

        shift_required = {
            ':', '_', '+', '{', '}', '|', '<', '>', '"', '?',
            '~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')'
        }

        for ch in text:
            key_char = ch.lower()
            if key_char in keymap:
                key = keymap[key_char]
                shift = ch.isupper() or ch in shift_required
                self.send_key(key, shift=shift, delay=delay)
            else:
                print(f"[{self.name}] Unsupported char for sendkey: {repr(ch)}")


    def send_specialkeys(self, keystr, ctrl=False, alt=False, shift=False, delay=0.1):
    # this is for sending Function keys, return, alt etc
        # Normalize input
        key = keystr.lower()

        # Map common synonyms
        if key == 'enter':
            key = 'ret'
        elif key.startswith('f') and key[1:].isdigit():
            key = key  # 'f1', 'f2', etc., sent as-is
        elif key == 'return':
            key = 'ret'

        # You can add more mappings here if needed.

        # Send the key via existing send_key method, no modifiers by default
        self.send_key(keystr.lower(), ctrl=ctrl, alt=alt, shift=shift, delay=delay)


    def send_command(self, cmd):
        with self.lock:
            try:
                self.sock.settimeout(0.2)
                while True:
                    if not self.sock.recv(4096):
                        break
            except socket.timeout:
                pass
            except Exception:
                pass

            self.sock.sendall((cmd + "\n").encode("utf-8"))
            self.sock.settimeout(2.0)

            data = ""
            start = time.time()
            prompt_count = 0

            while True:
                try:
                    chunk = self.sock.recv(4096)
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
        
    def collect_qemu_logs(self, save_path=None):
        logs = "\n".join(self.stdout_lines)
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(logs)
            except Exception as e:
                return False, f"Failed to write QEMU logs to {save_path}: {e}"
        return True, logs



    def take_screenshots_to_gif(self, interval, count, gif_name="screencap.gif", base_name="frame"):
        framerate = 10
        start_time = time.time()

        try:
            temp_dir = os.path.abspath(f"screens_tmp_{self.name}")
            os.makedirs(temp_dir, exist_ok=True)
            frames = []

            for i in range(count):
                name = f"{base_name}_{i}"
                ppm_path_abs = os.path.join(temp_dir, name + ".ppm")
                png_path = os.path.join(temp_dir, name + ".png")

                self.send_command(f"screendump {ppm_path_abs}")
                time.sleep(0.5)

                wait_start = time.time()
                while not os.path.exists(ppm_path_abs):
                    if time.time() - wait_start > 5:
                        return False, f"[{self.name}] Timed out waiting for screendump {ppm_path_abs}"
                    time.sleep(0.1)

                img = Image.open(ppm_path_abs)
                img.save(png_path)
                frames.append(img.convert("RGB"))

                time.sleep(interval)

            gif_path = os.path.abspath(os.path.join("reports", gif_name))
            frame_duration = max(1, int(1000.0 / framerate))  # ms per frame

            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=frame_duration,
                loop=0
            )

            duration = time.time() - start_time
            gif_playback_time = count / framerate
            speedup = duration / gif_playback_time if gif_playback_time > 0 else 0

            info = (f"[{self.name}] Captured {len(frames)} screenshots in {duration:.2f}s. "
                    f"GIF plays at {framerate} fps for {gif_playback_time:.2f}s "
                    f"(~{speedup:.1f}x speedup). Saved to {gif_path}")

            return True, info

        except Exception as e:
            return False, f"[{self.name}] GIF screenshot capture failed: {e}"




    def attach_floppy(self, path):
        if not os.path.exists(path):
            return False, f"[{self.name}] Floppy image not found: {path}"

        cmd = f"change floppy0 {path}"
        response = self.send_command(cmd)

        if "could not" in response.lower() or "error" in response.lower():
            return False, f"[{self.name}] Failed to attach floppy: {response.strip()}"
        return True, f"[{self.name}] Floppy attached successfully."

    def detatch_floppy(self):
        response = self.send_command("eject floppy0")

        if "ejected" in response.lower() or "floppy0" in response.lower():
            return True, f"[{self.name}] Floppy ejected successfully."
        elif "not found" in response.lower() or "error" in response.lower():
            return False, f"[{self.name}] Failed to eject floppy: {response.strip()}"
        return True, f"[{self.name}] Eject command sent."


    def save_snapshot(self, name="snap1"):
        response = self.send_command(f"savevm {name}")
        if "error" in response.lower():
            return False, f"[{self.name}] Failed to save snapshot: {response}"
        return True, f"[{self.name}] Snapshot '{name}' saved successfully."


    def load_snapshot(self, name="snap1"):
        response = self.send_command(f"loadvm {name}")
        if "error" in response.lower():
            return False, f"[{self.name}] Failed to load snapshot: {response}"
        return True, f"[{self.name}] Snapshot '{name}' loaded successfully."



        


    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.sock.close()
            self.process = None
            self.sock = None







def ocr_word_find(instance, phrase, timeout=10, startx=None, starty=None, stopx=None, stopy=None, errorphrase=None):
    ocrlogdir = os.path.join(BASE_DIR, "compile_logs")
    os.makedirs(ocrlogdir, exist_ok=True)
    log = []

    start_time = time.time()
    phrase_lower = phrase.lower()
    error_lower = errorphrase.lower() if errorphrase else None
    attempts = 0
    text = ""


    for i in range(timeout):
        attempts += 1
        iter_start = time.time()

        elapsed = int(iter_start - start_time)
        safe_phrase = phrase.replace(" ", "_")
        filename_base = f"{safe_phrase}_{elapsed}"
        screenshot_path = os.path.join(ocrlogdir, filename_base)
        png_path = screenshot_path + ".png"
        txt_path = screenshot_path + ".txt"

        ok, msg = instance.take_screenshot(screenshot_path)
        print(f'OCR Screenshot Path: {screenshot_path}')
        if not ok:
            log.append(f"Screenshot failed: {msg}")
            continue

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
        if error_lower and error_lower in text_lower:
            log.append(f"Aborted early due to error phrase: '{errorphrase}' found in OCR text.")
            return False, text, attempts, log

        time.sleep(2)

    return False, text, attempts, log













def make_floppy_image(filename):
    absfloppypath = os.path.join(BASE_DIR, filename)
    size = 1474560  # 1.44 MB
    if not os.path.exists(absfloppypath):
        with open(absfloppypath, "wb") as f:
            f.write(b"\x00" * size)
        return True, "Created new 1.44MB floppy image"
    else:
        actual_size = os.path.getsize(absfloppypath)
        if actual_size != size:
            return False, f"Floppy image exists but is {actual_size} bytes, expected 1474560"
        return True, "Floppy image already exists with correct size"




def convert_raw_to_qcow2(hdd_img_input, qcow2_output):
    hddimg_abspath = os.path.join(BASE_DIR, hdd_img_input)
    qcow2_abspath = os.path.join(BASE_DIR, qcow2_output)
    if not os.path.isfile(hddimg_abspath):
        return False, f"[error] Raw image not found: {hddimg_abspath}"

    if qcow2_output is None:
        qcow2_output = os.path.splitext(qcow2_output)[0] + ".qcow2"
        #forgot what this was for

    try:
        result = subprocess.run(
            ["qemu-img", "convert", "-O", "qcow2", hddimg_abspath, qcow2_abspath],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = result.stdout.decode("utf-8", errors="replace")
        return True, output
    except subprocess.CalledProcessError as e:
        output = e.stdout.decode("utf-8", errors="replace") if e.stdout else ''
        return False, output

    


def copy_to_fat_image(src_dir, hdd_img_path):
    srcdir_abspath = os.path.join(BASE_DIR, src_dir)
    hddimg_abspath = os.path.join(BASE_DIR, hdd_img_path)
    print("src abs path: ", srcdir_abspath)
    print("hdd abs path: ", hddimg_abspath)
    log = []
    mtools_config = f'drive h: file="{hddimg_abspath}" offset=32256\n'
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write(mtools_config)
        config_path = tmp.name

    try:
        try:
            result = subprocess.run(
                f'MTOOLSRC={config_path} mcopy -n -o -s {srcdir_abspath}/* h:/src/',
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