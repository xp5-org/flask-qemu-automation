import os
import datetime
from flask import Flask, render_template, send_from_directory, redirect, url_for
from bs4 import BeautifulSoup
import test_runner
import threading

app = Flask(__name__)
build_REPORT_DIR = "reports"
play_REPORT_DIR = "reports"

def get_report_summaries():
    if not os.path.exists(build_REPORT_DIR):
        return []

    summaries = []
    reports = []
    for subdir in sorted(os.listdir(build_REPORT_DIR), reverse=True):
        subdir_path = os.path.join(build_REPORT_DIR, subdir)
        if os.path.isdir(subdir_path):
            for f in os.listdir(subdir_path):
                if f.endswith(".html"):
                    reports.append(os.path.join(subdir, f))

    for report in reports:
        path = os.path.join(build_REPORT_DIR, report)
        try:
            with open(path, "r") as f:
                content = f.read()
                soup = BeautifulSoup(content, "html.parser")
                table = soup.find("table")
                if not table:
                    status = "UNKNOWN"
                    duration_total = ""
                else:
                    status = "PASS"
                    duration_total = 0.0
                    for row in table.find_all("tr")[1:]:
                        cols = row.find_all("td")
                        if len(cols) >= 3:
                            duration_text = cols[1].get_text(strip=True)
                            test_status = cols[2].get_text(strip=True).upper()

                            # Try to extract duration as float in seconds
                            try:
                                duration = float(duration_text.rstrip("s"))
                                duration_total += duration
                            except ValueError:
                                pass

                            if "FAIL" in test_status:
                                status = "FAIL"

                    duration_total = f"{duration_total:.2f}s" if duration_total else ""

                summaries.append((report, duration_total, status))
        except Exception:
            summaries.append((report, "", "ERROR"))

    return summaries



def get_latest_report_summary():
    if not os.path.exists(build_REPORT_DIR):
        return []

    all_reports = []
    for subdir in sorted(os.listdir(build_REPORT_DIR), reverse=True):
        subdir_path = os.path.join(build_REPORT_DIR, subdir)
        if os.path.isdir(subdir_path):
            for f in os.listdir(subdir_path):
                if f.endswith(".html"):
                    all_reports.append((subdir, f))

    if not all_reports:
        return []

    # sort timestamp dir
    all_reports.sort(reverse=True)
    latest_subdir, latest_file = all_reports[0]
    latest_path = os.path.join(build_REPORT_DIR, latest_subdir, latest_file)

    with open(latest_path, "r") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    summary = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) >= 3:
            test_name = cols[0].get_text(strip=True)
            duration_text = cols[1].get_text(strip=True)
            status_text = cols[2].get_text(strip=True).upper()

            if "PASS" in status_text:
                status = "PASS"
            elif "FAIL" in status_text:
                status = "FAIL"
            else:
                status = status_text
            summary.append((test_name, duration_text, status))
    return summary


@app.route("/")
def index():
    if not os.path.exists(build_REPORT_DIR):
        os.makedirs(build_REPORT_DIR)
    summaries = get_report_summaries()
    latest_summary = get_latest_report_summary()
    return render_template("index.html", summaries=summaries, latest_summary=latest_summary)




@app.route("/run_build")
def run_buildtests():
    print("run buildtests called")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.html"
    path = os.path.join(build_REPORT_DIR, filename)

    def run():
        test_runner.run_mybuildtests()
        with open("progress.txt", "w") as pf:
            pf.write("Done")

    with open("progress.txt", "w") as pf:
        pf.write("0/0") 

    threading.Thread(target=run).start()
    return "Started"

@app.route("/run_play")
def run_playtests():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.html"
    path = os.path.join(play_REPORT_DIR, filename)

    def run():
        test_runner.run_myplaytests()
        with open("progress.txt", "w") as pf:
            pf.write("Done")

    with open("progress.txt", "w") as pf:
        pf.write("0/0") 

    threading.Thread(target=run).start()
    return "Started"



@app.route("/progress")
def progress():
    try:
        with open("progress.txt", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "Done"


@app.route("/reports/<path:filepath>")
def view_report(filepath):
    # filepath could be "timestamp/filename.html" or "filename.html"
    full_path = os.path.join(build_REPORT_DIR, filepath)
    if not os.path.isfile(full_path):
        return "File not found", 404
    directory, filename = os.path.split(full_path)
    return send_from_directory(directory, filename)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085, debug=False)