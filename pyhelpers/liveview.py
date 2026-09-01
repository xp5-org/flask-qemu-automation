"""liveview.py — read-only live view of whatever this project has running.

This is the project side of the runner's `/api/v1/instances` surface. The runner
knows nothing about emulators; it loads this module by name and calls the
functions below, so a person or an LLM can *see* a running instance without
starting a test and without touching it.

Two discovery sources, merged:

  * **run**  — the live objects of the current run, read out of the context dict
    the runner publishes (appstate.live_context). These are the real
    QemuInstance / DosboxInstance / NovaSimhInstance objects, so everything they
    can do is available — including state that exists ONLY in this process, such
    as NovaSimhInstance.buf (a pty reader thread's buffer; no /proc scan can
    ever recover it).
  * **scan** — a /proc walk for known emulator binaries, so an instance someone
    launched by hand from a start-qemu-*.sh shows up too. Only externally
    addressable state is reachable this way: an X window, a QMP port.

Because those two sources differ in what they can do, capability is reported
**per instance**, not per project — a Nova under SimH offers `tty` and no
screenshot at all, a scanned QEMU offers `screenshot` but no `tty`. The API just
relays the `capabilities` list; it never assumes an emulator has a screen.

Everything here is read-only apart from the `media` capability (attach/detach
removable media), which mirrors the existing /instances page.

Capability vocabulary (shared with other projects' liveview.py so the API stays
emulator-neutral):
    screenshot  PNG of the current display
    ocr         text read off the current display
    tty         captured console/serial text
    media       list + swap removable media
"""

import os
import re
import subprocess
import sys
import time

_HELPERDIR = os.path.dirname(os.path.abspath(__file__))
if _HELPERDIR not in sys.path:
    sys.path.insert(0, _HELPERDIR)

import displayhelpers
import qemuhelpers


# Live captures land in their own directory: the reports dir is scanned for
# screenshot-<name>-<step>.png to build a test report, and a live capture is not
# part of any test's evidence.
LIVE_DIR = "/testrunnerapp/reports/live"

CAPABILITY_DOC = {
    "screenshot": "GET the current display as a PNG.",
    "ocr":        "GET the text on the current display (tesseract).",
    "tty":        "GET the console/serial text captured so far.",
    "media":      "List removable drive slots, and attach/detach media.",
    "keys":       "POST keystrokes to the guest: a string to type, a single key "
                  "token, or a sequence. Writes to the guest — sending keys "
                  "into a VM that a test is driving will corrupt that test.",
}

# ── Keyboard ─────────────────────────────────────────────────────────────────
# QEMU's `sendkey` takes key NAMES, not characters, so typing a string means
# translating each character to a name plus a shift flag. This map is the
# channel-independent version of QemuInstance.send_keyboardstring's private one,
# extended to cover the punctuation that one silently dropped (it printed
# "Unsupported char" and carried on, so a password or a path with '=' or quotes
# went in mangled).
#
# Names are QEMU's own (see qemu/ui/input-keymap.c). The shifted forms assume a
# US layout in the guest — on another layout the guest decides what shift-3
# means, and there is nothing this side can do about it.

_KEYMAP = {
    ' ': 'spc',  '\n': 'ret', '\r': 'ret', '\t': 'tab',
    '.': 'dot',  ',': 'comma', '-': 'minus', '=': 'equal',
    '/': 'slash', '\\': 'backslash', ';': 'semicolon', "'": 'apostrophe',
    '[': 'bracket_left', ']': 'bracket_right', '`': 'grave_accent',
}
_KEYMAP.update({c: c for c in "abcdefghijklmnopqrstuvwxyz0123456789"})

# character -> the unshifted key you press with shift held
_SHIFTED = {
    ':': 'semicolon', '"': 'apostrophe', '<': 'comma',  '>': 'dot',
    '?': 'slash',     '_': 'minus',      '+': 'equal',  '|': 'backslash',
    '{': 'bracket_left', '}': 'bracket_right', '~': 'grave_accent',
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
}

