#!/usr/bin/env python3
"""regen_ctestsuite.py -- build every src/*.c (see wrap_vendor_tests.py)
through the nova-llvm-backend toolchain (nova-cc -t nova3), same shape as
../nova_ctestsuite/regen_ctestsuite.py but calling nova-cc instead of
../nova_c/build_c_test.py. A build failure here is EXPECTED and routine at
this suite's scale, so this script does not exit nonzero on one, it just
records it. Writes gen/*.ini for everything that builds (nova-cc's own
gen/*.simh plus the "go 100"/"quit" lines this project's test harness
convention needs -- see NOTES.txt), and BUILD_STATUS.md summarizing the run.

Requires _toolchain/ already built -- see NOTES.txt.

Usage: python3 regen_ctestsuite.py
"""
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLCHAIN_DIR = os.path.join(HERE, "_toolchain")
NOVA_CC = os.path.join(TOOLCHAIN_DIR, "nova-llvm-backend", "nova-toolchain", "nova-cc")
LLVM_BUILD = os.path.join(TOOLCHAIN_DIR, "llvm-build")
DGASM_DIR = os.path.join(TOOLCHAIN_DIR, "dgasm", "build")

SRC_DIR = os.path.join(HERE, "src")
GEN_DIR = os.path.join(HERE, "gen")
STATUS_PATH = os.path.join(HERE, "BUILD_STATUS.md")
BUILD_FAILURES_PATH = os.path.join(HERE, "build_failures.txt")

# nova-cc's own dgasm -f simh output is bare "dep ADDR VAL" lines with no
# start/quit -- entry point is always address 0100 octal, fixed by the
# backend's own "org 0100" (confirmed empirically, see NOTES.txt). Appending
# these two lines turns it into the exact same "d ADDR VAL / go START / quit"
# shape ../nova_c/build_c_test.py already produces for the PCC pipeline, so
# it runs through the SAME test_startnovasimh/test_novascreensearch actions.
INI_FOOTER = "go 100\nquit\n"


class BuildError(RuntimeError):
    pass


def summarize_error(err):
    """Pick the single most informative line out of a (possibly multi-line,
    possibly a whole LLVM crash-dump-with-stack-trace) captured error, for
    BUILD_STATUS.md's one-line-per-failure summary. Prefers an explicit
    "error"/"LLVM ERROR" line (a real clang diagnostic or an llc
    Cannot-select crash) over the generic "N warning(s) generated" line
    clang always prints last, which carries no information about what
    actually went wrong."""
    lines = err.strip().splitlines()
    if not lines:
        return "(no output)"
    for line in lines:
        if "LLVM ERROR" in line or re.search(r"\berror\b", line, re.IGNORECASE):
            return line.strip()
    for line in lines:
        if "Cannot select" in line or "dgasm:" in line:
            return line.strip()
    # dgasm's own "Address out of range" diagnostic doesn't contain the
    # word "error" and isn't prefixed "dgasm:" either, so it fell through
    # every check above straight to the generic "last line" fallback --
    # which is always the *offending instruction's own text* (e.g. "JSR
    # @putchar_SLOT,0"), printed on the line *after* the diagnostic that
    # actually explains what's wrong. Confirmed uninformative on its own:
    # BUILD_STATUS.md and the generated brokenbuild testlists both ended
    # up saying a test would "keep failing to compile/assemble (JSR
    # @putchar_SLOT,0)" with no indication *why* that's a problem.
    for i, line in enumerate(lines):
        if "Address out of range" in line:
            detail = lines[i + 1].strip() if i + 1 < len(lines) else ""
            return f"{line.strip()}{(': ' + detail) if detail else ''}"
    # A raw LLVM assertion crash (not routed through report_fatal_error, so
    # no "LLVM ERROR:"-prefixed line exists) prints a stack dump whose LAST
    # line is often just llvm-symbolizer failing to resolve its own
    # addresses ("Could not open input file: ...") -- noise about the crash
    # handler, not about the actual test. Point at the real crash site
    # instead: the "In function: NAME" line the stack dump always includes.
    if "PLEASE submit a bug report" in err:
        for line in lines:
            if line.strip().startswith("In function:"):
                return f"LLVM backend crash ({line.strip()}) -- see BUILD_STATUS.md regen log for full stack dump"
        return "LLVM backend crash (no 'In function:' line captured) -- see BUILD_STATUS.md regen log for full stack dump"
    return lines[-1].strip()


def build(c_path, out_ini, cpu="nova3", timeout=120):
    env = dict(os.environ)
    env["LLVM_BUILD"] = LLVM_BUILD
    env["PATH"] = DGASM_DIR + ":" + env.get("PATH", "")
    work_simh = out_ini[:-4] + ".simh" if out_ini.endswith(".ini") else out_ini + ".simh"
    r = subprocess.run(
        [NOVA_CC, "-t", cpu, "-o", work_simh, c_path],
        capture_output=True, text=True, env=env, timeout=timeout,
    )
    if r.returncode != 0 or not os.path.exists(work_simh):
        raise BuildError((r.stdout + r.stderr).strip() or f"nova-cc exited {r.returncode} with no output")
    with open(work_simh) as f:
        simh_body = f.read()
    with open(out_ini, "w") as f:
        f.write(simh_body)
        if not simh_body.endswith("\n"):
            f.write("\n")
        f.write(INI_FOOTER)
    os.remove(work_simh)


def main():
    if not os.path.exists(NOVA_CC):
        sys.exit(f"no {NOVA_CC} -- build _toolchain/ first, see NOTES.txt")

    os.makedirs(GEN_DIR, exist_ok=True)
    c_files = sorted(glob.glob(os.path.join(SRC_DIR, "*.c")))
    if not c_files:
        sys.exit(f"no .c files found under {SRC_DIR} -- run wrap_vendor_tests.py first")

    passed = []
    failed = []
    for c_path in c_files:
        base = os.path.splitext(os.path.basename(c_path))[0]
        out_ini = os.path.join(GEN_DIR, base + ".ini")
        try:
            build(c_path, out_ini)
        except (BuildError, subprocess.TimeoutExpired) as e:
            failed.append((base, str(e)))
            if os.path.exists(out_ini):
                os.remove(out_ini)
            continue
        passed.append(base)

    print(f"built {len(passed)} / {len(c_files)}")
    if failed:
        print(f"{len(failed)} failed to build (see {os.path.basename(STATUS_PATH)}):")
        for base, _ in failed:
            print(f"  {base}")

    with open(STATUS_PATH, "w") as f:
        f.write("# cully_llvm build status\n\n")
        f.write(
            "Auto-generated by regen_ctestsuite.py -- do not hand-edit.\n"
            "See NOTES.txt for the pipeline.\n\n"
        )
        f.write(f"**{len(passed)} / {len(c_files)} candidate tests built successfully.**\n\n")
        f.write("## Built successfully (see RUNTIME_STATUS.md for which of these\n"
                "## actually got wired into testlists -- a clean build does not\n"
                "## guarantee a clean run on this backend)\n\n")
        for base in passed:
            f.write(f"- {base}\n")
        f.write("\n## Failing (excluded from testlists)\n\n")
        for base, err in failed:
            f.write(f"- **{base}**: `{summarize_error(err)}`\n")

    print(f"wrote {STATUS_PATH}")

    with open(BUILD_FAILURES_PATH, "w") as f:
        f.write("\n".join(base for base, _ in failed) + ("\n" if failed else ""))
    print(f"wrote {BUILD_FAILURES_PATH}")


if __name__ == "__main__":
    main()
