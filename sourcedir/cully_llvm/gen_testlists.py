#!/usr/bin/env python3
"""gen_testlists.py -- chunk stable_pass.txt (see screen_runtime.py) into
__testlist__cully_llvm_batchNN.py files, and known_issues.txt into
__testlist__cully_llvm_knownissuesNN.py files. Same shape and CHUNK_SIZE
reasoning as ../nova_ctestsuite/gen_testlists.py (see that script's own
header for the full explanation of the 21-step ceiling). Every generated
testlist sets "continue_on_failure": True -- these are compilations of
independent tests, not a dependent chain, so one test's failure no longer
skip-cascades the rest of the file (see test_runner.py).

build_failures.txt (tests that never even produced a gen/*.ini -- see
regen_ctestsuite.py) get wired in too, as brokenbuildNN testlists -- one
test_hostbuild step per test, re-invoking nova-cc live (via env vars
pointing at _toolchain/) and asserting it still fails.

Usage: python3 gen_testlists.py
Overwrites every __testlist__cully_llvm_batch*.py,
__testlist__cully_llvm_knownissues*.py, and
__testlist__cully_llvm_brokenbuild*.py in this directory.
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
STABLE_PASS_PATH = os.path.join(HERE, "stable_pass.txt")
KNOWN_ISSUES_PATH = os.path.join(HERE, "known_issues.txt")
BUILD_FAILURES_PATH = os.path.join(HERE, "build_failures.txt")
BUILD_STATUS_PATH = os.path.join(HERE, "BUILD_STATUS.md")
VENDOR_DIR = os.path.join(HERE, "vendor", "single-exec")
SRC_DIR = os.path.join(HERE, "src")

CHUNK_SIZE = 10
KNOWN_ISSUES_CHUNK_SIZE = 8
BROKENBUILD_CHUNK_SIZE = 10

SKIP_LINE_RE = re.compile(
    r"^\s*(int|void)\s*$"                       # bare return-type line
    r"|^\s*(int|void)?\s*main\s*\([^)]*\)\s*\{?\s*$"  # "main()" / "int main(void) {"
    r"|^\s*\{\s*$"                               # lone opening brace
)

# regen_ctestsuite.py's own "## Failing" section, one line per build
# failure: "- **ct00104**: `<the actual error>`". Parsed here so the
# brokenbuild testlists' own step descriptions can say *why* a test is
# expected to keep failing (a genuine compiler/assembler diagnostic)
# instead of just asserting that it will, unhelpfully, with no reason
# given -- a real point of confusion when reading testlist output cold,
# since "expect this to keep failing" alone gives no way to tell a
# still-open backend gap from something that's actually fine to ignore.
BUILD_ERROR_LINE_RE = re.compile(r"^- \*\*(\w+)\*\*: `(.*)`\s*$")


def load_build_errors():
    """base -> its BUILD_STATUS.md error string, or {} if the file is
    missing (still lets brokenbuild generation proceed, just without the
    per-test reason -- BUILD_STATUS.md is regenerated alongside
    build_failures.txt by regen_ctestsuite.py, so the two are normally in
    sync, but don't hard-fail gen_testlists.py over a stale/missing one)."""
    if not os.path.exists(BUILD_STATUS_PATH):
        return {}
    errors = {}
    with open(BUILD_STATUS_PATH) as f:
        for line in f:
            m = BUILD_ERROR_LINE_RE.match(line)
            if m:
                errors[m.group(1)] = m.group(2)
    return errors


def describe(base):
    """smoke01 (hand-written, not from vendor/) has no NNNNN test_id to look
    up -- return a fixed description for it instead of erroring."""
    if base == "smoke01":
        return "hand-written toolchain smoke test (testmain() returning 0)"

    test_id = base[2:]  # "ct00001" -> "00001"
    tags_path = os.path.join(VENDOR_DIR, test_id + ".c.tags")
    tags = ""
    if os.path.exists(tags_path):
        with open(tags_path) as f:
            tags = ", ".join(line.strip() for line in f if line.strip())

    c_path = os.path.join(VENDOR_DIR, test_id + ".c")
    snippet = ""
    if os.path.exists(c_path):
        with open(c_path) as f:
            for line in f:
                stripped = line.strip()
                if not stripped or SKIP_LINE_RE.match(line):
                    continue
                snippet = stripped
                break

    parts = [f"upstream c-testsuite tests/single-exec/{test_id}.c"]
    if tags:
        parts.append(f"[{tags}]")
    if snippet:
        parts.append(f"-- {snippet}"[:80])
    return " ".join(parts)

HEADER_TEMPLATE = '''import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Batch {batch_num} of the c-testsuite (github.com/c-testsuite/c-testsuite)
# single-exec battery run against cullyrichard's nova-llvm-backend (a real
# LLVM/Clang backend for the Data General Nova, extending the sibling
# eclipse-llvm-backend project). See ../cully_llvm/NOTES.txt for the full
# pipeline (vendor/ -> wrap_vendor_tests.py -> src/ -> regen_ctestsuite.py ->
# gen/ -> screen_runtime.py -> stable_pass.txt -> this file, via
# gen_testlists.py -- generated, not hand-maintained; re-run gen_testlists.py
# after re-screening rather than hand-editing this file).
# Only tests that built AND ran to a stable PASS (screen_runtime.py) are
# here -- see BUILD_STATUS.md / RUNTIME_STATUS.md for what got excluded and
# why (compile gaps in this LLVM backend, or a runtime FAIL/HANG).
#
# This is the LLVM-backend counterpart to ../nova_ctestsuite/ (same battery,
# the older PCC-for-Nova pipeline) -- the two are independent, see this
# directory's own NOTES.txt for why finishing one isn't a prerequisite for
# the other.

CONFIG = {{
    "parent": "cully_llvm",
    "projdir": "cully_llvm",
    "instance_name": "nova1",
    "function": "batch_{batch_num:02d}",
    # Each step pair here is one independent test's build+run, not a
    # dependent chain -- one test's failure shouldn't skip the rest of the
    # chunk. See test_runner.py's continue_on_failure handling.
    "continue_on_failure": True,
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {{
        "project": {{
            "_rel": "{{projdir}}",
        }}
    }},
    "steps": [
'''

STEP_TEMPLATE = '''        {{
            "action": "test_startnovasimh",
            "description": "{start_desc}",
            "param": {{
                "name": "nova{n}",
                "script_path": "{{projbasedir}}{{projdir}}/gen/{base}.ini",
                "cwd": "{{projbasedir}}{{projdir}}",
                "boot_rdos": False
            }},
            "subaction": ""
        }},
        {{
            "action": "test_novascreensearch",
            "description": "Check {base} printed \\"{test_id}: PASS\\" to its console",
            "param": {{
                "name": "nova{n}",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            }},
            "subaction": ""
        }},
'''

FOOTER = '''        {
            "action": "test_terminate_all",
            "description": "Tear down every Nova SIMH instance this batch started",
            "param": {},
            "subaction": ""
        },
    ],
}

PATHS = init_test_env(CONFIG, __name__)
'''

KNOWN_ISSUES_HEADER_TEMPLATE = '''import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Known-issues batch {batch_num} of the c-testsuite battery: tests that
# BUILT but did not run cleanly (screen_runtime.py classified them FAIL or
# HANG -- see RUNTIME_STATUS.md for which is which). Wired in as a visible
# to-fix backlog rather than left out, same convention as
# ../nova_ctestsuite/gen_testlists.py.
#
# Every test here is expected to fail/hang on its own -- that's the whole
# point of a known-issues list -- so "continue_on_failure" is on: each
# test_novascreensearch's abort flag no longer cascades into skipping every
# later step in this file, and all of them show a real result on every run
# instead of only the first one reached. (Formerly this skip-cascaded --
# see test_runner.py's continue_on_failure handling for the toggle.)
#
# This is the LLVM-backend counterpart to ../nova_ctestsuite/ -- see this
# directory's own NOTES.txt.

CONFIG = {{
    "parent": "cully_llvm",
    "projdir": "cully_llvm",
    "instance_name": "nova1",
    "function": "known_issues_{batch_num:02d}",
    "continue_on_failure": True,
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {{
        "project": {{
            "_rel": "{{projdir}}",
        }}
    }},
    "steps": [
'''

KNOWN_ISSUE_STEP_TEMPLATE = '''        {{
            "action": "test_startnovasimh",
            "description": "KNOWN ISSUE ({status}) -- {start_desc}",
            "param": {{
                "name": "nova{n}",
                "script_path": "{{projbasedir}}{{projdir}}/gen/{base}.ini",
                "cwd": "{{projbasedir}}{{projdir}}",
                "boot_rdos": False
            }},
            "subaction": ""
        }},
        {{
            "action": "test_novascreensearch",
            "description": "KNOWN ISSUE ({status}): expect this to {expect} -- if it now PASSes, move {base} from known_issues.txt to stable_pass.txt and re-run gen_testlists.py",
            "param": {{
                "name": "nova{n}",
                "successphrase": "PASS",
                "failphrase": "FAIL",
                "timeout": 15,
                "require_success": True
            }},
            "subaction": ""
        }},
'''


def gen_batches():
    with open(STABLE_PASS_PATH) as f:
        tests = [line.strip() for line in f if line.strip()]
    if not tests:
        raise SystemExit(f"no tests in {STABLE_PASS_PATH} -- run screen_runtime.py first")

    for old in glob.glob(os.path.join(HERE, "__testlist__cully_llvm_batch*.py")):
        os.remove(old)

    chunks = [tests[i:i + CHUNK_SIZE] for i in range(0, len(tests), CHUNK_SIZE)]
    for batch_num, chunk in enumerate(chunks, start=1):
        out_path = os.path.join(HERE, f"__testlist__cully_llvm_batch{batch_num:02d}.py")
        text = HEADER_TEMPLATE.format(batch_num=batch_num)
        for n, base in enumerate(chunk, start=1):
            test_id = base[2:] if base.startswith("ct") else base
            start_desc = describe(base).replace('\\', '\\\\').replace('"', '\\"').replace('{', '{{').replace('}', '}}')
            text += STEP_TEMPLATE.format(n=n, base=base, test_id=test_id, start_desc=start_desc)
        text += FOOTER
        with open(out_path, "w") as f:
            f.write(text)
        print(f"wrote {out_path} ({len(chunk)} tests)")

    print(f"{len(tests)} tests across {len(chunks)} batch testlists ({CHUNK_SIZE}/list)")


def gen_known_issues():
    if not os.path.exists(KNOWN_ISSUES_PATH):
        print(f"no {KNOWN_ISSUES_PATH} -- run screen_runtime.py first, skipping known-issues testlists")
        return

    with open(KNOWN_ISSUES_PATH) as f:
        entries = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            base, status = line.split(",")
            entries.append((base, status))
    if not entries:
        print("known_issues.txt is empty -- nothing to wire in (everything is stable PASS)")
        return

    for old in glob.glob(os.path.join(HERE, "__testlist__cully_llvm_knownissues*.py")):
        os.remove(old)

    chunks = [entries[i:i + KNOWN_ISSUES_CHUNK_SIZE]
              for i in range(0, len(entries), KNOWN_ISSUES_CHUNK_SIZE)]
    for batch_num, chunk in enumerate(chunks, start=1):
        out_path = os.path.join(HERE, f"__testlist__cully_llvm_knownissues{batch_num:02d}.py")
        text = KNOWN_ISSUES_HEADER_TEMPLATE.format(batch_num=batch_num)
        for n, (base, status) in enumerate(chunk, start=1):
            test_id = base[2:] if base.startswith("ct") else base
            start_desc = describe(base).replace('\\', '\\\\').replace('"', '\\"').replace('{', '{{').replace('}', '}}')
            expect = "print FAIL" if status == "FAIL" else "hang/timeout"
            text += KNOWN_ISSUE_STEP_TEMPLATE.format(
                n=n, base=base, test_id=test_id, start_desc=start_desc,
                status=status, expect=expect,
            )
        text += FOOTER
        with open(out_path, "w") as f:
            f.write(text)
        print(f"wrote {out_path} ({len(chunk)} tests)")

    print(f"{len(entries)} known issues across {len(chunks)} knownissues testlists "
          f"({KNOWN_ISSUES_CHUNK_SIZE}/list) -- continue_on_failure=True so every test shows a real result")


BROKENBUILD_HEADER_TEMPLATE = '''import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Broken-build batch {batch_num} of the c-testsuite battery: tests that
# never produced a gen/*.ini at all -- nova-cc (clang/llvm-link/opt/llc/
# reorder_asm.py/dgasm) rejected them outright (see BUILD_STATUS.md for
# each one's actual error -- an LLVM backend codegen gap, a missing libc
# function this runtime doesn't implement, or a header it doesn't have).
# There is no SimH .ini to run for these, so each step here re-invokes
# nova-cc LIVE against src/{{base}}.c via test_hostbuild and asserts it
# still fails -- that is the expected, currently-correct state, not a
# testlist bug.
#
# SAME continue_on_failure AS THE knownissues TESTLISTS (see gen_testlists.py's
# own header) -- every step here is expected to fail on its own, so one
# test_hostbuild's abort flag no longer skips the rest of the chunk.
#
# This is the LLVM-backend counterpart to ../nova_ctestsuite/ -- see this
# directory's own NOTES.txt.

CONFIG = {{
    "parent": "cully_llvm",
    "projdir": "cully_llvm",
    "instance_name": "nova1",
    "function": "broken_build_{batch_num:02d}",
    "continue_on_failure": True,
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {{
        "project": {{
            "_rel": "{{projdir}}",
        }}
    }},
    "steps": [
'''

BROKENBUILD_STEP_TEMPLATE = '''        {{
            "action": "test_hostbuild",
            "description": "BROKEN BUILD -- expect this to keep failing to compile/assemble ({error}) -- {start_desc} -- if it now builds, move {base} from build_failures.txt to stable_pass.txt/known_issues.txt (via regen_ctestsuite.py + screen_runtime.py) and re-run gen_testlists.py",
            "param": {{
                "command": "LLVM_BUILD={{projbasedir}}{{projdir}}/_toolchain/llvm-build PATH={{projbasedir}}{{projdir}}/_toolchain/dgasm/build:$PATH {{projbasedir}}{{projdir}}/_toolchain/nova-llvm-backend/nova-toolchain/nova-cc -t nova3 -o /tmp/cully_llvm_brokenbuild_{base}.simh {{projbasedir}}{{projdir}}/src/{base}.c",
                "timeout": 60
            }},
            "subaction": ""
        }},
'''


def gen_broken_builds():
    if not os.path.exists(BUILD_FAILURES_PATH):
        print(f"no {BUILD_FAILURES_PATH} -- run regen_ctestsuite.py first, skipping brokenbuild testlists")
        return

    with open(BUILD_FAILURES_PATH) as f:
        bases = [line.strip() for line in f if line.strip()]
    if not bases:
        print("build_failures.txt is empty -- nothing to wire in (everything builds)")
        return

    for old in glob.glob(os.path.join(HERE, "__testlist__cully_llvm_brokenbuild*.py")):
        os.remove(old)

    build_errors = load_build_errors()

    chunks = [bases[i:i + BROKENBUILD_CHUNK_SIZE] for i in range(0, len(bases), BROKENBUILD_CHUNK_SIZE)]
    for batch_num, chunk in enumerate(chunks, start=1):
        out_path = os.path.join(HERE, f"__testlist__cully_llvm_brokenbuild{batch_num:02d}.py")
        text = BROKENBUILD_HEADER_TEMPLATE.format(batch_num=batch_num)
        for base in chunk:
            start_desc = describe(base).replace('\\', '\\\\').replace('"', '\\"').replace('{', '{{').replace('}', '}}')
            error = build_errors.get(base, "see BUILD_STATUS.md")
            error = error.replace('\\', '\\\\').replace('"', '\\"').replace('{', '{{').replace('}', '}}')
            text += BROKENBUILD_STEP_TEMPLATE.format(
                base=base, start_desc=start_desc, error=error)
        text += FOOTER
        with open(out_path, "w") as f:
            f.write(text)
        print(f"wrote {out_path} ({len(chunk)} tests)")

    print(f"{len(bases)} broken builds across {len(chunks)} brokenbuild testlists "
          f"({BROKENBUILD_CHUNK_SIZE}/list) -- continue_on_failure=True so every test shows a real result")


def main():
    gen_batches()
    gen_known_issues()
    gen_broken_builds()


if __name__ == "__main__":
    main()