# Words a caller is likely to use for keys QEMU names differently.
_KEY_SYNONYMS = {
    'enter': 'ret', 'return': 'ret', 'newline': 'ret', 'cr': 'ret',
    'escape': 'esc', 'space': 'spc', 'del': 'delete', 'backspace': 'backspace',
    'pgup': 'pgup', 'pgdn': 'pgdn', 'ins': 'insert',
}


def _char_to_token(ch):
    """One character -> a QEMU sendkey token, or None if it can't be typed."""
    if ch in _SHIFTED:
        return f"shift-{_SHIFTED[ch]}"
    if ch.isupper() and ch.lower() in _KEYMAP:
        return f"shift-{_KEYMAP[ch.lower()]}"
    if ch in _KEYMAP:
        return _KEYMAP[ch]
    return None


def _normalise_token(tok):
    """Normalise one caller-supplied key token, keeping modifier prefixes.

    'ctrl-alt-del' -> 'ctrl-alt-delete', 'Enter' -> 'ret', 'F3' -> 'f3'.
    """
    parts = str(tok).strip().lower().split("-")
    # A trailing empty part means the token ended in '-' (e.g. "shift--"); treat
    # the '-' as the key itself rather than dropping it.
    if parts and parts[-1] == "":
        parts = parts[:-1] + ["minus"]
    if not parts:
        return None
    key = parts[-1]
    key = _KEY_SYNONYMS.get(key, key)
    if key == "del":
        key = "delete"
    return "-".join(parts[:-1] + [key])


def _build_tokens(text=None, key=None, keys=None, enter=False):
    """Turn whatever the caller sent into an ordered list of sendkey tokens.

    Returns (tokens, unsupported_chars).
    """
    tokens, bad = [], []

    if text:
        for ch in str(text):
            tok = _char_to_token(ch)
            if tok is None:
                bad.append(ch)
            else:
                tokens.append(tok)

    if key:
        tok = _normalise_token(key)
        if tok:
            tokens.append(tok)

    if keys:
        if isinstance(keys, str):
            keys = [k for k in re.split(r"[,\s]+", keys.strip()) if k]
        for k in keys:
            tok = _normalise_token(k)
            if tok:
                tokens.append(tok)

    if enter:
        tokens.append("ret")

    return tokens, bad


def _live_dir():
    os.makedirs(LIVE_DIR, exist_ok=True)
    return LIVE_DIR


