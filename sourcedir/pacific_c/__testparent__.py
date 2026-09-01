"""Parent container for this directory.

The __testlist__*.py files here declare themselves children of it by
name, and each contributes one button. Name/archtype/platform live
here so every child agrees on them by construction.
"""

PARENT = {
    "name": "Pacific C Bartest",
    "archtype": "i386",
    "platform": "MSDOS i386",
}
