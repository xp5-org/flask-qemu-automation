#!/usr/bin/env python3
"""Build rdos_d31_fb.dsk: a stock RDOS disk with FBDRAW.SR loaded onto it.

Mirrors how rdos_d31_fortran.dsk is prepared for the nova_rdos FORTRAN test --
the SOURCE is baked in, and the testlist does the assemble/link/run live so the
toolchain path is exercised rather than assumed.

Run this after changing gen_rdos_src.py:

    python3 gen_rdos_src.py && python3 build_rdos_disk.py

Two non-obvious things about getting a file in over the paper tape reader:
  * XFER stops with "LOAD $PTR, STRIKE ANY KEY." and waits for ONE keystroke
    before it pulls the tape. Miss it and the next command's first character
    gets eaten as that key.
  * DG 8-level tape carries a parity bit in channel 8 and RDOS checks it.
    Plain ASCII (and odd parity) both give "PARITY ERROR: $PTR" plus a corrupt
    file; EVEN parity is what $PTR accepts. gen_rdos_src.py emits that.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, "/testsrc/pyhelpers")
from simhhelpers import NovaSimhInstance

HERE = os.path.dirname(os.path.abspath(__file__))
PRISTINE = "/testsrc/sourcedir/nova_rdos/rdos_d31.dsk"
TARGET = os.path.join(HERE, "rdos_d31_fb.dsk")
SCRIPT = os.path.join(HERE, "demo", "rdos_fbdraw.ini")


def main():
    if not os.path.exists(os.path.join(HERE, "src", "FBDRAW.ptp")):
        print("src/FBDRAW.ptp missing -- run gen_rdos_src.py first")
        return 1

    shutil.copy(PRISTINE, TARGET)          # always start from a stock disk
    inst = NovaSimhInstance("mkdisk", script_path=SCRIPT,
                            binary=os.path.join(HERE, "bin", "dgnova-fb"),
                            cwd=HERE)
    try:
        if not inst.start():
            print("failed to start simulator")
            return 1
        if not inst.boot_to_rdos(timeout=40):
            print("RDOS boot failed:\n%s" % inst.buf[-1500:])
            return 1
        print("booted RDOS")

        inst.buf = ""
        inst.send_command("XFER/A $PTR FBDRAW.SR")
        if not inst.wait_for("STRIKE ANY KEY", timeout=10):
            print("no tape prompt:\n%s" % inst.buf[-500:])
            return 1
        time.sleep(0.5)
        os.write(inst.master_fd, b" ")     # the "any key" that starts the read
        time.sleep(8)
        if "PARITY ERROR" in inst.buf:
            print("tape parity rejected:\n%s" % inst.buf[-500:])
            return 1

        inst.buf = ""
        inst.send_command("LIST FBDRAW.SR")
        time.sleep(3)
        listing = inst.buf.strip().replace("\r", "")
        print("--- %s" % listing[:200])
        if "FBDRAW.SR" not in listing or "DOES NOT EXIST" in listing:
            print("source did not land on the disk")
            return 1
    finally:
        inst.stop()

    print("built %s (%d bytes)" % (TARGET, os.path.getsize(TARGET)))
    print("FBDRAW.SR is on the disk; the testlist does ASM / RLDR / run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