def _capture_path(iid, ext="png"):
    """One file per instance, overwritten each capture — a live view is the
    current frame, not a growing pile of stills."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", iid)
    return os.path.join(_live_dir(), f"live-{safe}.{ext}")


def _env():
    e = os.environ.copy()
    e["DISPLAY"] = displayhelpers.resolve_display(e.get("DISPLAY"))
    return e


def _xdo(*args):
    try:
        return subprocess.run(["xdotool", *args], capture_output=True,
                              text=True, env=_env()).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _window_for_pid(pid, min_width=200):
    """The emulator's on-screen window, by pid.

    Filtered on width because these emulators also own tiny utility/hidden
    windows (SDL2 and GTK both create them) and grabbing one of those yields a
    useless 1x1 png.
    """
    if not pid:
        return None
    for wid in _xdo("search", "--pid", str(pid)).split():
        geo = dict(l.split("=", 1) for l in
                   _xdo("getwindowgeometry", "--shell", wid).splitlines() if "=" in l)
        try:
            if int(geo.get("WIDTH", 0)) >= min_width:
                return wid
        except ValueError:
            continue
    return None


def _grab_window(pid, path):
    """Screenshot an X window with `import`. Returns (ok, path_or_error)."""
    wid = _window_for_pid(pid)
    if not wid:
        return False, ("no X window for pid %s — the emulator is headless, or is "
                       "not on DISPLAY %s" % (pid, _env().get("DISPLAY")))
    try:
        subprocess.run(["import", "-window", wid, path],
                       check=True, capture_output=True, env=_env())
    except subprocess.CalledProcessError as e:
        return False, f"import failed: {e.stderr.decode('utf-8', 'replace').strip() or e}"
    except OSError as e:
        return False, f"import failed: {e}"
    return (os.path.exists(path) and os.path.getsize(path) > 0), path


def _ocr_png(path):
    """Text of a PNG via tesseract. Returns (ok, text_or_error).

    --psm 6 ("single uniform block of text") and TESSERACT_TESSDATA_ARGS
    (the accurate combined traineddata, vs apt's LSTM-only "fast" default --
    see qemuhelpers.py / Dockerfile) match test_ocrwordsearch's tuning, so
    this live-instance endpoint reads a VGA screen dump as well as a step
    does instead of falling back to tesseract's untuned defaults.
    """
    cmd = ["tesseract", path, "stdout", "--psm", "6"] + qemuhelpers.TESSERACT_TESSDATA_ARGS.split()
    try:
        r = subprocess.run(cmd,
                           capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        return False, f"tesseract failed: {(e.stderr or '').strip() or e}"
    except OSError as e:
        return False, f"tesseract not available: {e}"
    return True, r.stdout


def _pid_of(obj):
    """The OS pid behind an instance object, whatever it calls its handle.

    The classes are independent of each other and name it differently:
    QemuInstance/DosboxInstance keep `.process`, ViceInstance keeps `.proc`,
    NovaSimhInstance keeps a bare `.pid`.
    """
    for attr in ("process", "proc"):
        p = getattr(obj, attr, None)
        if p is not None and getattr(p, "pid", None):
            return p.pid
    pid = getattr(obj, "pid", None)
    return pid if isinstance(pid, int) else None


def _alive(pid):
    """Is this pid a *running* process?

    os.path.isdir("/proc/<pid>") is not enough: when a test terminates its VM,
    the dead child stays a zombie until the runner reaps it, and /proc keeps a
    directory for it — which would leave a torn-down instance listed as live.
    Field 3 of /proc/<pid>/stat is the state letter; 'Z' is that zombie.
    """
    if not pid:
        return False
    try:
        with open(f"/proc/{pid}/stat") as f:
            data = f.read()
        # comm (field 2) can contain spaces and parens, so index past its close
        state = data[data.rindex(")") + 2]
    except (OSError, ValueError, IndexError):
        return False
    return state != "Z"


# ── Per-kind adapters ─────────────────────────────────────────────────────────
#
# An adapter answers three questions about one class of emulator: does a live
# context object belong to me (`matches`), what is running right now that I know
# about (`scan`), and what can be done to one (`caps` + the capability methods).
# Adding an emulator to the live view means adding an adapter here — nothing in
# the runner or the API changes.

class _Adapter:
    kind = "?"

    @classmethod
    def matches(cls, obj):
        return False

    @classmethod
    def scan(cls):
        return []

    @classmethod
    def caps(cls, entry):
        return []

    @classmethod
    def label(cls, entry):
        return entry.get("label") or cls.kind

    @classmethod
    def screenshot(cls, entry, path):
        return False, f"{cls.kind}: no screenshot capability"

    @classmethod
    def tty(cls, entry):
        return False, f"{cls.kind}: no tty capability"


class _QemuAdapter(_Adapter):
    kind = "qemu"

    @classmethod
    def matches(cls, obj):
        return hasattr(obj, "monitor_port") and hasattr(obj, "take_screenshot")

    @classmethod
    def scan(cls):
        out = []
        for inst in qemuhelpers.list_instances():
            out.append({
                "kind": cls.kind,
                "pid": inst["pid"],
                "label": inst.get("label"),
                "source": "scan",
                "detail": inst,
            })
        return out

    @classmethod
    def caps(cls, entry):
        caps = ["screenshot", "ocr"]
        detail = entry.get("detail") or {}
        obj = entry.get("obj")
        # Media swap needs a control channel we can actually get a word in on.
        # A runner-launched VM holds its single HMP socket for the whole run, so
        # only a QMP port (our private channel) makes it swappable from here —
        # list_instances already works this out.
        if detail.get("qmp_port") or detail.get("controllable"):
            caps.append("media")
        if obj is not None and getattr(obj, "serial_path", None):
            caps.append("tty")
        # Typing needs a monitor channel, same as media does.
        if (obj is not None and getattr(obj, "sock", None)) or \
                detail.get("qmp_port") or detail.get("monitor_port"):
            caps.append("keys")
        return caps

    @classmethod
    def send_keys(cls, entry, tokens, delay=0.05):
        """Emit sendkey tokens on whichever monitor channel is usable.

        Same ladder as screenshot and for the same reason: the HMP socket is
        single-client and a run owns it, so the live object goes first (it holds
        that socket), then QMP, then a direct HMP connection.
        """
        detail = entry.get("detail") or {}
        obj = entry.get("obj")

        if obj is not None and getattr(obj, "sock", None):
            for tok in tokens:
                obj.send_key(tok, delay=delay)
            return True, "instance-monitor"

        qmp_port = detail.get("qmp_port")
        if qmp_port:
            for tok in tokens:
                ok, text = qemuhelpers._hmp_via_qmp(qmp_port, f"sendkey {tok}")
                if not ok:
                    return False, f"qmp sendkey {tok}: {text}"
                time.sleep(delay)
            return True, "qmp"

        port = detail.get("monitor_port")
        if port:
            for tok in tokens:
                ok, text = qemuhelpers._hmp(port, f"sendkey {tok}")
                if not ok:
                    return False, f"hmp sendkey {tok}: {text}"
                time.sleep(delay)
            return True, "hmp"

        return False, "no monitor channel to send keys on"

    @classmethod
    def screenshot(cls, entry, path):
        """Capture ladder, safest channel first.

        QMP `screendump` is the only one that is concurrency-safe on a VM the
        runner started: the HMP monitor socket is single-client and the run owns
        it, so talking to it directly would hang. When there is no QMP port, fall
        back to grabbing the GTK window off X, and only then to HMP — which is
        reachable exactly when nothing else holds it.
        """
        detail = entry.get("detail") or {}
        obj = entry.get("obj")
        errors = []

        # A live object owns the monitor socket, so let it do the work.
        if obj is not None and hasattr(obj, "take_screenshot"):
            try:
                ok, res = obj.take_screenshot(test_step="live", filename=path)
                if ok:
                    return True, path
                errors.append(f"instance.take_screenshot: {res}")
            except Exception as e:
                errors.append(f"instance.take_screenshot raised {type(e).__name__}: {e}")

        qmp_port = detail.get("qmp_port")
        if qmp_port:
            ppm = path[:-4] + ".ppm" if path.endswith(".png") else path + ".ppm"
            _unlink(ppm)
            ok, text = qemuhelpers._hmp_via_qmp(qmp_port, f'screendump "{ppm}"')
            if ok and _wait_for_file(ppm):
                conv_ok, conv = _ppm_to_png(ppm, path)
                if conv_ok:
                    return True, path
                errors.append(conv)
            else:
                errors.append(f"qmp screendump: {text}")

        pid = entry.get("pid")
        ok, res = _grab_window(pid, path)
        if ok:
            return True, path
        errors.append(res)

        port = detail.get("monitor_port")
        if port and not detail.get("_hmp_held"):
            ppm = path[:-4] + ".ppm" if path.endswith(".png") else path + ".ppm"
            _unlink(ppm)
            ok, text = qemuhelpers._hmp(port, f'screendump "{ppm}"')
            if ok and _wait_for_file(ppm):
                conv_ok, conv = _ppm_to_png(ppm, path)
                if conv_ok:
                    return True, path
                errors.append(conv)
            else:
                errors.append(f"hmp screendump: {text}")

        return False, "; ".join(errors) or "no capture channel available"

    @classmethod
    def tty(cls, entry):
        obj = entry.get("obj")
        path = getattr(obj, "serial_path", None) if obj is not None else None
        if not path or not os.path.exists(path):
            return False, "no serial capture file for this instance"
        try:
            with open(path, "r", errors="replace") as f:
                return True, f.read()
        except OSError as e:
            return False, f"cannot read {path}: {e}"


class _XWindowAdapter(_Adapter):
    """Emulators driven through an X window: screenshot with `import`, read the
    screen by OCR. DOSBox-X, 86Box and Basilisk II are all this shape."""
    binaries = ()
    attrs = ()

    @classmethod
    def matches(cls, obj):
        return all(hasattr(obj, a) for a in cls.attrs)

    @classmethod
    def scan(cls):
        out = []
        for pid, argv in _iter_procs():
            binary = os.path.basename(argv[0])
            if binary not in cls.binaries:
                continue
            out.append({
                "kind": cls.kind,
                "pid": pid,
                "label": cls.kind,
                "source": "scan",
                "detail": {"binary": binary, "cmdline": " ".join(argv)},
            })
        return out

    @classmethod
    def caps(cls, entry):
        return ["screenshot", "ocr"]

    @classmethod
    def screenshot(cls, entry, path):
        obj = entry.get("obj")
        if obj is not None and hasattr(obj, "take_screenshot"):
            try:
                ok, res = obj.take_screenshot(test_step="live", filename=path)
                if ok:
                    return True, path
            except Exception as e:
                res = f"{type(e).__name__}: {e}"
            # The instance's own grab can fail for reasons that don't stop a
            # plain window grab (a stale cached window id), so still try.
            ok, res2 = _grab_window(entry.get("pid"), path)
            return (True, path) if ok else (False, f"{res}; {res2}")
        return _grab_window(entry.get("pid"), path)


class _DosboxAdapter(_XWindowAdapter):
    kind = "dosbox"
    binaries = ("dosbox-x", "dosbox")
    attrs = ("get_window_id", "read_screen", "conf_path")

    @classmethod
    def matches(cls, obj):
        return (hasattr(obj, "get_window_id") and hasattr(obj, "read_screen")
                and "dosbox" in type(obj).__name__.lower())


class _Box86Adapter(_XWindowAdapter):
    kind = "86box"
    binaries = ("86box", "86Box")

    @classmethod
    def matches(cls, obj):
        return "box86" in type(obj).__name__.lower() or "86box" in type(obj).__name__.lower()


class _BasiliskAdapter(_XWindowAdapter):
    kind = "basilisk"
    binaries = ("BasiliskII",)

    @classmethod
    def matches(cls, obj):
        return "basilisk" in type(obj).__name__.lower()


class _SimhAdapter(_Adapter):
    """SimH (Nova/RDOS) has no display at all — it is a teletype. Its entire
    screen is the pty buffer, which lives in the runner's memory, so a scanned
    instance can be listed but offers nothing to read."""
    kind = "simh"

    @classmethod
    def matches(cls, obj):
        return hasattr(obj, "buf") and hasattr(obj, "master_fd")

    @classmethod
    def scan(cls):
        out = []
        for pid, argv in _iter_procs():
            if "dgnova" not in os.path.basename(argv[0]):
                continue
            out.append({
                "kind": cls.kind,
                "pid": pid,
                "label": "nova",
                "source": "scan",
                "detail": {"binary": os.path.basename(argv[0]),
                           "cmdline": " ".join(argv),
                           "note": "console text is only readable while the run "
                                   "that started it is loaded — the pty buffer "
                                   "lives in the runner process."},
            })
        return out

    @classmethod
    def caps(cls, entry):
        return ["tty"] if entry.get("obj") is not None else []

    @classmethod
    def tty(cls, entry):
        obj = entry.get("obj")
        if obj is None:
            return False, ("this SimH instance was not started by the loaded run, "
                           "so its console buffer is not in this process")
        return True, getattr(obj, "buf", "") or ""


class _HostBuildAdapter(_Adapter):
    """A test_hostbuild subprocess (dispatch_functions.HostBuildInstance) --
    a plain host shell script/build with no display"""
    kind = "hostbuild"

    @classmethod
    def matches(cls, obj):
        return hasattr(obj, "log_path") and hasattr(obj, "process")

    @classmethod
    def caps(cls, entry):
        return ["tty"]

    @classmethod
    def tty(cls, entry):
        obj = entry.get("obj")
        path = getattr(obj, "log_path", None) if obj is not None else None
        if not path or not os.path.exists(path):
            return False, "no output captured yet for this host build"
        try:
            with open(path, "r", errors="replace") as f:
                return True, f.read()
        except OSError as e:
            return False, f"cannot read {path}: {e}"


class _FbMonitorAdapter(_Adapter):
    """A pygame window fed by a live framebuffer sink -- novafbhelpers's
    NovaFbMonitorProcess and verilatorvgahelpers's VerilatorFbMonitorProcess
    are the exact same shape (both spawn MONITOR_PY), just watching a
    different backend's --live sink. Matched by class name, like the
    dosbox/86box/basilisk adapters above, so this file never has to import
    either helper module."""
    classnames = ()

    @classmethod
    def matches(cls, obj):
        return type(obj).__name__ in cls.classnames

    @classmethod
    def caps(cls, entry):
        return ["screenshot"]

    @classmethod
    def screenshot(cls, entry, path):
        return _grab_window(entry.get("pid"), path)


class _NovaFbMonitorAdapter(_FbMonitorAdapter):
    kind = "novafb_monitor"
    classnames = ("NovaFbMonitorProcess",)


class _VerilatorFbMonitorAdapter(_FbMonitorAdapter):
    kind = "verilatorfb_monitor"
    classnames = ("VerilatorFbMonitorProcess",)


class _VerilatorAdapter(_Adapter):
    """The compiled Verilator testbench binary itself (VerilatorLiveInstance)
    -- headless, no window and no console of its own. It only publishes
    frames to a live sink for a _VerilatorFbMonitorAdapter window to read, so
    there is nothing to offer here beyond showing that it is running."""
    kind = "verilator"

    @classmethod
    def matches(cls, obj):
        return type(obj).__name__ == "VerilatorLiveInstance"


ADAPTERS = (_QemuAdapter, _DosboxAdapter, _Box86Adapter, _BasiliskAdapter, _SimhAdapter,
            _HostBuildAdapter, _NovaFbMonitorAdapter, _VerilatorFbMonitorAdapter, _VerilatorAdapter)


# ── Small shared utilities ────────────────────────────────────────────────────

def _iter_procs():
    """(pid, argv) for every readable process."""
    for pid in sorted((p for p in os.listdir("/proc") if p.isdigit()), key=int):
        argv = qemuhelpers._read_cmdline(pid)
        if not argv:
            continue
        yield int(pid), [a.decode("utf-8", "replace") for a in argv]


def _unlink(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _wait_for_file(path, timeout=5.0):
    """screendump returns before QEMU has finished writing the file."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            time.sleep(0.05)          # let the last block land
            return True
        time.sleep(0.05)
    return False


