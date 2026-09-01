"""Parent container for this directory.

The __testlist__*.py files here declare themselves children of it by
name, and each contributes one button. Name/archtype/platform live
here so every child agrees on them by construction.
"""

PARENT = {
    "name": "cully_llvm",
    "archtype": "nova",
    "platform": "DGNova nova-llvm-backend (eclipse-clang) baremetal",
    "description": "Runs C89 test suite through cullyrichard's nova-llvm-backend "
        "against Nova SIMH. https://github.com/cullyrichard/nova-llvm-backend "
        "and https://github.com/cullyrichard/eclipse-llvm-backend.",
    "batch_run_all": True,
    "batch_run_failed": True,
}
