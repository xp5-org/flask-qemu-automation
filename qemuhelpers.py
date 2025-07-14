import subprocess
import socket
import threading
import os
import time
from PIL import Image
import tempfile

class QemuInstance:
    def __init__(self, name, image_path, monitor_port, floppy_path=None, memory="4M"):
        self.name = name
        self.image_path = image_path
        self.monitor_port = monitor_port
        self.floppy_path = floppy_path
        self.memory = memory
        self.process = None
        self.sock = None
        self.stdout_lines = []
        self.stdout_thread = None

    def start(self):
        args = [
            "qemu-system-i386",
            "-hda", self.image_path,
            "-m", self.memory,
            "-monitor", f"tcp:127.0.0.1:{self.monitor_port},server,nowait",
            "-vga", "std"
        ]
        if self.floppy_path:
            args.extend(["-fda", self.floppy_path])

        self.process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        self.stdout_thread = threading.Thread(target=self._read_stdout)
        self.stdout_thread.daemon = True
        self.stdout_thread.start()

        if not self._wait_for_monitor():
            return False

        self.sock = socket.create_connection(("127.0.0.1", self.monitor_port))
        return True

    def _wait_for_monitor(self, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                sock = socket.create_connection(("127.0.0.1", self.monitor_port), timeout=1)
                sock.close()
                return
            except:
                time.sleep(0.2)
        raise RuntimeError(f"{self.name}: QEMU monitor timeout on port {self.monitor_port}")

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
        mods = []
        if ctrl: mods.append("ctrl")
        if alt: mods.append("alt")
        if shift: mods.append("shift")
        combo = "-".join(mods + [keyname]) if mods else keyname
        self.send_command(f"sendkey {combo}")
        time.sleep(delay)

    def type_string(self, text, delay=0.05):
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


    def take_screenshots_to_gif(self, interval, count, gif_name="screencap.gif", base_name="frame"):
        framerate = 10
        start_time = time.time()

        try:
            temp_dir = os.path.abspath(f"screens_tmp_{self.name}")
            os.makedirs(temp_dir, exist_ok=True)
            frames = []

            for i in range(count):
                name = f"{base_name}_{i}"
                ppm_path = os.path.join(temp_dir, name + ".ppm")
                png_path = os.path.join(temp_dir, name + ".png")

                self.send_command(f"screendump {ppm_path}")
                time.sleep(0.5)

                wait_start = time.time()
                while not os.path.exists(ppm_path):
                    if time.time() - wait_start > 5:
                        return False, f"[{self.name}] Timed out waiting for screendump {ppm_path}"
                    time.sleep(0.1)

                img = Image.open(ppm_path)
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



    def take_screenshot(self, name="screenshot"):
        name = name.replace(" ", "_")  # sanitize filename
        ppm_path = os.path.abspath(name + ".ppm")
        png_path = os.path.abspath(name + ".png")

        self.send_command(f"screendump {ppm_path}")
        time.sleep(0.5)

        start = time.time()
        while not os.path.exists(ppm_path):
            if time.time() - start > 5:
                return False, f"[{self.name}] Timed out waiting for screendump: {ppm_path}"
            time.sleep(0.1)

        try:
            img = Image.open(ppm_path)
            img.save(png_path)
            return True, f"[{self.name}] Screenshot saved to: {png_path}"
        except Exception as e:
            return False, f"[{self.name}] Failed to convert PPM to PNG: {e}"

    def attach_floppy(self, path):
        if not os.path.exists(path):
            return False, f"[{self.name}] Floppy image not found: {path}"

        cmd = f"change floppy0 {path}"
        response = self.send_command(cmd)

        if "could not" in response.lower() or "error" in response.lower():
            return False, f"[{self.name}] Failed to attach floppy: {response.strip()}"
        return True, f"[{self.name}] Floppy attached successfully."

    def eject_floppy(self):
        response = self.send_command("eject floppy0")

        if "ejected" in response.lower() or "floppy0" in response.lower():
            return True, f"[{self.name}] Floppy ejected successfully."
        elif "not found" in response.lower() or "error" in response.lower():
            return False, f"[{self.name}] Failed to eject floppy: {response.strip()}"
        return True, f"[{self.name}] Eject command sent."


    def save_snapshot(self, name="snap1"):
        return self.send_command(f"savevm {name}")

    def load_snapshot(self, name="snap1"):
        response = self.send_command(f"loadvm {name}")
        if "error" in response.lower():
            return False, f"[{self.name}] Failed to load snapshot: {response}"
        return True, f"[{self.name}] Snapshot '{name}' loaded successfully."

    def take_screenshot(self, out_png="screenshot.png"):
        ppm_path = out_png.replace(".png", ".ppm")
        self.send_command(f"screendump {ppm_path}")

        start = time.time()
        while not os.path.exists(ppm_path):
            if time.time() - start > 5:
                return False, f"[{self.name}] Timeout waiting for screendump"
            time.sleep(0.1)

        try:
            img = Image.open(ppm_path)
            img.save(out_png)
            return True, f"[{self.name}] Screenshot saved to {out_png}"
        except Exception as e:
            return False, f"[{self.name}] Failed to save PNG: {e}"

        


    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.sock.close()
            self.process = None
            self.sock = None







def ocr_word_find(sock, phrase, timeout=10, startx=None, starty=None, stopx=None, stopy=None, errorphrase=None):
    log_dir = "./compile_logs"
    os.makedirs(log_dir, exist_ok=True)
    log = []

    start_time = time.time()
    phrase_lower = phrase.lower()
    error_lower = errorphrase.lower() if errorphrase else None
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
        if error_lower and error_lower in text_lower:
            log.append(f"Aborted early due to error phrase: '{errorphrase}' found in OCR text.")
            return False, text, attempts, log

        time.sleep(2)

    return False, text, attempts, log












def make_floppy_image(path):
    size = 1474560  # 1.44 MB
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(b"\x00" * size)
        return True, "Created new 1.44MB floppy image"
    else:
        actual_size = os.path.getsize(path)
        if actual_size != size:
            return False, f"Floppy image exists but is {actual_size} bytes, expected 1474560"
        return True, "Floppy image already exists with correct size"




def convert_raw_to_qcow2(raw_path, qcow2_path):
    if not os.path.isfile(raw_path):
        return False, f"[error] Raw image not found: {raw_path}"

    if qcow2_path is None:
        qcow2_path = os.path.splitext(raw_path)[0] + ".qcow2"

    try:
        result = subprocess.run(
            ["qemu-img", "convert", "-O", "qcow2", raw_path, qcow2_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = result.stdout.decode("utf-8", errors="replace")
        return True, output
    except subprocess.CalledProcessError as e:
        output = e.stdout.decode("utf-8", errors="replace") if e.stdout else ''
        return False, output

    


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