def _ppm_to_png(ppm, png):
    try:
        from PIL import Image
        Image.open(ppm).save(png)
    except Exception as e:
        return False, f"cannot convert {ppm}: {e}"
    finally:
        _unlink(ppm)
    return True, png


# ── Discovery ─────────────────────────────────────────────────────────────────

def _live_entries():
    """Instances of the currently loaded run, taken from the published context.

    Duck-typed on purpose: a start step registers its instance with
    `context[name] = instance` and nothing more, so no project code has to be
    changed for a new emulator to appear here.
    """
    try:
        sys.path.insert(0, "/testrunnerapp")
        from appstate import live_context
    except Exception:
        return []

    entries = []
    seen = set()
    for key, obj in list(live_context.context().items()):
        if key in ("sock", "abort") or obj is None or isinstance(obj, (str, int, float, bool, dict, list)):
            continue
        if id(obj) in seen:
            continue                        # 'qemu1' is an alias of a named instance
        for ad in ADAPTERS:
            try:
                if not ad.matches(obj):
                    continue
            except Exception:
                continue
            pid = _pid_of(obj)
            if not _alive(pid):
                break                       # instance object outlived its process
            seen.add(id(obj))
            entries.append({
                "kind": ad.kind,
                "pid": pid,
                "label": getattr(obj, "name", key),
                "source": "run",
                "context_key": key,
                "obj": obj,
                "detail": {},
            })
            break
    return entries


