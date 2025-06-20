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
import buildtest
import os
import shutil
import re
import datetime

import helpers
import buildtest  # importing runs the decorators, fills helpers.test_registry

QEMU_IMAGE = "hdd.qcow2"
MONITOR_PORT = 55555
PROGRESS_FILE = "progress.txt"
REPORT_DIR = "reports"
qemu_process = None
compile_logs_dir = "compile_logs"

def run_registered_test(name, registry, sock):
    for test_func in registry:
        if test_func.test_description == name:
            try:
                print(f"Running {name}")
                start_time = time.time()
                success, log_output = test_func(sock)
                duration = time.time() - start_time
                status = "PASS" if success else "FAIL"
                color = "green" if success else "red"
                print(log_output)
            except Exception as e:
                status = "ERROR"
                log_output = str(e)
                color = "gray"
                duration = 0.0
            return (name, status, color, log_output, "", duration)
    return (name, "NOT FOUND", "gray", "No matching test found", "", 0.0)

def run_tests(test_descriptions, registry, sock):
    results = []
    total = len(test_descriptions)
    
    with open(PROGRESS_FILE + ".tmp", "w") as pf:
        pf.write(f"0/{total}")
    os.replace(PROGRESS_FILE + ".tmp", PROGRESS_FILE)
    
    for index, name in enumerate(test_descriptions, start=1):
        with open(PROGRESS_FILE + ".tmp", "w") as pf:
            pf.write(f"{index-1}/{total}")
        os.replace(PROGRESS_FILE + ".tmp", PROGRESS_FILE)
        
        print(f"Running test {index}/{total}: {name}")
        result = run_registered_test(name, registry, sock)
        if result:
            results.append(result)

    print(f"Completed {total}/{total}")
    time.sleep(1)
    
    return results

def run_mybuildtests():
    import datetime
    import buildtest
    
    qemu_process = helpers.start_buildtest_qemu()  # your customized build QEMU start
    qemu_thread = threading.Thread(target=lambda: qemu_process.communicate())
    qemu_thread.daemon = True
    qemu_thread.start()
    
    sock = helpers.wait_for_monitor()
    time.sleep(5)
    
    test_cases = [f.test_description for f in helpers.buildtest_registry]
    results = run_tests(test_cases, helpers.buildtest_registry, sock)
    
    qemu_process.terminate()
    qemu_thread.join(timeout=5)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    subdir_path = os.path.join(REPORT_DIR, timestamp)
    os.makedirs(subdir_path, exist_ok=True)
    report_filename = f"report_{timestamp}.html"
    report_path = os.path.join(subdir_path, report_filename)
    
    generate_report(results, report_path)

def run_myplaytests():
    import datetime
    import playtest
    
    qemu_process = helpers.start_playtest_qemu()  # your customized play QEMU start
    qemu_thread = threading.Thread(target=lambda: qemu_process.communicate())
    qemu_thread.daemon = True
    qemu_thread.start()
    sock = helpers.wait_for_monitor()
    
    
    test_cases = [f.test_description for f in helpers.playtest_registry]
    results = run_tests(test_cases, helpers.playtest_registry, sock)
    
    qemu_process.terminate()
    qemu_thread.join(timeout=5)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    subdir_path = os.path.join(REPORT_DIR, timestamp)
    os.makedirs(subdir_path, exist_ok=True)
    report_filename = f"report_{timestamp}.html"
    report_path = os.path.join(subdir_path, report_filename)
    
    generate_report(results, report_path)



def generate_report(results, report_path):
    subdir_path = os.path.dirname(report_path)
    print(f"Creating directory: '{subdir_path}'")
    if subdir_path and not os.path.exists(subdir_path):
        os.makedirs(subdir_path, exist_ok=True)

    # Move compile logs into report subdir
    if os.path.exists(compile_logs_dir):
        for filename in os.listdir(compile_logs_dir):
            shutil.move(os.path.join(compile_logs_dir, filename), subdir_path)

    # Move images (.png, .ppm) from REPORT_DIR to report subdir
    for filename in os.listdir(REPORT_DIR):
        if filename.endswith(".png") or filename.endswith(".ppm"):
            shutil.move(os.path.join(REPORT_DIR, filename), subdir_path)

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
<tr><th>Test Name</th><th>Duration (s)</th><th>Result</th></tr>
""")

        for name, status, color, _, _, duration in results:
            f.write(f'<tr><td>{name}</td><td>{duration:.2f}</td><td class="{color}">{status}</td></tr>\n')

        f.write("</table><h2>Detailed Output</h2>\n")

        # Map screenshots by test index (expects files like test1.png, test2.png, ...)
        screenshot_map = {}
        for fname in os.listdir(subdir_path):
            m = re.match(r"test(\d+)\.png$", fname)
            if m:
                screenshot_map[int(m.group(1))] = fname

        for idx, (name, status, color, output, stdout, duration) in enumerate(results):
            img_index = idx + 1
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
        <pre>
        OUTPUT:\n{output}\n\n
        STDOUT:\n{stdout}\n\n</pre>
    </div>
    <div style="flex: 1;">
        <h4>Screenshot</h4>
        {img_tag}
    </div>
</div>
""")

        f.write("</body></html>")
    print(f"Wrote report to {report_path}")

            

