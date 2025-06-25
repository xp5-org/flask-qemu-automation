import subprocess
import time
import os
import signal


ROM_PATH = "/mydir/qemuflasktestrunner/sc2k.z64"
SCREENSHOT_DIR = "/tmp/mupen_screenshots"
KEY_TO_SEND = 'Return'  # evdev key code name
XWININFO_CMD = ["xwininfo", "-root", "-tree"]

def start_mupen64plus():
    return subprocess.Popen(["mupen64plus", ROM_PATH], env=os.environ)

def find_mupen_window_id():
    try:
        output = subprocess.check_output(XWININFO_CMD).decode()
    except subprocess.CalledProcessError:
        return None

    for line in output.splitlines():
        if '("mupen64plus"' in line.lower() or 'sc2k' in line.lower():
            parts = line.strip().split()
            hexid = parts[0]
            try:
                decid = str(int(hexid, 16))
                print(f"Mupen64Plus window ID (decimal): {decid}")
                return decid
            except ValueError:
                continue
    return None

def send_key(win_id, key):
    try:
        #subprocess.run(['xdotool', 'windowactivate', '--sync', win_id], check=True)
        time.sleep(0.1)
        subprocess.run(['xdotool', 'keydown', '--window', win_id, key], check=True)
        time.sleep(0.05)
        subprocess.run(['xdotool', 'keyup', '--window', win_id, key], check=True)
        print("Key sent")
    except subprocess.CalledProcessError as e:
        print(f"xdotool failed: {e}")


def next_screenshot_path(base_dir):
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    n = 1
    while True:
        path = os.path.join(base_dir, f"screenshot-{n}.png")
        if not os.path.exists(path):
            return path
        n += 1

def screenshot_window(win_id, output_path):
    try:
        subprocess.run(['import', '-window', win_id, output_path], check=True)
        print(f"Screenshot saved to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"import failed: {e}")

def main():
    proc = start_mupen64plus()
    time.sleep(2)  # give mednafen time to open its window

    win_id = find_mupen_window_id()
    if not win_id:
        print("Could not locate Mupen window via xwininfo.")
        proc.terminate()
        return

    for _ in range(30):
        send_key(win_id, KEY_TO_SEND)
        time.sleep(4)
        screenshot_path = next_screenshot_path(SCREENSHOT_DIR)
        screenshot_window(win_id, screenshot_path)
        time.sleep(1)

    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

if __name__ == "__main__":
    main()