def _all_entries():
    """Live entries first, then scanned ones that aren't already covered.

    A runner-started VM appears in both sources; the live entry wins because it
    carries the instance object, and so can do strictly more.
    """
    entries = _live_entries()
    live_pids = {e["pid"] for e in entries if e.get("pid")}

    for ad in ADAPTERS:
        try:
            scanned = ad.scan()
        except Exception:
            continue
        for e in scanned:
            if e.get("pid") in live_pids:
                # Keep the scan's detail (monitor/qmp ports) on the live entry —
                # the live QEMU object doesn't know its own QMP port.
                for live in entries:
                    if live.get("pid") == e.get("pid"):
                        live.setdefault("detail", {}).update(e.get("detail") or {})
                continue
            entries.append(e)
    return entries


def _entry_id(entry):
    if entry.get("source") == "run":
        return f"run:{entry.get('context_key') or entry.get('label')}"
    return f"{entry['kind']}:{entry['pid']}"


def _public(entry):
    """The API-visible view of an entry — never leaks the instance object."""
    ad = _adapter_for(entry)
    detail = dict(entry.get("detail") or {})
    detail.pop("cmdline", None)     # long, and echoed under /instances/{id}
    return {
        "id":           _entry_id(entry),
        "kind":         entry["kind"],
        "label":        entry.get("label") or entry["kind"],
        "pid":          entry.get("pid"),
        "source":       entry.get("source"),
        "capabilities": ad.caps(entry) if ad else [],
        "detail":       detail,
    }


