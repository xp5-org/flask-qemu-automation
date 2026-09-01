"""Parent container for this directory.

The __testlist__*.py files here declare themselves children of it by
name, and each contributes one button. Name/archtype/platform live
here so every child agrees on them by construction.
"""

PARENT = {
    "name": "xp5_nova_fpgademo",
    "archtype": "nova",
    "platform": "Data General Nova / FPGA framebuffer mock (device 042), "
                "programs compiled from C via cullyrichard's nova-llvm-backend",
    "description": "Demos for the nova_fb card (../nova_fb/), written as "
        "real C and compiled through ../cully_llvm/'s nova-llvm-backend "
        "toolchain (clang -> llc -mcpu=nova3 -> dgasm), instead of the "
        "hand-assembled octal deposits ../nova_fb/gen_*.py uses.",
}
