"""Parent container for this directory.

The __testlist__*.py files here declare themselves children of it by
name, and each contributes one button. Name/archtype/platform live
here so every child agrees on them by construction.
"""

PARENT = {
    "name": "mac_m68k",
    "archtype": "m68k",
    "platform": "mac m68k",
}