def _adapter_for(entry):
    for ad in ADAPTERS:
        if ad.kind == entry.get("kind"):
            return ad
    return None


def _resolve(iid):
    """Accept 'run:<key>', '<kind>:<pid>', or a bare pid."""
    entries = _all_entries()
    for e in entries:
        if _entry_id(e) == iid:
            return e
    if str(iid).isdigit():
        for e in entries:
            if e.get("pid") == int(iid):
                return e
    return None


# ── Public API (what the runner calls) ────────────────────────────────────────

def list_instances():
    """Every instance this project can currently see. Read-only."""
    return [_public(e) for e in _all_entries()]


def get_instance(iid):
    entry = _resolve(iid)
    if not entry:
        return None
    data = _public(entry)
    data["cmdline"] = (entry.get("detail") or {}).get("cmdline")
    return data


def screenshot(iid):
    """Capture the instance's display. Returns (ok, png_path_or_error)."""
    entry = _resolve(iid)
    if not entry:
        return False, f"unknown instance: {iid}"
    ad = _adapter_for(entry)
    if "screenshot" not in ad.caps(entry):
        return False, (f"instance {iid} ({entry['kind']}) has no screenshot "
                       f"capability; it offers: "
                       f"{', '.join(ad.caps(entry)) or 'nothing'}")
    path = _capture_path(_entry_id(entry))
    _unlink(path)
    return ad.screenshot(entry, path)


