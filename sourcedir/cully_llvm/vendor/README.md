# vendor/single-exec

Verbatim upstream [c-testsuite](https://github.com/c-testsuite/c-testsuite)
`tests/single-exec/*.c` (+ `.expected`/`.tags` siblings), gitignored here
(661 files, ~456K) -- see `/sourcedir/cully_llvm/vendor/single-exec` in the
repo root `.gitignore`.

**Not needed to run any test in this directory.** Every testlist here loads
a committed `gen/*.ini`, never this. This directory is only the *input* to
the regenerate-from-source pipeline (see `../NOTES.txt`'s "Status" section):

```
vendor/single-exec/*.c  --wrap_vendor_tests.py-->  src/*.c
                                                       |  regen_ctestsuite.py
                                                       v
                                                    gen/*.ini   (committed)
```

`gen_testlists.py`'s `describe()` also reads `.tags`/`.c` snippets from here
for testlist descriptions, but again only when regenerating testlists, not
at test-run time.

## Repopulating

Only needed if you're re-deriving `src/*.c` from scratch or auditing it
against upstream -- normal test runs never need this:

```
git clone https://github.com/c-testsuite/c-testsuite /tmp/c-testsuite
cp /tmp/c-testsuite/tests/single-exec/*.c \
   /tmp/c-testsuite/tests/single-exec/*.expected \
   /tmp/c-testsuite/tests/single-exec/*.tags \
   vendor/single-exec/
```

Then re-run `wrap_vendor_tests.py` (and `regen_ctestsuite.py`,
`screen_runtime.py`, `gen_testlists.py` per `../NOTES.txt`) as needed.
