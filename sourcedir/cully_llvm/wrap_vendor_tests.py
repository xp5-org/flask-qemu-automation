#!/usr/bin/env python3
"""wrap_vendor_tests.py 

turn vendor/single-exec/*.c 
verbatim upstream c-testsuite files into a testlist

Upstream convention (c-testsuite's own): each test defines main(), returns 0
on success, and the runner checks the process exit code. 

Usage: python3 wrap_vendor_tests.py
Writes src/*.c (one per vendor/single-exec/NNNNN.c) and prints a summary of
anything skipped.
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.join(HERE, "vendor", "single-exec")
SRC_DIR = os.path.join(HERE, "src")

WRAPPER_TEMPLATE = """
#include <stdio.h>

void main(void)
{{
	printf("{label}: %s\\n", testmain() == 0 ? "PASS" : "FAIL");
}}
"""

MAIN_RE = re.compile(r"\bmain\b")


def wrap_one(c_path, label):
    with open(c_path) as f:
        src = f.read()

    if re.search(r"\bargc\b|\bargv\b", src):
        return None, "uses argc/argv (no argv on bare metal)"
    if MAIN_RE.search(src) is None:
        return None, "no 'main' identifier found"

    wrapped = MAIN_RE.sub("testmain", src)
    wrapped = wrapped.rstrip() + "\n" + WRAPPER_TEMPLATE.format(label=label)
    return wrapped, None


def main():
    os.makedirs(SRC_DIR, exist_ok=True)
    vendor_files = sorted(glob.glob(os.path.join(VENDOR_DIR, "*.c")))
    written = 0
    skipped = []
    for c_path in vendor_files:
        base = os.path.splitext(os.path.basename(c_path))[0]
        wrapped, skip_reason = wrap_one(c_path, base)
        if skip_reason:
            skipped.append((base, skip_reason))
            continue
        out_path = os.path.join(SRC_DIR, f"ct{base}.c")
        with open(out_path, "w") as f:
            f.write(wrapped)
        written += 1

    print(f"wrote {written} wrapped test(s) to {SRC_DIR}")
    if skipped:
        print(f"skipped {len(skipped)}:")
        for base, reason in skipped:
            print(f"  {base}: {reason}")


if __name__ == "__main__":
    main()
