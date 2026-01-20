import subprocess
import os
import time
import threading

APPBASE_DIR = "/testrunnerapp"
TESTSRC_BASEDIR = "/testsrc"



class DosboxInstance:
    def __init__(self, name, config_path=None):
        self.name = name
        self.process = None
        self.pid = None
        self.stdout_lines = []
        self.screenshot_count = 0
        self.config_path = config_path


    def start(self):
        args = ["dosbox"]
        if self.config_path:
            args += ["-conf", self.config_path]
        try:
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.pid = self.process.pid
            print("DOSBOX PID IS: ", self.pid)
            print("start command is", args)
            
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
        # Finds the window ID specifically belonging to this instance's PID
        try:
            cmd = ['xdotool', 'search', '--pid', str(self.pid), '--onlyvisible', '--class', 'dosbox']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        return None

    def wait_for_ready(self, timeout=5):
        start = time.time()
        while time.time() - start < timeout:
            if self.process.poll() is not None: return False
            if self.get_window_id():
                time.sleep(0.5)
                return True
            time.sleep(0.5)
        return False

    def send_command(self, cmd_text, special_keys=None):
        wid = self.get_window_id()
        if wid:
            os.system(f'xdotool windowactivate --sync {wid}')
            if cmd_text:
                os.system(f'xdotool type --window {wid} "{cmd_text}"')
            if special_keys:
                for key in special_keys:
                    os.system(f'xdotool key --window {wid} {key}')


    def take_screenshot(self, test_step=None, filename=None):
        reports_dir = "/testrunnerapp/reports"
        os.makedirs(reports_dir, exist_ok=True)

        step_str = f"-{test_step}" if test_step else ""
        name = filename if filename else f"screenshot-{self.name}{step_str}-{self.screenshot_count}.png"
        path = os.path.join(reports_dir, name) if not filename else os.path.abspath(filename)

        wid = self.get_window_id()
        if not wid:
            return False, "Window ID not found"

        try:
            subprocess.run(['import', '-window', wid, path], check=True)
            self.screenshot_count += 1
            print("DEBUG: SCREENSHOT TAKEN AT: ", path)
            return True, path
        except Exception as e:
            print("FAILED TO TAKE SCREENSHOT", e)
            return False, str(e)


    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()