def ocr(iid, phrase=None):
    """Read the text on the instance's display.

    Returns (ok, {text, image, found?}). `phrase` is an optional convenience
    match — the text is returned either way, so a caller can decide for itself.
    """
    ok, res = screenshot(iid)
    if not ok:
        return False, res
    ok, text = _ocr_png(res)
    if not ok:
        return False, text
    data = {"text": text, "image": res}
    if phrase:
        data["phrase"] = phrase
        data["found"] = phrase.lower() in text.lower()
    return True, data


def tty(iid, tail=None):
    """The console/serial text captured so far. Returns (ok, text_or_error)."""
    entry = _resolve(iid)
    if not entry:
        return False, f"unknown instance: {iid}"
    ad = _adapter_for(entry)
    if "tty" not in ad.caps(entry):
        return False, (f"instance {iid} ({entry['kind']}) has no tty capability; "
                       f"it offers: {', '.join(ad.caps(entry)) or 'nothing'}")
    ok, text = ad.tty(entry)
    if ok and tail:
        try:
            text = "\n".join(text.splitlines()[-int(tail):])
        except (TypeError, ValueError):
            pass
    return ok, text


# ── Keys (write) ─────────────────────────────────────────────────────────────

def send_keys(iid, text=None, key=None, keys=None, enter=False, delay=0.05):
    """Type into a running guest.

    Any combination of:
      text   a string to type character by character ("dir /w")
      key    one key token ("f3", "ret", "ctrl-alt-del")
      keys   a sequence of tokens (list, or a comma/space separated string)
      enter  append a Return after everything else

    A newline is never implied: a caller sends one by asking for it —
    enter=True, key="ret", or a "\\n" inside `text`, whichever reads better.
    Returns (ok, {sent, count, channel, unsupported, run_busy}).
    """
    entry = _resolve(iid)
    if not entry:
        return False, f"unknown instance: {iid}"
    ad = _adapter_for(entry)
    caps = ad.caps(entry)
    if "keys" not in caps:
        return False, (f"instance {iid} ({entry['kind']}) has no keys capability; "
                       f"it offers: {', '.join(caps) or 'nothing'}")

    tokens, bad = _build_tokens(text=text, key=key, keys=keys, enter=enter)
    if not tokens:
        return False, ("nothing to send — provide 'text', 'key', 'keys', "
                       "or enter=true")

    try:
        delay = float(delay)
    except (TypeError, ValueError):
        delay = 0.05

    ok, channel = ad.send_keys(entry, tokens, delay=delay)
    if not ok:
        return False, channel

    result = {
        "sent":     tokens,
        "count":    len(tokens),
        "channel":  channel,
        "instance": _entry_id(entry),
    }
    if bad:
        # Report rather than fail: the rest of the string did go in, and a
        # caller needs to know the guest saw something different from the ask.
        result["unsupported"] = "".join(bad)
        result["warning"] = ("these characters have no sendkey mapping and were "
                             "skipped; the rest was typed")
    busy = _run_busy()
    if busy:
        result["run_busy"] = True
        result["warning_run"] = ("a test is running on this runner — keys sent "
                                 "now compete with the steps driving the guest")
    return True, result


