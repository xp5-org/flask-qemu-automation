"""Parent container for this directory.

The __testlist__*.py files here declare themselves children of it by
name, and each contributes one button. Name/archtype/platform live
here so every child agrees on them by construction.
"""

import os

_TOOLCHAIN_MARKER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_toolchain", ".bootstrap_complete")

_DESCRIPTION = ("Runs C89 test suite through cullyrichard's nova-llvm-backend "
    "against Nova SIMH. https://github.com/cullyrichard/nova-llvm-backend "
    "and https://github.com/cullyrichard/eclipse-llvm-backend.")

# _toolchain/ is gitignored (~1.4GB, fully reproducible from public sources)
# and never shipped with the checkout. Flag it here rather than letting
# every test just fail on a missing gen/*.ini with no explanation -- this
# gets re-read on every reload_tests(), so the warning clears itself once
# the build_toolchain test finishes.
if not os.path.exists(_TOOLCHAIN_MARKER):
    _DESCRIPTION = ("⚠ _toolchain/ missing -- run the \"build_toolchain\" "
        "test below to provision it (long-running: clones + builds LLVM). ") + _DESCRIPTION

PARENT = {
    "name": "cully_llvm",
    "archtype": "nova",
    "platform": "DGNova nova-llvm-backend (eclipse-clang) baremetal",
    "description": _DESCRIPTION,
    "batch_run_all": True,
    "batch_run_failed": True,
}
