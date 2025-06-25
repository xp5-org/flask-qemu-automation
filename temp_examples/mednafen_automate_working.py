import subprocess
import time
import os
import signal

ROM_PATH = "/mydir/qemuflasktestrunner/simcity.smc"
SCREENSHOT_DIR = "/tmp/mednafen_screenshots"
KEY_TO_SEND = "Return"   # or "z", "x", etc.
XWININFO_CMD = ["xwininfo", "-root", "-tree"]

def start_mednafen():
    return subprocess.Popen(["mednafen", ROM_PATH], env=os.environ)

def find_mednafen_window_id():
    # Run xwininfo and grep for "mednafen"
    try:
        output = subprocess.check_output(XWININFO_CMD).decode()
    except subprocess.CalledProcessError:
        return None

    for line in output.splitlines():
        if '("mednafen"' in line.lower():
            # each line starts with hex id, e.g. "        0x2200006 "
            parts = line.strip().split()
            hexid = parts[0]
            try:
                # convert hex string to decimal string
                decid = str(int(hexid, 16))
                print(f"Mednafen window ID (decimal): {decid}")
                return decid
            except ValueError:
                continue
    return None

def send_key(win_id, key):
    try:
        subprocess.run(['xdotool','key','--window', win_id, key], check=True)
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
        subprocess.run(['import','-window', win_id, output_path], check=True)
        print(f"Screenshot saved to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"import failed: {e}")

def main():
    proc = start_mednafen()
    time.sleep(2)  # give mednafen time to open its window

    win_id = find_mednafen_window_id()
    if not win_id:
        print("Could not locate Mednafen window via xwininfo.")
        proc.terminate()
        return

    for _ in range(3):
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