def _run_busy():
    try:
        sys.path.insert(0, "/testrunnerapp")
        from appstate import progress_state
        return (progress_state.step or "Idle") not in ("Idle", "Done")
    except Exception:
        return False


# ── Media (the one non-read-only capability; mirrors /qemuctl) ────────────────

def _media_target(iid):
    entry = _resolve(iid)
    if not entry:
        return None, f"unknown instance: {iid}"
    ad = _adapter_for(entry)
    if "media" not in ad.caps(entry):
        return None, (f"instance {iid} ({entry['kind']}) has no media capability. "
                      "A QEMU the runner started is swappable only if it was "
                      "given a QMP port — its HMP monitor is held by the run.")
    return entry, None


def media_list(iid):
    entry, e = _media_target(iid)
    if e:
        return False, e
    return qemuhelpers.list_blocks(pid=entry["pid"])


def media_attach(iid, device, path, read_only=None):
    entry, e = _media_target(iid)
    if e:
        return False, e
    return qemuhelpers.attach_media(entry["pid"], device, path, read_only=read_only)


def media_detach(iid, device, force=False):
    entry, e = _media_target(iid)
    if e:
        return False, e
    return qemuhelpers.detach_media(entry["pid"], device, force=force)


def media_sources():
    """Images that may be attached — the same two roots the Disk Builder offers."""
    return list(qemuhelpers.ALLOWED_ROOTS)
