#!/usr/bin/env python3
"""wrap_vendor_tests.py -- turn vendor/single-exec/*.c (verbatim upstream
c-testsuite files, ALL 220 of them -- see NOTES.txt for why this backend's
candidate set is much less narrowed than ../nova_ctestsuite's own 127-of-220)
into src/*.c the nova-llvm-backend (nova-cc) pipeline can build.

Upstream convention (c-testsuite's own): each test defines main(), returns 0
on success, and the runner checks the process exit code. This crt0 has no OS
process/exit code at all -- a bare-metal Nova program just HALTs -- so there
is nothing to read the return value FROM after the fact. Same problem
../nova_ctestsuite/wrap_vendor_tests.py solves, and the same fix: rename
`main` -> `testmain`, then append a fixed wrapper that calls it and prints
PASS/FAIL + a numeric label.

Unlike that script, this one uses printf (not a putchar-per-character loop)
for the wrapper -- this backend has a real printf (rt/eclipse_rt.c), unlike
the PCC-for-Nova pipeline's crt0_template.sr (putchar/getchar/malloc only).
This sidesteps ../nova_ctestsuite's own ct00032 finding entirely (a putchar
loop long enough to add its own literal-pool words shifted an existing
reference out of dga's +-127-word direct-addressing range and silently
corrupted a result) -- one shared printf call site costs the SAME zero-page
budget regardless of the numeric label's value, so there is no equivalent
"labeling the test changes its own answer" risk class here. If
screen_runtime.py ever finds a real instance of it anyway, add a NO_LABEL
skip the same way that script does.

Also unlike that script: candidate selection here does NOT exclude
#include/printf/needs-libc -- this backend has real libc-ish headers
(stdio.h/string.h/stdlib.h/ctype.h, see nova-toolchain/rt/include/) and
clang -cc1 runs its own preprocessor internally (unlike PCC's ccom, which
needed an external cpp pass first and is why the PCC pipeline had to exclude
anything needing more than trivial preprocessing). The only tests excluded
up front are the 3 that take argc/argv (00182/00200/00207 -- no command-line
args on bare metal, confirmed via grep across all 220, see NOTES.txt).
Everything else is attempted; a real incompatibility (an unimplemented libc
function, a header this runtime doesn't have) shows up as a build failure
instead, same as ../nova_ctestsuite's own convention.

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
