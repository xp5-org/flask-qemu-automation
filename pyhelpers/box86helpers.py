import os
import subprocess
import sys
import threading
import time

from displayhelpers import resolve_display
from qemuhelpers import TESSERACT_TESSDATA_ARGS

HELPERDIR = os.path.dirname(os.path.abspath(__file__))
if HELPERDIR not in sys.path:
    sys.path.insert(0, HELPERDIR)
APPBASE_DIR = "/testrunnerapp"
if APPBASE_DIR not in sys.path:
    sys.path.insert(0, APPBASE_DIR)
try:
    import appstate as processreg
except ImportError:
    class processreg:
        register = staticmethod(lambda *a, **k: None)
        unregister = staticmethod(lambda *a, **k: None)

TESTSRC_BASEDIR = "/testsrc"

BOX86_BIN = "86box"


class Box86Instance:
    def __init__(self, name, vm_path, display=None):
        self.name = name
        self.vm_path = vm_path
        self.process = None
        self.pid = None
        self.stdout_lines = []
        self.screenshot_count = 0
        self.xvfb = None
        self.display = display if display == "auto" else resolve_display(display)

    def _env(self):
        env = dict(os.environ)
        env["DISPLAY"] = self.display
        return env

    def _start_xvfb(self):
        for num in range(120, 150):
            if os.path.exists(f"/tmp/.X11-unix/X{num}"):
                continue
            proc = subprocess.Popen(
                ["Xvfb", f":{num}", "-screen", "0", "1024x768x24"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            deadline = time.time() + 10
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                if os.path.exists(f"/tmp/.X11-unix/X{num}"):
                    self.xvfb = proc
                    self.display = f":{num}"
                    return True
                time.sleep(0.1)
            if proc.poll() is None:
                proc.terminate()
        return False

    def start(self):
        if self.display == "auto" and not self._start_xvfb():
            self.stdout_lines.append("Failed to start a private Xvfb.")
            return False

        # -N: don't pop a confirmation dialog on quit, which would wedge stop().
        args = [BOX86_BIN, "-P", self.vm_path, "-N"]
        try:
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=self._env()
            )
            # wrapper execs the emulator, so this pid is 86Box itself.
            self.pid = self.process.pid
            print("86BOX PID IS: ", self.pid, flush=True)
            print("start command is", args, flush=True)
            processreg.register(self.name, self.process, source="86box")

            self.stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
            self.stdout_thread.start()
            return True
        except Exception as e:
            self.stdout_lines.append(str(e))
            return False

    def _read_stdout(self):
        if self.process and self.process.stdout:
            for line in self.process.stdout:
                self.stdout_lines.append(line.strip())

    def get_window_id(self):
        try:
            cmd = ['xdotool', 'search', '--all', '--pid', str(self.pid),
                   '--onlyvisible', '--name', '86Box']
            result = subprocess.run(cmd, capture_output=True, text=True, env=self._env(), timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
        return None

    def wait_for_ready(self, timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            if self.process.poll() is not None:
                return False
            if self.get_window_id():
                time.sleep(0.5)
                return True
            time.sleep(0.5)
        return False

    def is_alive(self):
        """False once the emulator process has exited. Calling poll() reaps it"""
        return self.process is not None and self.process.poll() is None

    def _sleep_while_alive(self, seconds, deadline=None):
        """Sleep up to `seconds` waking early if the process exits.

        status is checked once a second
        
        returns False if it exited.
        """
        end = time.time() + seconds
        if deadline is not None:
            end = min(end, deadline)
        while time.time() < end:
            if not self.is_alive():
                return False
            time.sleep(min(1.0, max(0.0, end - time.time())))
        return self.is_alive()

    def wait_for_post(self, expect, timeout=60, poll=2.0):
        """Poll the screen until `expect` (case-insensitive) shows up in OCR.
        """
        needle = expect.lower()
        deadline = time.time() + timeout
        text = ""
        while time.time() < deadline:
            if not self.is_alive():
                return False, f"86Box exited (window closed?)\n{text}"
            ok, text = self.read_screen()
            if ok and needle in text.lower():
                return True, text
            if not self._sleep_while_alive(float(poll), deadline):
                return False, f"86Box exited (window closed?)\n{text}"
        return False, text

    def send_command(self, cmd_text, special_keys=None, key_delay=40):
        """Type into the 86box VM
        """
        wid = self.get_window_id()
        if not wid:
            return False

        env = self._env()
        try:
            # --sync waits for a WM event that never arrives if
            # the window is closed/destroyed mid-call
            # timeout need to be set here or gets stuck forever
            subprocess.run(['xdotool', 'windowactivate', '--sync', wid],
                           capture_output=True, env=env, timeout=5)
            subprocess.run(['xdotool', 'windowfocus', '--sync', wid],
                           capture_output=True, env=env, timeout=5)

            focused = subprocess.run(['xdotool', 'getwindowfocus'],
                                     capture_output=True, text=True, env=env, timeout=5)
        except subprocess.TimeoutExpired:
            print(f"WARNING: {self.name} window {wid} did not respond to "
                  f"xdotool (closed mid-command?); treating as focus failure")
            return False

        if focused.stdout.strip() != wid:
            print(f"WARNING: {self.name} window {wid} did not take focus "
                  f"(focus is {focused.stdout.strip()}); input would be dropped")
            return False

        try:
            if cmd_text:
                subprocess.run(['xdotool', 'type', '--delay', str(key_delay), cmd_text],
                               env=env, timeout=30)
            if special_keys:
                for key in special_keys:
                    subprocess.run(['xdotool', 'key', key], env=env, timeout=5)
        except subprocess.TimeoutExpired:
            print(f"WARNING: {self.name} window {wid} stopped responding "
                  f"while sending input (closed mid-command?)")
            return False
        return True

    def take_screenshot(self, test_step=None, filename=None):
        if APPBASE_DIR not in sys.path:
            sys.path.insert(0, APPBASE_DIR)
        from appstate import current_reports_dir
        reports_dir = current_reports_dir()

        step_str = f"-{test_step}" if test_step else ""
        name = filename if filename else f"screenshot-{self.name}{step_str}-{self.screenshot_count}.png"
        path = os.path.join(reports_dir, name) if not filename else os.path.abspath(filename)

        wid = self.get_window_id()
        if not wid:
            return False, "Window ID not found"

        try:
            subprocess.run(['import', '-window', wid, path], check=True, env=self._env(), timeout=10)
            self.screenshot_count += 1
            print("DEBUG: SCREENSHOT TAKEN AT: ", path)
            return True, path
        except Exception as e:
            print("FAILED TO TAKE SCREENSHOT", e)
            return False, str(e)

    def read_screen(self):
        """OCR the current screen. Returns (ok, text).
        """
        ok, path = self.take_screenshot(filename=f"/tmp/{self.name}-ocr.png")
        if not ok:
            return False, path
        cmd = ['tesseract', path, 'stdout', '--psm', '6'] + TESSERACT_TESSDATA_ARGS.split()
        try:
            result = subprocess.run(cmd,
                                    capture_output=True, text=True, check=True)
            return True, result.stdout
        except Exception as e:
            return False, str(e)

    def stop(self):
        processreg.unregister(self.name)
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self.xvfb:
            self.xvfb.terminate()
            try:
                self.xvfb.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.xvfb.kill()
                self.xvfb.wait()
            self.xvfb = None


class Box86Conf:
    """Minimal editor for 86box.cfg"""

    def __init__(self, filepath):
        self.filepath = filepath

        with open(filepath, "r", newline="") as f:
            raw = f.read()
        # linux and dos line ending differs need to replace
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
        self.lines = raw.splitlines(keepends=True)

    def set(self, section, key, value):
        out, in_section, done = [], False, False
        for line in self.lines:
            stripped = line.strip()
            if stripped.startswith("["):
                if in_section and not done:
                    out.append(f"{key} = {value}\n")
                    done = True
                in_section = stripped == f"[{section}]"
            elif in_section and stripped.split("=")[0].strip() == key:
                line = f"{key} = {value}\n"
                done = True
            out.append(line)
        if not done:
            if not any(l.strip() == f"[{section}]" for l in out):
                out.append(f"\n[{section}]\n")
            else:
                idx = next(i for i, l in enumerate(out) if l.strip() == f"[{section}]")
                out.insert(idx + 1, f"{key} = {value}\n")
                self.lines = out
                return
            out.append(f"{key} = {value}\n")
        self.lines = out

    def save(self, outpath=None):
        path = outpath if outpath else self.filepath
        print('SAVING NEW 86BOX CONF TO PATH: ', path)
        # newline="" so the \r\n we substitute in is written literally,
        # matching DosboxConf.save's fix for the same issue.
        with open(path, "w", newline="") as f:
            f.write("".join(self.lines).replace("\n", "\r\n"))
