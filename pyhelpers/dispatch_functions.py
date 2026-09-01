import os
import math
import shutil
import sys
import time
import re
import subprocess
import tempfile
import signal
import numpy as np
from PIL import Image

# make app helpers dir visible
TESTSRC_BASEDIR = "/testsrc"                # root dir of git repo qemu-specific test src
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"    # qemuhelpers.py lives here
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from qemuhelpers import (
    copy_to_fat_image,
    copy_from_fat_image,
    ocr_word_find,
    ppdcompile,
    convert_raw_to_qcow2,
    create_overlay_image,
    overlay_backing_file,
    create_fat_disk_image,
    convert_qcow2_to_raw,
    make_disk_image,
    find_button_in_screenshot,
    find_icon_in_screenshot,
)
from mediahelpers import detect_tone, detect_tone_sequence
TEMPLATES_DIR = os.path.join(TESTSRC_BASEDIR, "templates")
from qemuhelpers import QemuInstance
from qemuhelpers import MouseAction
from simhhelpers import NovaSimhInstance, NovaTermProcess, compile_via_nova_llvm
from novafbhelpers import DEFAULT_LIVE_PATH
from novafbhelpers import NovaFbMonitorProcess
from verilatorvgahelpers import (VerilatorLiveInstance,
                                 DEFAULT_LIVE_PATH as VERILATOR_DEFAULT_LIVE_PATH,
                                 VerilatorFbMonitorProcess)
from basiliskhelpers import BasiliskInstance
from dosboxhelpers import DosboxInstance, DosboxConf
from box86helpers import Box86Instance
from apphelpers import init_test_env
from mediahelpers import GifRecorder, active_recorders, stop_all as stop_all_gif_recorders


GUI_INSTANCE_TYPES = (DosboxInstance, Box86Instance)
OCR_INSTANCE_TYPES = (QemuInstance, BasiliskInstance) + GUI_INSTANCE_TYPES


# this is for returning only decorated def's found in this file
def dispatchtest_step(func):
    func._is_teststep = True
    return func


def build_vars(config):
    """Flat {token} lookup map for a CONFIG.

    Merges the top-level config with the leaves of structure.project,
    plus the projbasedir/projdir/src_dir aliases the step templates use.
    """
    project_cfg = config.get("structure", {}).get("project", {})
    vars_map = dict(config)

    # scalar leaves of structure.project (e.g. floppy1_path, config_path)
    for k, v in project_cfg.items():
        if isinstance(v, (str, int)):
            vars_map.setdefault(k, v)

    src_node = project_cfg.get("sourcecode_dir", "")
    if isinstance(src_node, dict):
        src_node = src_node.get("_rel", "")
    vars_map.setdefault("src_dir", src_node)
    vars_map.setdefault("projbasedir", config.get("projbasedir", ""))
    vars_map.setdefault("projdir", config.get("projdir", ""))
    return vars_map


def resolve_path(val, vars_map):
    """Iteratively resolve {tokens} in val against vars_map.
    """
    if not isinstance(val, str):
        return val
    atomic = {k: v for k, v in vars_map.items() if isinstance(v, (str, int))}
    resolved = val
    while "{" in resolved:
        try:
            previous = resolved
            resolved = resolved.format(**atomic)
            if previous == resolved:
                break
        except (KeyError, ValueError, IndexError):
            break
    return resolved


@dispatchtest_step
def test_sendkeyboardinput(inputstring, name="qemu1", takeascreenshot=True, **kwargs):
    log = []
    context = kwargs.get("context")
    instance_name = name or "qemu1"
    instance = context.get(instance_name)
    if not instance:
        return False, f"No QEMU instance '{instance_name}' available in context"

    instance.send_keyboardstring(inputstring)
    log.append(f"{instance_name} Sent string:\n{inputstring}")
    instance.send_keyboardstring("\n")
    time.sleep(0.5)

    _maybe_screenshot(instance, takeascreenshot, log, label=instance_name)

    return True, "\n".join(log)


def _as_bool(v):
    """catch python true/false as strings and return bool type, used with JS & Python exchange"""
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _as_list(v):
    """flatten config value to a list of non-empty strings.
    List-valued step params (prom_env, extra_args, extra_disks) to/from
    testbuilder as a single comma-joined string
    """
    if v is None or v == "":
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [part.strip() for part in str(v).split(",") if part.strip()]


def _maybe_screenshot(instance, flag, log, label=None):
    """Per-step screenshot
    all emulator-driving steps takes `takeascreenshot` so the report picture
    is a checkbox on the step that generated the call
    """
    if not _as_bool(flag):
        return True
    name = label or getattr(instance, "name", "instance")
    if not hasattr(instance, "take_screenshot"):
        log.append(f"{name}: no screenshot capability, skipped")
        return True
    result = instance.take_screenshot()
    # take_screenshot returns (ok, path) on QEMU/Basilisk
    ok = result[0] if isinstance(result, tuple) else bool(result)
    log.append(f"Screenshot for {name} taken" if ok
               else f"Screenshot for {name} failed")
    return bool(ok)


def _reuse_or_take_screenshot(instance, ocr_screenshot_path, flag, log, label=None):
    """Report picture for an OCR step 
    """
    if not _as_bool(flag):
        return True
    name = label or getattr(instance, "name", "instance")
    if not ocr_screenshot_path or not os.path.exists(ocr_screenshot_path):
        return _maybe_screenshot(instance, flag, log, label=label)

    helperdir = "/testrunnerapp"
    if helperdir not in sys.path:
        sys.path.insert(0, helperdir)
    from appstate import progress_state, current_reports_dir
    m = re.match(r'\d+', progress_state.step or "")
    stepnum = m.group(0) if m else "live"

    reports_dir = current_reports_dir()
    dest_name = f"screenshot-{name}-{stepnum}-{instance.screenshot_count}.png"
    dest_path = os.path.join(reports_dir, dest_name)
    try:
        shutil.copy2(ocr_screenshot_path, dest_path)
    except OSError as e:
        log.append(f"{name}: failed to reuse OCR screenshot: {e}")
        return True
    instance.screenshot_count += 1
    log.append(f"Screenshot for {name} reused from OCR capture")
    return True


@dispatchtest_step
def test_sendspecialkey(key=None, name="qemu1", alt=False, ctrl=False, shift=False,
                        delay=0.1, takeascreenshot=False, **kwargs):
    """Send a single special/function key (f1..f12, ret/enter, esc, etc.) with
    optional modifiers, via the monitor. For menu/dialog keyboard driving"""
    context = kwargs.get("context", {})
    instance = context.get(name)
    if not instance:
        return False, f"No QEMU instance '{name}' available in context"
    if not key:
        return False, "no key specified"

    instance.send_specialkeys(key, ctrl=_as_bool(ctrl), alt=_as_bool(alt),
                              shift=_as_bool(shift), delay=float(delay))
    mods = "".join(m for m, f in (("ctrl-", ctrl), ("alt-", alt), ("shift-", shift)) if _as_bool(f))
    log = [f"{name} sent key: {mods}{key}"]
    _maybe_screenshot(instance, takeascreenshot, log, label=name)
    return True, "\n".join(log)


@dispatchtest_step
def test_sendspecialkeys(keys=None, name="qemu1", delay=0.5, takeascreenshot=True, **kwargs):
    """Send a sequence of special or function keys for one logical step.
    `keys` is a list of key tokens sent in
    order, each waiting `delay` seconds after. A token may carry modifiers in
    QEMU sendkey form: "f3", "ret", "alt-f", "ctrl-alt-del". A comma/space
    separated string is also accepted (e.g. "f3, ret, f, ret").

    useful for navigating through dos menus or directories where no OCR is needed
    """
    context = kwargs.get("context", {})
    instance = context.get(name)
    if not instance:
        return False, f"No QEMU instance '{name}' available in context"
    if not keys:
        return False, "no keys specified"
    if isinstance(keys, str):
        keys = [k for k in re.split(r"[,\s]+", keys.strip()) if k]

    delay = float(delay)
    for k in keys:
        instance.send_specialkeys(str(k), delay=delay)
    log = [f"{name} sent key sequence: {' '.join(str(k) for k in keys)}"]
    _maybe_screenshot(instance, takeascreenshot, log, label=name)
    return True, "\n".join(log)


@dispatchtest_step
def test_dirandfilesto_hddimg(sourcecode_dir=None, hdd_img_path=None, dest_dir="src", **kwargs):
    log = []
    context = kwargs.get("context")
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    if sourcecode_dir is None:
        sourcecode_dir = "{projbasedir}{projdir}/{src_dir}"
    if hdd_img_path is None:
        hdd_img_path = "{projbasedir}{projdir}/{hdd1_img}"

    sourcecode_dir = resolve_path(sourcecode_dir, vars_map)
    hdd_img_path = resolve_path(hdd_img_path, vars_map)
    dest_dir = resolve_path(dest_dir, vars_map)

    success, output = copy_to_fat_image(sourcecode_dir, hdd_img_path, dest_dir=dest_dir)
    log.append(output)

    if not success:
        context["abort"] = True
        return False, "\n".join(log)

    return success, "\n".join(log)


@dispatchtest_step
def test_rebuild_srcdisk(srcdisk_path=None, srcdisk_size_mb=None, sourcecode_dir=None, **kwargs):
    """Recreate D: from scratch and repopulate it from sourcecode_dir.

    This is the same recreate-then-copy _prepare_srcdisk does for QEMU's
    hdd2_prepare
    """
    log = []
    context = kwargs.get("context")
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    srcdisk_path = resolve_path(srcdisk_path, vars_map)
    sourcecode_dir = resolve_path(
        sourcecode_dir or "{projbasedir}{projdir}/{src_dir}", vars_map)
    srcdisk_size_mb = resolve_path(
        srcdisk_size_mb or config.get("srcdisk_size_mb") or 512, vars_map)

    if not srcdisk_path:
        return False, "test_rebuild_srcdisk: srcdisk_path is required"

    if not _prepare_srcdisk(srcdisk_path, srcdisk_size_mb, sourcecode_dir, log):
        context["abort"] = True
        return False, "\n".join(log)

    return True, "\n".join(log)


@dispatchtest_step
def test_extract_from_hddimg(hdd_img_path=None, src_dos_dir="src", dest_dir=None, **kwargs):
    """Pull build output back OUT of a disk image the emulator wrote to (e.g.
    the D: source/build disk from test_dirandfilesto_hddimg / _prepare_srcdisk)
    into a host directory, and log each extracted file as an ARTIFACT: so it
    shows up in the report's Build Artifacts table.
    """
    log = []
    context = kwargs.get("context")
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    if hdd_img_path is None:
        hdd_img_path = "{projbasedir}{projdir}/{srcdisk_img}"
    if dest_dir is None:
        dest_dir = "{projbasedir}{projdir}/{src_dir}"

    hdd_img_path = resolve_path(hdd_img_path, vars_map)
    src_dos_dir = resolve_path(src_dos_dir, vars_map)
    dest_dir = resolve_path(dest_dir, vars_map)

    if not hdd_img_path or not os.path.isfile(hdd_img_path):
        return False, f"test_extract_from_hddimg: image not found: {hdd_img_path!r}"

    def _snapshot():
        snap = {}
        if os.path.isdir(dest_dir):
            for root, _dirs, files in os.walk(dest_dir):
                for fn in files:
                    p = os.path.join(root, fn)
                    snap[p] = os.path.getmtime(p)
        return snap

    before = _snapshot()

    success, output = copy_from_fat_image(src_dos_dir, dest_dir, hdd_img_path)
    log.append(output)
    if not success:
        context["abort"] = True
        return False, "\n".join(log)

    after = _snapshot()

    new_or_changed = sorted(p for p, mtime in after.items()
                             if p not in before or mtime != before[p])
    if not new_or_changed:
        log.append(f"no new/changed files found under {dest_dir}")
    for p in new_or_changed:
        log.append(f"ARTIFACT: {p}")

    return True, "\n".join(log)


def _prepare_hdd_overlay(hdd1_template, hdd1_overlay_path, log, persist=False):
    """C: — a COW overlay on a shared read-only template.

    default: the overlay is rebuilt from scratch, so a run always boots the
    pristine template and never inherits the last run's writes
    
    persist=True (config "hdd1_persist") the existing
    overlay writes are retained. anything installed into C: survives across run.

    a persisted overlay is only valid on top of the template it was created from, so
    its recorded backing file is checked first; a mismatch (the testlist switched
    hdd1_template) rebuilds rather than silently booting the wrong chain.

    hdd1_template is a bare filename resolved against /testsrc/templates
    a test selects its boot image by name.
    Returns True/False; appends detail to `log`.
    """
    if os.sep not in str(hdd1_template):
        hdd1_template = os.path.join(TEMPLATES_DIR, hdd1_template)
    hdd1_template = os.path.abspath(hdd1_template)

    if persist and os.path.isfile(hdd1_overlay_path):
        backing = overlay_backing_file(hdd1_overlay_path)
        if backing == hdd1_template:
            log.append(f"C: keeping existing overlay (hdd1_persist): "
                       f"{hdd1_overlay_path} on {os.path.basename(hdd1_template)} "
                       f"— writes from previous runs are preserved")
            return True
        log.append(f"C: overlay {hdd1_overlay_path} is backed by {backing!r}, not the "
                   f"requested {hdd1_template!r} — rebuilding it despite hdd1_persist")

    success, output = create_overlay_image(hdd1_template, hdd1_overlay_path, overwrite=True)
    log.append(output)
    return success


def _prepare_srcdisk(srcdisk_path, srcdisk_size_mb, sourcecode_dir, log,
                     srcdisk_label="SRC"):
    """D: — a raw FAT16 data disk carrying source in and build output out.

    srcdisk is recreated on every start. 

    raw format design decision: mtools only uses raw, this is the
    one disk the host can read/write directly, with no conversion on either
    side. 
    
    Returns True/False; appends detail to `log`.
    """
    success, output = create_fat_disk_image(
        srcdisk_path, srcdisk_size_mb, label=srcdisk_label,
        make_src_dir=True, overwrite=True, system=False,
    )
    log.append(output)
    if not success:
        return False

    if sourcecode_dir and os.path.isdir(sourcecode_dir):
        success, output = copy_to_fat_image(sourcecode_dir, srcdisk_path, dest_dir="src")
        log.append(output)
        return success

    log.append(f"no sourcecode_dir to copy (looked for {sourcecode_dir!r})")
    return True


@dispatchtest_step
def test_convert_hddimg_to_hddqcow(hdd_img_path=None, hdd_qcow_path=None, **kwargs):
    log = []
    context = kwargs.get("context")
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    hdd_img_path = resolve_path(hdd_img_path, vars_map)
    hdd_qcow_path = resolve_path(hdd_qcow_path, vars_map)

    success, output = convert_raw_to_qcow2(hdd_img_path, hdd_qcow_path)
    log.append(output)

    if not success:
        context["abort"] = True
        return False, "\n".join(log)

    return success, "\n".join(log)


def _ocr_instances(context, name=None):
    """function wrapper helper
    return the name of an instance (qemuinstance, dosbox instance) targeted for OCR

    Returns (list, error).
    """
    if name:
        inst = context.get(name)
        if not isinstance(inst, OCR_INSTANCE_TYPES):
            return None, f"No OCR-capable instance '{name}' available in context"
        return [(name, inst)], None

    found = []
    for key, inst in context.items():
        if isinstance(inst, OCR_INSTANCE_TYPES) and not any(inst is f for _, f in found):
            found.append((key, inst))
    return found, None


def _ocr_schedule(numberofattempts, attemptdelay, timeout, poll):
    """define ocr scheduling as qty of attempts to try, 
       and amount of delay between those attempts
       total timeout for the entire step
    """
    if timeout not in (None, ""):
        delay = float(poll) if poll not in (None, "") else 2.0
        delay = max(delay, 0.1)
        attempts = int(math.ceil(float(timeout) / delay))
        return max(1, attempts), delay

    attempts = int(numberofattempts) if numberofattempts not in (None, "") else 1
    delay = float(attemptdelay) if attemptdelay not in (None, "") else 3.0
    return max(1, attempts), delay


@dispatchtest_step
def test_ocrwordsearch(successphrase=None, failphrase=None,
                       numberofattempts=None, attemptdelay=None,
                       timeout=None, poll=None, name=None,
                       startx=None, starty=None, stopx=None, stopy=None,
                       require_success=False, takeascreenshot=True, **kwargs):
    """poll an instances screen with OCR until successphrase appears.

    The single screen-wait for every backend that has a screen
    `name` targets one instance

    startx/starty/stopx/stopy crop the screenshot before OCR, to accelerate it

    require_success makes a missing successphrase FAIL the step and abort the
    run instead of only reporting it
    
    A failphrase seen on screen always fails

    CONFIG["ocr_scale"]  upscales every screenshot either 2 or 4
    """
    context = kwargs.get("context", {})
    require_success = _as_bool(require_success)
    attempts_n, delay = _ocr_schedule(numberofattempts, attemptdelay, timeout, poll)

    targets, err = _ocr_instances(context, name)
    if err:
        return False, err

    log = []
    abort = False
    ocr_ok = True
    saw_failphrase = False

    for label, instance in targets:
        success, screentext, attempts, ocrlog, ocr_screenshot_path = ocr_word_find(
            instance,
            successphrase,
            numberofattempts=attempts_n,
            attemptdelay=delay,
            startx=startx,
            starty=starty,
            stopx=stopx,
            stopy=stopy,
            errorphrase=failphrase
        )
        ocr_ok = ocr_ok and bool(success)
        if failphrase and failphrase.lower() in (screentext or "").lower():
            saw_failphrase = True

        log.append(f"{label} screentext:\n{screentext}")
        log.append(f"{label} ocrlog:\n{ocrlog}")

        if not _reuse_or_take_screenshot(instance, ocr_screenshot_path, takeascreenshot, log, label=label) and not success:
            abort = True

    if abort:
        context["abort"] = True
        for label, instance in targets:
            log.append(f"Stopping {label}")
            instance.stop()
        return False, "\n".join(log)

    if saw_failphrase:
        context["abort"] = True
        log.append(f"fail phrase '{failphrase}' is on screen — failing step")
        return False, "\n".join(log)

    if not targets:
        log.append("No OCR-capable instances found in context")
        if require_success:
            context["abort"] = True
            return False, "\n".join(log)
        return True, "\n".join(log)

    if require_success and not ocr_ok:
        context["abort"] = True
        log.append(f"OCR did not find success phrase '{successphrase}' "
                   f"(require_success) — failing step")
        return False, "\n".join(log)

    return True, "\n".join(log)


@dispatchtest_step
def test_startqemu(name=None, cpuarch=None, port=55555, floppy1_path=None,
                   floppy1_size=None, floppy2_path=None, floppy2_size=None,
                   hdd1_qcow_path=None, hdd2_path=None,
                   cdrom_path=None, cdrom2_path=None, hdd1_template=None,
                   hdd1_persist=None, srcdisk_size_mb=None,
                   sourcecode_dir=None, memory="4M", vnc_port=None,
                   sound_device=None, audio_backend="wav", audio_out_path=None,
                   pa_out_name=None, pa_in_name=None, pa_server=None,
                   serial_path=None, hdd2_prepare=True,
                   machine=None, cpu=None, vga=None, net_device=None,
                   mac_address=None, bios_path=None, boot_order=None,
                   prom_env=None, extra_args=None, extra_disks=None,
                   qemu_binary=None, takeascreenshot=False, **kwargs):
    log = []
    context = kwargs.get("context")
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    sound_device = resolve_path(sound_device or config.get("sound_device"), vars_map) or None
    audio_backend = resolve_path(audio_backend or config.get("audio_backend") or "wav", vars_map)
    audio_out_path = resolve_path(audio_out_path or config.get("audio_out_path"), vars_map) or None
    pa_out_name = resolve_path(pa_out_name or config.get("pa_out_name"), vars_map) or None
    pa_in_name = resolve_path(pa_in_name or config.get("pa_in_name"), vars_map) or None
    pa_server = resolve_path(pa_server or config.get("pa_server"), vars_map) or None
    serial_path = resolve_path(serial_path or config.get("serial_path"), vars_map) or None
    floppy1_size = resolve_path(floppy1_size or config.get("floppy1_size"), vars_map)
    floppy1_path = resolve_path(floppy1_path or vars_map.get("floppy1_path", ""), vars_map)
    hdd1_qcow_path = resolve_path(hdd1_qcow_path, vars_map)
    hdd2_path = resolve_path(hdd2_path, vars_map) or None
    cdrom_path = resolve_path(cdrom_path, vars_map) or None
    floppy2_path = resolve_path(floppy2_path or config.get("floppy2_path"), vars_map) or None
    floppy2_size = resolve_path(floppy2_size or config.get("floppy2_size"), vars_map)
    cdrom2_path = resolve_path(cdrom2_path or config.get("cdrom2_path"), vars_map) or None
    hdd1_template = resolve_path(hdd1_template or config.get("hdd1_template"), vars_map)
    hdd1_persist = resolve_path(hdd1_persist if hdd1_persist is not None
                                else config.get("hdd1_persist", False), vars_map)
    hdd1_persist = _as_bool(hdd1_persist)
    if hdd1_template and hdd1_qcow_path:
        if not _prepare_hdd_overlay(hdd1_template, hdd1_qcow_path, log,
                                    persist=hdd1_persist):
            context["abort"] = True
            return False, "\n".join(log)

    # hdd2 has two modes:
    #  - prepare=True (default): (re)format it as a FAT "D:" source/output disk
    #    and copy the project source in
    #  - prepare=False: attach the file AS-IS. Needed when hdd2 is a pre-built template
    hdd2_prepare = _as_bool(hdd2_prepare)
    if hdd2_path and hdd2_prepare:
        srcdisk_size_mb = resolve_path(
            srcdisk_size_mb or config.get("srcdisk_size_mb") or 512, vars_map)
        sourcecode_dir = resolve_path(
            sourcecode_dir or "{projbasedir}{projdir}/{src_dir}", vars_map)
        if not _prepare_srcdisk(hdd2_path, srcdisk_size_mb, sourcecode_dir, log):
            context["abort"] = True
            return False, "\n".join(log)
    elif hdd2_path:
        log.append(f"  hdb attached as-is (no format): {hdd2_path}")

    # Floppy is optional
    if floppy1_path:
        make_disk_image(floppy1_path, floppy1_size)
    else:
        floppy1_path = None
    if floppy2_path and floppy2_size:
        make_disk_image(floppy2_path, floppy2_size)

    memory = resolve_path(memory or config.get("memory") or "4M", vars_map)
    machine = resolve_path(machine or config.get("machine"), vars_map) or None
    cpu = resolve_path(cpu or config.get("cpu"), vars_map) or None
    vga = resolve_path(vga or config.get("vga"), vars_map) or None
    net_device = resolve_path(net_device or config.get("net_device"), vars_map) or None
    mac_address = resolve_path(mac_address or config.get("mac_address"), vars_map) or None
    bios_path = resolve_path(bios_path or config.get("bios_path"), vars_map) or None
    boot_order = resolve_path(boot_order or config.get("boot_order"), vars_map) or None

    qemu_binary = resolve_path(qemu_binary or config.get("qemu_binary"), vars_map) or None
    prom_env = [resolve_path(v, vars_map)
                for v in _as_list(prom_env if prom_env is not None
                                  else config.get("prom_env"))]
    extra_args = [resolve_path(v, vars_map)
                  for v in _as_list(extra_args if extra_args is not None
                                    else config.get("extra_args"))]
    extra_disks = [resolve_path(v, vars_map)
                   for v in _as_list(extra_disks if extra_disks is not None
                                     else config.get("extra_disks"))]
    
    log.append(f"Starting {name} on port {port} with image={hdd1_qcow_path}")
    if machine or cpu:
        log.append(f"  machine  = {machine or '(qemu default)'}"
                   f" cpu={cpu or '(qemu default)'} vga={vga or '(qemu default)'}")
    if bios_path:
        log.append(f"  bios     = {bios_path}")
    if qemu_binary:
        log.append(f"  binary   = {qemu_binary}")
    for extra in extra_disks:
        log.append(f"  disk     = {extra}")
    if hdd2_path:
        log.append(f"  hdb (D:) = {hdd2_path}")
    if floppy1_path:
        log.append(f"  fda (A:) = {floppy1_path}")
    if floppy2_path:
        log.append(f"  fdb (B:) = {floppy2_path}")
    if cdrom_path:
        log.append(f"  cdrom    = {cdrom_path}")
    if cdrom2_path:
        log.append(f"  cdrom2   = {cdrom2_path}")
    if serial_path:
        log.append(f"  serial   = {serial_path} (guest stdout via -serial file:)")
    if sound_device:
        log.append(f"  sound    = {sound_device} via -audiodev {audio_backend}"
                   + (f" -> {audio_out_path}" if audio_backend == "wav" else "")
                   + (f" (out={pa_out_name or 'default'}, in={pa_in_name or 'default'})"
                      if audio_backend == "pa" else ""))
    instance = QemuInstance(name, cpuarch, port, hdd1imagepath=hdd1_qcow_path,
                            hdd2imagepath=hdd2_path, cdrom_path=cdrom_path,
                            cdrom2_path=cdrom2_path,
                            floppy_path=floppy1_path, floppy2_path=floppy2_path,
                            memory=memory, vnc_port=vnc_port,
                            sound_device=sound_device, audio_backend=audio_backend,
                            audio_out_path=audio_out_path,
                            pa_out_name=pa_out_name, pa_in_name=pa_in_name,
                            pa_server=pa_server, serial_path=serial_path,
                            machine=machine, cpu=cpu, vga=vga,
                            net_device=net_device, mac_address=mac_address,
                            bios_path=bios_path, boot_order=boot_order,
                            prom_env=prom_env, extra_args=extra_args,
                            extra_disks=extra_disks,
                            screenshot_scale=config.get("ocr_scale"),
                            qemu_binary=qemu_binary)

    # Write a clickable launch script and register it
    projbasedir = vars_map.get("projbasedir", "") or config.get("projbasedir", "")
    projdir = vars_map.get("projdir", "") or config.get("projdir", "")
    project_dir = None
    if projbasedir and projdir:
        project_dir = os.path.join(projbasedir, projdir)
    elif hdd1_qcow_path:
        project_dir = os.path.dirname(hdd1_qcow_path)
    elif floppy1_path:
        project_dir = os.path.dirname(floppy1_path)
    script_target = (os.path.join(project_dir, f"start-qemu-{name}.sh")
                     if project_dir and os.path.isdir(project_dir) else None)
    script_ok, script_path = instance.write_launch_script(path=script_target)
    if script_ok:
        log.append(f"Wrote QEMU launch script: {script_path}")
        log.append(f"ARTIFACT: {script_path}")
        for img in instance.referenced_disk_images():
            log.append(f"ARTIFACT: {img}")
    else:
        log.append(script_path)

    time.sleep(3)

    # collect_qemu_logs joins a relative save_path onto the flat /testrunnerapp dir
    helperdir = "/testrunnerapp"
    if helperdir not in sys.path:
        sys.path.insert(0, helperdir)
    from appstate import current_reports_dir
    qemu_log_path = os.path.join(current_reports_dir(), f"qemu_stdout_{name}.log")

    if not instance.start():
        success, logs_or_msg = instance.collect_qemu_logs(qemu_log_path)
        log.append("Failed to start QEMU.")
        log.append(logs_or_msg)
        context["abort"] = True
        return False, "\n".join(log)

    success, logs_or_msg = instance.collect_qemu_logs(qemu_log_path)
    log.append(logs_or_msg)

    if not instance.wait_for_ready():
        log.append(f"{name} did not become ready.")
        log.append(logs_or_msg)
        return False, "\n".join(log)

    context[name] = instance
    # First-started instance is the default "qemu1" target for subsequent
    context.setdefault("qemu1", instance)
    log.append(f"{name} is ready.")
    log.append(logs_or_msg)

    if vnc_port:
        vnc_ok, vnc_msg = instance.vnc_connect()
        log.append(vnc_msg)
        if not vnc_ok:
            context["abort"] = True
            return False, "\n".join(log)

    _maybe_screenshot(instance, takeascreenshot, log, label=name)

    return True, "\n".join(log)


@dispatchtest_step
def test_start_basilisk(name="basilisk1", rom=None, boot_disk=None,
                        extra_disk=None, serial_path=None, ramsize_mb=64,
                        modelid=14, cpu=4, fpu="true", takeascreenshot=False,
                        **kwargs):
    """Launch a Basilisk II classic-Mac emulator (alternative to the QEMU q800).
    Basilisk mounts RAW HFS images directly.
    extra_disk points at the raw .dsk a host build emits.
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    rom = resolve_path(rom or config.get("basilisk_rom"), vars_map) or None
    boot_disk = resolve_path(boot_disk or config.get("basilisk_boot_disk"), vars_map) or None
    extra_disk = resolve_path(extra_disk, vars_map) or None
    serial_path = resolve_path(serial_path or config.get("serial_path"), vars_map) or None

    kw = {}
    if rom: kw["rom"] = rom
    if boot_disk: kw["boot_disk"] = boot_disk
    inst = BasiliskInstance(
        name, extra_disks=[extra_disk] if extra_disk else None,
        serial_path=serial_path, ramsize_mb=int(ramsize_mb),
        modelid=int(modelid), cpu=int(cpu), fpu=_as_bool(fpu), **kw)

    log = [f"Starting Basilisk '{name}'"]
    if extra_disk:
        log.append(f"  app disk (raw HFS) = {extra_disk}")
    if serial_path:
        log.append(f"  serial -> {serial_path} (Mac serial A via pty)")
    if not inst.start():
        context["abort"] = True
        return False, "\n".join(log + inst.stdout_lines)

    context[name] = inst
    context.setdefault("qemu1", inst)     # default target for shared steps
    log.append(f"{name} launched (pid {inst.process.pid})")
    _maybe_screenshot(inst, takeascreenshot, log, label=name)
    return True, "\n".join(log)


@dispatchtest_step
def test_hostbuild(command=None, cwd=None, timeout=600, **kwargs):
    """Run a host-side build command for retro68k and others. cross-compile before
    booting QEMU. This is the 'compile on the Linux host' half of the m68k
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    command = resolve_path(command, vars_map)
    cwd = resolve_path(cwd, vars_map) or None
    if not command:
        return False, "test_hostbuild: no command given"

    log = [f"$ {command}" + (f"   (cwd={cwd})" if cwd else "")]
    timeout = int(timeout)
    fd, out_path = tempfile.mkstemp(prefix="test_hostbuild_", suffix=".log")
    os.close(fd)
    start = time.time()
    try:
        with open(out_path, "w") as out_f:
            proc = subprocess.Popen(command, shell=True, cwd=cwd,
                                    stdout=out_f, stderr=subprocess.STDOUT,
                                    start_new_session=True)
        timed_out = False
        aborted = False
        while True:
            try:
                proc.wait(timeout=2)
                break
            except subprocess.TimeoutExpired:
                if context.get("abort"):
                    aborted = True
                elif time.time() - start > timeout:
                    timed_out = True
                else:
                    continue
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
                break

        with open(out_path) as f:
            output = f.read().rstrip()
    finally:
        try:
            os.remove(out_path)
        except OSError:
            pass

    if output:
        log.append(output)

    if aborted:
        return False, "\n".join(log + ["aborted (stop requested)"])
    if timed_out:
        context["abort"] = True
        return False, "\n".join(log + [f"timed out after {timeout}s"])
    if proc.returncode != 0:
        context["abort"] = True
        log.append(f"exit {proc.returncode} — build FAILED")
        return False, "\n".join(log)
    log.append("build OK")
    return True, "\n".join(log)


@dispatchtest_step
def test_filecontains(file_path=None, successphrase=None, failphrase=None,
                      timeout=20, **kwargs):
    """Assert a host file contains successphrase and not failphrase. 
    OCR-free verification path for m68k mac: the guest writes
    a token to the serial port, QEMU captures it to this file -serial file:,
    and grep it. Polls up to `timeout`s .
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    file_path = resolve_path(file_path, vars_map)
    if not file_path:
        return False, "test_filecontains: no file_path given"

    log = [f"checking {file_path} for '{successphrase}'"]
    deadline = time.time() + int(timeout)
    content = ""
    while time.time() < deadline:
        try:
            with open(file_path, "r", errors="replace") as f:
                content = f.read()
        except FileNotFoundError:
            content = ""
        if failphrase and failphrase in content:
            context["abort"] = True
            log.append(f"FAIL phrase '{failphrase}' present")
            return False, "\n".join(log)
        if successphrase and successphrase in content:
            log.append(f"found '{successphrase}'")
            return True, "\n".join(log)
        time.sleep(1)

    context["abort"] = True
    log.append(f"'{successphrase}' not found within {timeout}s")
    log.append(f"--- file tail ---\n{content[-500:]}")
    return False, "\n".join(log)


@dispatchtest_step
def test_attach_screenshot(image_path=None, name="img", scale=1, **kwargs):
    """Attach host-side image(s) to this step of the report, the way a QEMU
    screendump appears.

    For platforms whose "screen" is a file rather than a VM framebuffer: the
    nova_fb device writes a PNG every time the Nova program presents a frame,
    and without this the report shows only console text

    image_path may name one file or a glob ("output/cursor*.png"); matches are
    attached in sorted order.

    Report assets matched by FILENAME:
    screenshot-<name>-<stepnum>[-<n>].(png|gif) in the runner's reports dir,
    where <name> must contain no '-' (the pattern is screenshot-[^-]+-(\\d+)).
    reporthelper._move_assets then sweeps them into the report subdirectory.

    scale>1 nearest-neighbour upscales before attaching, for small or 1-bit
    frames that are hard to see at native size in a browser.
    """
    import glob as _glob
    import shutil as _shutil

    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    image_path = resolve_path(image_path, vars_map)
    if not image_path:
        return False, "test_attach_screenshot: no image_path given"
    if "-" in str(name):
        return False, f"test_attach_screenshot: name {name!r} must not contain '-'"

    matches = sorted(_glob.glob(image_path)) if any(c in image_path for c in "*?[") \
        else ([image_path] if os.path.exists(image_path) else [])
    log = [f"attaching {len(matches)} image(s) from {image_path}"]
    if not matches:
        context["abort"] = True
        return False, "\n".join(log + ["no image matched — nothing to attach"])

    # Step number for the filename, same source qemuhelpers.take_screenshot uses.
    _helperdir = "/testrunnersrc/pyhelpers"
    if _helperdir not in sys.path:
        sys.path.insert(0, _helperdir)
    try:
        from appstate import progress_state, current_reports_dir
        stepnum = re.match(r"\d+", progress_state.step).group(0)
    except Exception as e:
        return False, "\n".join(log + [f"could not determine step number: {e}"])

    try:
        reports_dir = current_reports_dir()
    except OSError as e:
        return False, "\n".join(log + [f"reports dir unavailable: {e}"])

    scale = int(scale)
    for i, src in enumerate(matches):
        suffix = f"-{i}" if len(matches) > 1 else ""
        dest = os.path.join(reports_dir, f"screenshot-{name}-{stepnum}{suffix}.png")
        if scale > 1:
            img = Image.open(src)
            img = img.convert("L").resize((img.width * scale, img.height * scale),
                                          Image.NEAREST)
            img.save(dest)
            log.append(f"  {os.path.basename(src)} -> {os.path.basename(dest)} "
                       f"({img.width}x{img.height}, {scale}x)")
        else:
            _shutil.copyfile(src, dest)
            log.append(f"  {os.path.basename(src)} -> {os.path.basename(dest)}")
    return True, "\n".join(log)


@dispatchtest_step
def test_start_gif_capture(name="qemu1", interval=0.5, max_seconds=120,
                           max_frames=240, scale=1, playback_speed=1, **kwargs):
    """Start recording the screen to an animated GIF and RETURN IMMEDIATELY.

    non blocking: it starts a background
    thread that grabs a frame every `interval` seconds and stays resident until terminated

    Recording stops on the first of: an explicit test_stop_gif_capture,
    test_terminate_all, max_seconds, max_frames, the testlist ending, or the
    instance dying. 

    The GIF is attached to whichever step STOPS the recording (assets are
    keyed by step number) -- test_stop_gif_capture or teardown -- not to this
    step.

      interval        seconds between frames (0.5 = 2 fps)
      max_seconds     hard cap on wall-clock recording time (0 = no cap)
      max_frames      hard cap on frames kept (0 = no cap) -- frames are held
                      in memory until the GIF is written, so this is the knob
                      that bounds it
      scale           <1 shrinks the frames (0.5 halves each side)
      playback_speed  >1 plays the GIF faster than real time
    """
    context = kwargs.get("context", {})
    instance = context.get(name)
    if not instance:
        return False, f"No instance '{name}' available in context"
    if not hasattr(instance, "take_screenshot"):
        return False, f"Instance '{name}' ({type(instance).__name__}) cannot screenshot"
    if "-" in str(getattr(instance, "name", "")):
        # Report assets are matched with screenshot-[^-]+-(\d+), so a '-' in
        # the instance name makes the GIF unattachable.
        return False, f"instance name {instance.name!r} must not contain '-'"

    # An earlier recorder on the same instance would fight this one for the
    # monitor and overwrite its GIF -- close it out first.
    log = []
    for rec in active_recorders():
        if rec.instance is instance:
            log.append(rec.stop(reason="superseded by a new capture step")[1])

    recorder = GifRecorder(
        instance,
        interval=float(interval),
        max_seconds=float(max_seconds),
        max_frames=int(max_frames),
        scale=float(scale),
        playback_speed=float(playback_speed),
    ).start()

    context.setdefault("_gif_recorders", []).append(recorder)

    log.append(f"[{instance.name}] recording started — a frame "
               f"every {recorder.interval:g}s, until test_stop_gif_capture"
               f" (caps: {recorder.max_seconds:g}s / {recorder.max_frames} frames)."
               f" GIF will attach to whichever step stops it, not this one.")
    return True, "\n".join(log)


@dispatchtest_step
def test_stop_gif_capture(name=None, **kwargs):
    """Stop a recording started by test_start_gif_capture and write its GIF.

    A capture runs until something explicitly ends it, so pair every
    test_start_gif_capture with one of these. 
    """
    context = kwargs.get("context", {})
    recorders = [r for r in active_recorders()
                 if not name or getattr(r.instance, "name", None) == name]
    if not recorders:
        return True, ("no GIF recording in progress"
                      + (f" for '{name}'" if name else ""))

    log = []
    ok_all = True
    for rec in recorders:
        ok, msg = rec.stop(reason="test_stop_gif_capture")
        ok_all = ok_all and ok
        log.append(msg)
    return ok_all, "\n".join(log)


@dispatchtest_step
def test_terminate_all(**kwargs):
    """Stop every emulator instance registered in context — QEMU, SIMH,
    Basilisk, DOSBox-X and 86Box 
    """
    context = kwargs.get("context", {}) or {}
    log = []

    for ok, msg in stop_all_gif_recorders(reason="test_terminate_all"):
        log.append(msg)

    time.sleep(3)

    seen, uniq = set(), []
    for inst in context.values():
        if isinstance(inst, (QemuInstance, NovaSimhInstance, BasiliskInstance,
                             NovaFbMonitorProcess, NovaTermProcess,
                             VerilatorLiveInstance, VerilatorFbMonitorProcess)
                      + GUI_INSTANCE_TYPES) and id(inst) not in seen:
            seen.add(id(inst))
            uniq.append(inst)

    if not uniq:
        log.append("No QEMU/SIMH instances found to stop.")
        return True, "\n".join(log)

    for inst in uniq:
        if isinstance(inst, (NovaFbMonitorProcess, NovaTermProcess,
                            VerilatorFbMonitorProcess)) and inst.keep_open:
            # the testlist asked to stay active,  "PAUSE ON" set here
            log.append(f"Leaving {inst.name} open (keep_open); close it with Q")
            continue
        log.append(f"Stopping {inst.name}")
        inst.stop()
        log.append(f"{inst.name} has exited.")
    return True, "\n".join(log)


@dispatchtest_step
def test_assert_screen_size(expected_width=None, expected_height=None,
                            name="qemu1", tolerance=0, require_success=True,
                            **kwargs):
    """Assert the guest's current framebuffer resolution.

    Takes a fresh `screendump` (QEMU captures the guest surface at its NATIVE
    size) and compares the resulting image's pixel dimensions to
    expected_width x expected_height. 
    """
    context = kwargs.get("context", {}) or {}
    instance = context.get(name)
    if not instance:
        return False, f"No QEMU instance '{name}' available in context"
    if expected_width is None or expected_height is None:
        return False, "expected_width and expected_height are required"

    ew, eh, tol = int(expected_width), int(expected_height), int(tolerance)

    ok, path = instance.take_screenshot()
    if not ok:
        return False, f"screendump failed: {path}"

    try:
        w, h = Image.open(path).size
    except Exception as e:
        return False, f"could not read screendump {path}: {e}"

    match = abs(w - ew) <= tol and abs(h - eh) <= tol
    msg = f"screen {w}x{h} vs expected {ew}x{eh} (tol {tol}) -> {'MATCH' if match else 'MISMATCH'}"
    if match:
        return True, msg
    return (not _as_bool(require_success)), msg


@dispatchtest_step
def test_audio_tonecheck(wav_path=None, expect_hz=1000, tolerance_hz=60,
                         min_snr_db=10, instance_name="qemu1",
                         require_success=True, **kwargs):
    """Verify the guest played a tone at expect_hz.

    Reads the .wav that QEMU's wav audiodev captured from the emulated sound
    card and looks for the tone with a Goertzel filter. Run this AFTER
    test_terminate_all: QEMU backfills the RIFF header when it exits
    """
    log = []
    context = kwargs.get("context", {}) or {}
    config = kwargs.get("config", {})
    vars_map = build_vars(config)
    require_success = str(require_success).strip().lower() in ("1", "true", "yes", "on")

    wav_path = resolve_path(wav_path, vars_map) or None
    try:
        expect_hz = float(resolve_path(expect_hz, vars_map))
        tolerance_hz = float(resolve_path(tolerance_hz, vars_map))
        min_snr_db = float(resolve_path(min_snr_db, vars_map))
    except (TypeError, ValueError) as e:
        msg = f"Bad tone-check parameter: {e}"
        log.append(msg)
        if require_success:
            context["abort"] = True
        return (not require_success), "\n".join(log)
    if not wav_path:

        instance = context.get(instance_name)
        wav_path = getattr(instance, "audio_out_path", None)
    if not wav_path:
        msg = (f"No wav_path given and instance {instance_name!r} has no audio_out_path "
               f"— did test_startqemu set sound_device/audio_backend=wav?")
        log.append(msg)
        if require_success:
            context["abort"] = True
        return (not require_success), "\n".join(log)

    ok, msg, details = detect_tone(wav_path, expect_hz=expect_hz,
                                   tolerance_hz=tolerance_hz,
                                   min_snr_db=min_snr_db)
    log.append(msg)
    if details:
        log.append(f"  measured: {details}")


    if os.path.isfile(wav_path):
        log.append(f"ARTIFACT: {wav_path}")

    if not ok and require_success:
        context["abort"] = True
        return False, "\n".join(log)

    return True, "\n".join(log)


@dispatchtest_step
def test_audio_tonesequence(wav_path=None, expect_hz_list=None, tolerance_hz=60,
                            min_snr_db=10, instance_name="qemu1",
                            require_success=True, **kwargs):
    """capture tool for tone testing. cycles through several different tones
    Uses mediahelpers.detect_tone_sequence, which slides a
    window across the capture and finds each expected frequency's own best
    window independently.

    expect_hz_list accepts a comma-separated string ("440,660,880") or a list.

    Run this AFTER test_terminate_all, same reason as test_audio_tonecheck:
    QEMU only backfills the .wav's RIFF header on a clean exit.
    """
    log = []
    context = kwargs.get("context", {}) or {}
    config = kwargs.get("config", {})
    vars_map = build_vars(config)
    require_success = str(require_success).strip().lower() in ("1", "true", "yes", "on")

    wav_path = resolve_path(wav_path, vars_map) or None
    expect_hz_list = resolve_path(expect_hz_list, vars_map)
    try:
        if isinstance(expect_hz_list, str):
            expect_hz_list = [float(h) for h in re.split(r"[,\s]+", expect_hz_list.strip()) if h]
        else:
            expect_hz_list = [float(h) for h in (expect_hz_list or [])]
        tolerance_hz = float(resolve_path(tolerance_hz, vars_map))
        min_snr_db = float(resolve_path(min_snr_db, vars_map))
    except (TypeError, ValueError) as e:
        msg = f"Bad tone-sequence-check parameter: {e}"
        log.append(msg)
        if require_success:
            context["abort"] = True
        return (not require_success), "\n".join(log)
    if not expect_hz_list:
        msg = "test_audio_tonesequence: no expect_hz_list given"
        log.append(msg)
        if require_success:
            context["abort"] = True
        return (not require_success), "\n".join(log)
    if not wav_path:
        instance = context.get(instance_name)
        wav_path = getattr(instance, "audio_out_path", None)
    if not wav_path:
        msg = (f"No wav_path given and instance {instance_name!r} has no audio_out_path "
               f"— did test_startqemu set sound_device/audio_backend=wav?")
        log.append(msg)
        if require_success:
            context["abort"] = True
        return (not require_success), "\n".join(log)

    ok, msg, details = detect_tone_sequence(wav_path, expect_hz_list,
                                            tolerance_hz=tolerance_hz,
                                            min_snr_db=min_snr_db)
    log.append(msg)
    if details:
        log.append(f"  measured: {details}")

    if os.path.isfile(wav_path):
        log.append(f"ARTIFACT: {wav_path}")

    if not ok and require_success:
        context["abort"] = True
        return False, "\n".join(log)

    return True, "\n".join(log)


@dispatchtest_step
def test_startnovasimh(name="nova1", disk_image_path=None, boot_timeout=30, memory=None,
                       binary=None, script_path=None, cwd=None, boot_rdos=True,
                       live_path=None, **kwargs):
    """Power on a dgnova SIMH instance and drive it through the fixed
    RDOS cold-boot prompt sequence up to the 'R' console prompt.

    Optional arguments let a project run its own simulator build and its own
    SIMH script instead of booting RDOS off a disk:
      binary      alternate simulator (sourcedir/nova_fb/bin/dgnova-fb has the
                  framebuffer device on code 042; the stock dgnova does not)
      script_path SIMH command file to run instead of the generated boot script
      cwd         working directory, so relative paths inside that script resolve
      boot_rdos   False for a script that runs a bare program and halts, where
                  there is no Filename?/Date/Time prompt sequence to drive
      live_path   nova_fb live view sink ("set fb live="), which
                  test_start_novafb_monitor opens to put the card's output in a
                  window. Costs a memcpy per present and nothing when unset.
    """
    log = []
    context = kwargs.get("context")
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    disk_image_path = resolve_path(disk_image_path, vars_map) if disk_image_path else None
    binary = resolve_path(binary, vars_map) if binary else None
    script_path = resolve_path(script_path, vars_map) if script_path else None
    cwd = resolve_path(cwd, vars_map) if cwd else None
    live_path = resolve_path(live_path, vars_map) if live_path else None
    boot_timeout = int(boot_timeout)
    boot_rdos = _as_bool(boot_rdos)

    instance = NovaSimhInstance(name, disk_image=disk_image_path, memory=memory,
                                binary=binary, script_path=script_path, cwd=cwd,
                                live_path=live_path)
    if script_path:
        log.append(f"Starting {name} ({instance.binary}) with script={script_path}")
    else:
        log.append(f"Starting {name} ({instance.binary}) with disk={instance.disk_image}")

    if not instance.start():
        log.append("Failed to start dgnova.")
        log.append(instance.buf)
        context["abort"] = True
        return False, "\n".join(log)

    if boot_rdos and not instance.boot_to_rdos(timeout=boot_timeout):
        log.append("Timed out waiting for RDOS boot / 'R' prompt.")
        log.append(instance.buf[-1000:])
        instance.stop()
        context["abort"] = True
        return False, "\n".join(log)

    context[name] = instance
    # First-started instance is the default "nova1" target for subsequent
    context.setdefault("nova1", instance)
    log.append(f"{name} booted to RDOS console." if boot_rdos
               else f"{name} started; running {script_path}.")
    log.append(instance.buf[-500:])
    return True, "\n".join(log)


@dispatchtest_step
def test_start_novafb_monitor(name="novafb_monitor", live_path=None, scale=0,
                              fps=60, title=None, wait=30, require_success=True,
                              keep_open=False, **kwargs):
    """Open a window showing what the nova_fb card is presenting
    
    pyhelpers/novafbhelpers.py's Monitor, a pygame window 
    fed by the card's shared-memory live sink.

    Pair it with live_path on test_startnovasimh 

    The window MATCHES THE CARD'S RESOLUTION: 720x400 of framebuffer is a
    720x400 window, with no padding

    A mode change replaces the X window -- pygame's set_mode always
    does -- so the window will not keep its position across one. The size is
    only ever set when the mode or the zoom changes, never per frame.

    keep_open leaves the window up after test_terminate_all

    The returned message names the DISPLAY the window went to
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    live_path = resolve_path(live_path, vars_map) if live_path else DEFAULT_LIVE_PATH

    monitor = NovaFbMonitorProcess(name, live_path=live_path, scale=int(scale),
                                   fps=int(fps), title=title, wait=float(wait),
                                   keep_open=_as_bool(keep_open))
    ok, msg = monitor.start()
    if not ok:
        # this is the vga fb viewer not the term monitor
        if _as_bool(require_success):
            context["abort"] = True
            return False, msg
        return True, f"{msg} (require_success=False, continuing headless)"

    context[name] = monitor
    return True, msg


@dispatchtest_step
def test_start_verilator_live(name="verilator1", binary=None, live_path=None,
                              cwd=None, seconds=0, **kwargs):
    """Run a compiled Verilator testbench binary in --live mod 
    clock runs indefinitely, publishing a frame to
    `live_path` every time it completes one

    Pair it with test_start_verilatorfb_monitor

    this is the optional vga-viewer half of the verilator_vga backend
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    binary = resolve_path(binary, vars_map)
    live_path = resolve_path(live_path, vars_map) if live_path else VERILATOR_DEFAULT_LIVE_PATH
    cwd = resolve_path(cwd, vars_map) if cwd else None

    inst = VerilatorLiveInstance(name, binary=binary, live_path=live_path,
                                 cwd=cwd, seconds=int(seconds))
    ok, msg = inst.start()
    if not ok:
        context["abort"] = True
        return False, msg

    context[name] = inst
    return True, msg


@dispatchtest_step
def test_start_verilatorfb_monitor(name="verilatorfb_monitor", live_path=None,
                                   scale=0, fps=60, title=None, wait=30,
                                   require_success=True, keep_open=False,
                                   **kwargs):
    """Open a window showing what a Verilator testbench is presenting

    Same shape as test_start_novafb_monitor, for the verilator_vga 
    require_success=False keeps a headless container 
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    live_path = resolve_path(live_path, vars_map) if live_path else VERILATOR_DEFAULT_LIVE_PATH

    monitor = VerilatorFbMonitorProcess(name, live_path=live_path, scale=int(scale),
                                        fps=int(fps), title=title, wait=float(wait),
                                        keep_open=_as_bool(keep_open))
    ok, msg = monitor.start()
    if not ok:
        if _as_bool(require_success):
            context["abort"] = True
            return False, msg
        return True, f"{msg} (require_success=False, continuing headless)"

    context[name] = monitor
    return True, msg


@dispatchtest_step
def test_open_nova_terminal(name="nova_terminal", instance="nova1",
                            sock_path=None, title=None, geometry="100x30",
                            font_size=14, wait=30, require_success=True,
                            keep_open=False, banner=None, **kwargs):
    """Open a terminal window on the user's desktop attached to a running Nova's
    SIMH console

    require_success=False keeps a headless container
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    inst = context.get(instance)
    if not inst:
        return False, f"No SIMH/Nova instance '{instance}' available in context"

    sock_path = (resolve_path(sock_path, vars_map) if sock_path
                 else f"/tmp/novaconsole-{instance}-{os.getpid()}.sock")
    try:
        inst.open_console_relay(sock_path)
    except Exception as exc:
        msg = f"Could not serve {instance}'s console on {sock_path}: {exc}"
        if _as_bool(require_success):
            context["abort"] = True
            return False, msg
        return True, f"{msg} (require_success=False, continuing)"

    term = NovaTermProcess(name, sock_path=sock_path, title=title,
                           geometry=geometry, font_size=int(font_size),
                           wait=float(wait), keep_open=_as_bool(keep_open),
                           banner=banner or "")
    ok, msg = term.start()
    if not ok:
        if _as_bool(require_success):
            context["abort"] = True
            return False, msg
        return True, f"{msg} (require_success=False, continuing headless)"

    context[name] = term
    return True, msg


@dispatchtest_step
def test_sendnovacommand(cmd_text="", name="nova1", delay=1.0, **kwargs):
    """Send a line of text to a dgnova SIMH instance's
    console"""
    context = kwargs.get("context", {})
    instance = context.get(name)
    if not instance:
        return False, f"No SIMH/Nova instance '{name}' available in context"

    instance.send_command(cmd_text)
    time.sleep(float(delay))
    log = [f"{name} sent command: {cmd_text!r}", instance.buf[-500:]]
    return True, "\n".join(log)


@dispatchtest_step
def test_novascreensearch(successphrase=None, failphrase=None, timeout=15,
                          require_success=False, name="nova1", **kwargs):
    """Search a Nova SIMH instance's captured console text for a phrase """
    context = kwargs.get("context", {})
    instance = context.get(name)
    if not instance:
        return False, f"No SIMH/Nova instance '{name}' available in context"

    timeout = int(timeout)
    require_success = _as_bool(require_success)
    log = []

    found = instance.wait_for(successphrase, timeout=timeout) if successphrase else True
    failed = bool(failphrase) and failphrase in instance.buf

    log.append(f"{name} console tail:\n{instance.buf[-800:]}")

    if failed:
        log.append(f"Fail phrase '{failphrase}' found on console")
        context["abort"] = True
        instance.stop()
        log.append(f"Stopped {name} (abort path — a later teardown step "
                   f"won't run since context['abort'] short-circuits it)")
        return False, "\n".join(log)

    if require_success and not found:
        log.append(f"Success phrase '{successphrase}' not found "
                   f"(require_success) — failing step")
        context["abort"] = True
        instance.stop()
        log.append(f"Stopped {name} (abort path — a later teardown step "
                   f"won't run since context['abort'] short-circuits it)")
        return False, "\n".join(log)

    log.append(f"success phrase found: {found}")
    return True, "\n".join(log)


@dispatchtest_step
def test_cully_llvm_compile(src_path=None, out_path=None, cpu="nova3",
                            header_lines=None, footer_lines=None,
                            cully_llvm_dir=None, timeout=120, **kwargs):
    """Compile a Nova C source through cully_llvm's nova-llvm-backend
    toolchain (nova-cc) into a SIMH deposit script -- the live-compile
    counterpart to the gen/*.ini files that ship pre-built in every nova-C
    project (cully_llvm/, xp5_nova_fpgademo/, ...), so a project that just
    reuses that compiler doesn't need its own gen_*.py subprocess wrapper
    (see xp5_nova_fpgademo/gen_fractal.py, which this generalizes).
    header_lines/footer_lines wrap the raw deposits with backend-specific
    setup (e.g. nova_fb's "set fb ...") or a "go 100"/"quit" trailer.

    Deliberately thin: all toolchain-path/env-var knowledge, and the
    fallback for a missing/unbuilt _toolchain/ or a deleted cully_llvm/
    entirely, live in simhhelpers.compile_via_nova_llvm -- so this step can
    never be the reason dispatch_functions.py itself fails to import, and a
    missing cully_llvm/ just fails this one step rather than the run.
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)
    src_path = resolve_path(src_path, vars_map)
    out_path = resolve_path(out_path, vars_map)
    cully_llvm_dir = resolve_path(cully_llvm_dir, vars_map) or None

    success, msg = compile_via_nova_llvm(
        src_path, out_path, cpu=cpu, cully_llvm_dir=cully_llvm_dir,
        header_lines=header_lines, footer_lines=footer_lines, timeout=timeout,
    )
    if not success:
        # Same convention as test_hostbuild: a failed build (missing
        # toolchain, deleted cully_llvm/, or a real compile error) must not
        # let a later test_startnovasimh step boot a stale/absent out_path.
        context["abort"] = True
    return success, msg


@dispatchtest_step
def test_mouseaction(action=None, name="qemu1", test_step=0,
                     takeascreenshot=False, **kwargs):
    """Run a named MouseAction helper against a QEMU instance .this is for the image-match + click
    macros used by the Mac m68k tests.
    """
    context = kwargs.get("context", {})
    instance = context.get(name)
    if not instance:
        return False, f"No QEMU instance '{name}' available in context"

    fn = getattr(MouseAction, action, None) if action else None
    if not callable(fn):
        return False, f"Unknown MouseAction '{action}'"

    success, log = fn(instance, test_step=test_step)
    shot_log = []
    _maybe_screenshot(instance, takeascreenshot, shot_log, label=name)
    if shot_log:
        log = f"{log}\n" + "\n".join(shot_log)
    if not success:
        context["abort"] = True
    return success, log


@dispatchtest_step
def test_findbutton_click(button_path=None, name="qemu1", test_step=0, **kwargs):
    """Screenshot the instance, locate button_path within it, and VNC-click
    its centre. Used by the VNC mac tests , absolute mouse move.
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    instance = context.get(name)
    if not instance:
        return False, f"No QEMU instance '{name}' available in context"

    button_path = resolve_path(button_path, vars_map)
    log = []

    ok, shot = instance.take_screenshot(test_step=test_step)
    if not ok:
        return False, f"[{instance.name}] Screenshot failed: {shot}"
    log.append(f"[{instance.name}] Screenshot taken: {shot}")

    found, pos = find_button_in_screenshot(button_path, shot)
    if not found:
        context["abort"] = True
        log.append(f"Button not found: {button_path}")
        return False, "\n".join(log)

    x, y = pos
    log.append(f"Button found at {pos}")

    # q800's ADB mouse is relative — position + click via the GTK-window
    # closed loop (xdotool + screendump feedback); direct monitor/VNC
    # injection can't position this device.
    ok, msg = instance.gui_move_to(x, y, do_click=True)
    log.append(msg)
    if not ok:
        context["abort"] = True
        return False, "\n".join(log)

    ok, shot = instance.take_screenshot(test_step=test_step)
    log.append(f"[{instance.name}] Post-click screenshot: {shot}")
    return True, "\n".join(log)


@dispatchtest_step
def test_find_and_open_icon(icon_path=None, name="qemu1", test_step=0,
                            clicks=2, tolerance=0.12, pixel_delta=48,
                            mask_path=None, region=None, exact_fallback=True,
                            **kwargs):
    """Locate a Finder icon, a mounted disk, or an application inside a window
    and OPEN it with a double-click.

    Uses find_icon_in_screenshot 
    falls back to the exact matcher
    if asked. Positions + double-clicks via the GTK/xdotool closed loop, since
    the q800's ADB mouse is relative. Params:
      icon_path     template PNG (crop tight to the glyph)
      clicks        2 = double-click to open; 1 = just select
      tolerance     max fraction of pixels allowed to mismatch
      pixel_delta   grayscale delta that counts a pixel as different
      mask_path     optional PNG, black = ignore (blanks the dithered surround)
      region        optional "x0,y0,x1,y1" search box (disks mount top-right)
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    instance = context.get(name)
    if not instance:
        return False, f"No QEMU instance '{name}' available in context"

    icon_path = resolve_path(icon_path, vars_map)
    mask_path = resolve_path(mask_path, vars_map) or None
    log = []

    # region may arrive as "x0,y0,x1,y1" (config strings) or a list.
    roi = None
    if region:
        if isinstance(region, str):
            roi = tuple(int(v) for v in region.split(","))
        else:
            roi = tuple(int(v) for v in region)

    ok, shot = instance.take_screenshot(test_step=test_step)
    if not ok:
        return False, f"[{instance.name}] Screenshot failed: {shot}"
    log.append(f"[{instance.name}] Screenshot taken: {shot}")

    found, pos = find_icon_in_screenshot(
        icon_path, shot, tolerance=float(tolerance),
        pixel_delta=int(pixel_delta), mask_path=mask_path, region=roi)
    if not found:
        log.append(f"tolerant match: {pos}")
        if exact_fallback:
            found, pos = find_button_in_screenshot(icon_path, shot)
            log.append(f"exact-match fallback: {'hit '+str(pos) if found else pos}")
    if not found:
        context["abort"] = True
        log.append(f"Icon not found: {icon_path}")
        return False, "\n".join(log)

    x, y = pos
    log.append(f"Icon found at {pos}; opening with {int(clicks)} click(s)")
    ok, msg = instance.gui_move_to(x, y, do_click=True, clicks=int(clicks))
    log.append(msg)
    if not ok:
        context["abort"] = True
        return False, "\n".join(log)

    time.sleep(2)                                # let the window/disk open
    ok, shot = instance.take_screenshot(test_step=test_step)
    log.append(f"[{instance.name}] Post-open screenshot: {shot}")
    return True, "\n".join(log)


@dispatchtest_step
def test_closeallwindows(button_path=None, name="qemu1", max_windows=8, **kwargs):
    """Close every open window by repeatedly locating a close-box image and
    clicking it.
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    instance = context.get(name)
    if not instance:
        return False, f"No QEMU instance '{name}' available in context"

    button_path = resolve_path(
        button_path or "/testsrc/buttontest/finder_window_closebutton.png", vars_map)

    max_windows = int(max_windows)      # config params arrive as strings
    log = []
    frames = []                         # PIL frames for the animated gif
    tmp_shot = f"/tmp/_closewin_{instance.name}.png"

    def capture():
        """Grab the guest framebuffer -> save temp png + keep a
        PIL frame for the gif. Returns the temp path (or None)."""
        arr = instance._gui_screencap()
        if arr is None:
            return None
        img = Image.fromarray(arr.astype("uint8"))
        img.save(tmp_shot)
        frames.append(img.copy())
        return tmp_shot

    closed = 0
    for i in range(max_windows):
        shot = capture()                # state before this close (also the match frame)
        if shot is None:
            return False, "screencap failed (monitor screendump)"
        found, pos = find_button_in_screenshot(button_path, shot)
        if not found:
            log.append(f"no close box found — {closed} window(s) closed")
            break
        okm, msg = instance.gui_move_to(pos[0], pos[1], do_click=True)
        log.append(f"window {i}: close box {pos} -> {msg.splitlines()[-1] if msg else ''}")
        closed += 1
        time.sleep(1.2)
    else:
        log.append(f"hit max_windows={max_windows}; {closed} closed")

    capture()                           # final state after the last close

    # Compile the frames into an animated gif named so the report attaches it
    # to this step: screenshot-<name>-<stepnum>.gif
    if frames:
        try:
            from appstate import progress_state, current_reports_dir
            stepnum = re.match(r"\d+", str(progress_state.step)).group(0)
            reports_dir = current_reports_dir()
        except Exception:
            stepnum = "0"
            reports_dir = "/testrunnerapp/reports"
        gif_path = os.path.join(reports_dir, f"screenshot-{instance.name}-{stepnum}.gif")
        try:
            frames[0].save(gif_path, save_all=True, append_images=frames[1:],
                           duration=900, loop=0, optimize=False)
            log.append(f"animated gif ({len(frames)} frames): {gif_path}")
        except Exception as e:
            log.append(f"gif build failed: {e}")

    return True, "\n".join(log)


@dispatchtest_step
def test_mouse_hang_probe(name="qemu1", rounds=24, moves_per_round=6, step_px=24,
                          settle=0.05, latency_ratio_threshold=4.0, freeze_rounds=4,
                          out_log=None, takeascreenshot=False, **kwargs):
    """Stress a PC-machine guest's PS/2 mouse over an extended period and
    watch for a *progressive* freeze rather than a hard hang.

    was using this to speed up debugging a win98 qemu-isapc bug

    Fails (and aborts, so test_terminate_all still tears down) if either
    signal crosses its threshold in the back half of the run.
    """
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)
    out_log = resolve_path(out_log, vars_map) if out_log else None

    instance = context.get(name)
    if not instance:
        return False, f"No QEMU instance '{name}' available in context"

    rounds = int(rounds)
    moves_per_round = int(moves_per_round)
    step_px = int(step_px)
    settle = float(settle)
    latency_ratio_threshold = float(latency_ratio_threshold)
    freeze_rounds = int(freeze_rounds)

    pattern = [(step_px if i % 2 == 0 else -step_px, 0) for i in range(moves_per_round)]

    log_lines = []
    latencies = []
    diffs = []
    prev_frame = None

    for r in range(rounds):
        t0 = time.time()
        for dx, dy in pattern:
            ok, msg = instance.send_mouse_pos(dx, dy)
            if not ok:
                log_lines.append(f"round {r}: mouse_move failed: {msg}")
            time.sleep(settle)
        shot_ok, shot_path = instance.take_screenshot()
        latency = time.time() - t0
        latencies.append(latency)

        diff = None
        if shot_ok:
            try:
                frame = np.asarray(Image.open(shot_path).convert("RGB")).astype(np.int32)
                if prev_frame is not None and prev_frame.shape == frame.shape:
                    diff = int(np.abs(frame - prev_frame).sum())
                prev_frame = frame
            except Exception as e:
                log_lines.append(f"round {r}: frame load failed: {e}")
        else:
            log_lines.append(f"round {r}: screendump failed: {shot_path}")
        diffs.append(diff)

        log_lines.append(f"round {r}: latency={latency:.2f}s diff={diff}")

    baseline_n = max(1, rounds // 6)
    tail_n = max(1, min(freeze_rounds, rounds // 2))
    baseline_latency = sorted(latencies[:baseline_n])[len(latencies[:baseline_n]) // 2]
    tail_latencies = latencies[-tail_n:]
    tail_latency = sorted(tail_latencies)[len(tail_latencies) // 2]
    latency_ratio = (tail_latency / baseline_latency) if baseline_latency > 0 else float("inf")

    early_diffs = [d for d in diffs[baseline_n:baseline_n + tail_n] if d is not None]
    tail_diffs = [d for d in diffs[-tail_n:] if d is not None]
    early_moved = any(d and d > 0 for d in early_diffs)
    tail_frozen = len(tail_diffs) == tail_n and all((d or 0) == 0 for d in tail_diffs)

    verdict_lines = [
        f"baseline_latency={baseline_latency:.2f}s tail_latency={tail_latency:.2f}s "
        f"ratio={latency_ratio:.2f} (threshold {latency_ratio_threshold})",
        f"early_moved={early_moved} tail_frozen={tail_frozen} (last {tail_n} rounds)",
    ]

    hang_detected = (latency_ratio >= latency_ratio_threshold) or (early_moved and tail_frozen)
    if hang_detected:
        verdict = "MOUSE_HANG_DETECTED"
    else:
        verdict = "MOUSE_OK"
    verdict_lines.insert(0, verdict)

    full_log = "\n".join(verdict_lines + log_lines)
    if out_log:
        try:
            os.makedirs(os.path.dirname(out_log), exist_ok=True)
            with open(out_log, "w") as f:
                f.write(full_log + "\n")
        except Exception as e:
            full_log += f"\n(failed to write out_log {out_log}: {e})"

    _maybe_screenshot(instance, takeascreenshot, [], label=name)

    if hang_detected:
        context["abort"] = True
        return False, full_log
    return True, full_log


def _as_lines(v):
    """Coerce a step param to a list of lines.

    Deliberately NOT _as_list: these carry DOS/emulator command lines, and a
    comma is an ordinary character in one (``imgmount c img -t hdd -fs fat``,
    ``hdd_01_parameters = 63, 32, 520, 0, ide``). A string is split on newlines
    only, so a single line survives intact.
    """
    if v is None or v == "":
        return []
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if str(x).strip()]
    return [ln for ln in str(v).splitlines() if ln.strip()]


def _resolve_tokens(text, vars_map, passes=5):
    """Resolve {tokens} in a file's CONTENT, one token at a time.

    Not resolve_path: that formats the whole string in a single str.format
    call, so one token with no CONFIG value raises and leaves the ENTIRE file
    unresolved. A config file is prose plus settings, and a stray brace in a
    comment must not silently cost every real path its value. Anything that
    does not name a CONFIG key is left standing verbatim, for the caller to
    report. Returns (text, sorted list of unresolved token names).
    """
    atomic = {k: v for k, v in vars_map.items() if isinstance(v, (str, int))}
    pattern = re.compile(r"\{([a-zA-Z_]\w*)\}")

    def sub(m):
        key = m.group(1)
        return str(atomic[key]) if key in atomic else m.group(0)

    for _ in range(passes):          # tokens whose values contain tokens
        new_text = pattern.sub(sub, text)
        if new_text == text:
            break
        text = new_text

    leftover = sorted({m.group(1) for m in pattern.finditer(text)})
    return text, leftover


def _current_stepnum(default="0"):
    """Number of the step now running, for naming report screenshots.

    Report assets are matched by FILENAME (screenshot-<name>-<stepnum>...),
    not by anything a step returns — see test_attach_screenshot.
    """
    _helperdir = "/testrunnersrc/pyhelpers"
    if _helperdir not in sys.path:
        sys.path.insert(0, _helperdir)
    try:
        from appstate import progress_state
        return re.match(r"\d+", str(progress_state.step)).group(0)
    except Exception:
        return default


def _gui_instance(context, name=None):
    """Fetch a DOSBox-X / 86Box instance from context.

    With no name, returns the only such instance — a testlist running one
    emulator then never has to repeat its name on every step. Returns
    (instance, error_message).
    """
    if name:
        inst = context.get(name)
        if not isinstance(inst, GUI_INSTANCE_TYPES):
            return None, f"No DOSBox-X/86Box instance '{name}' available in context"
        return inst, None

    found = []
    for inst in context.values():
        if isinstance(inst, GUI_INSTANCE_TYPES) and not any(inst is f for f in found):
            found.append(inst)
    if not found:
        return None, "No DOSBox-X/86Box instance available in context"
    if len(found) > 1:
        return None, ("Several DOSBox-X/86Box instances are running "
                      f"({', '.join(i.name for i in found)}) — pass name=")
    return found[0], None


def _dead_gui_instance(context):
    """Name of a DOSBox-X/86Box instance in context that has exited, else None.

    Lets a step that is otherwise waiting on something off-screen (a build
    artifact appearing on a mounted host dir) give up as soon as the emulator
    producing it goes away — closing the window is the user saying "stop",
    and nothing is going to write that file afterwards.

    Returns None when no GUI instance is in context at all, so host-only
    builds are unaffected.
    """
    for inst in context.values():
        if isinstance(inst, GUI_INSTANCE_TYPES):
            alive = getattr(inst, "is_alive", None)
            if alive is not None and not alive():
                return inst.name
    return None


@dispatchtest_step
def test_flatten_qcow_to_raw(qcow_path=None, raw_path=None, hdd1_template=None,
                             **kwargs):
    """Flatten a QCOW2 overlay (plus its backing template) into a raw image.

    DOSBox-X and 86Box cannot read QCOW2, so a project that boots the shared
    read-only template under one of them mounts this per-run raw copy instead.
    Same bytes QEMU's C: sees; the template is never written to.

    hdd1_template is optional and only used when qcow_path does not exist yet:
    the overlay is created from that template first, so a test that has never
    been run under QEMU still has a C: to flatten. Named like the template
    filenames in /testsrc/templates, or an absolute path.
    """
    log = []
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    qcow_path = resolve_path(qcow_path, vars_map)
    raw_path = resolve_path(raw_path, vars_map)
    hdd1_template = resolve_path(hdd1_template or config.get("hdd1_template"), vars_map)

    if not qcow_path or not raw_path:
        return False, "test_flatten_qcow_to_raw: qcow_path and raw_path are required"

    if not os.path.isfile(qcow_path):
        if not hdd1_template:
            context["abort"] = True
            return False, (f"No QCOW2 at {qcow_path} and no hdd1_template to build "
                           f"one from")
        if not _prepare_hdd_overlay(hdd1_template, qcow_path, log, persist=False):
            context["abort"] = True
            return False, "\n".join(log)

    success, output = convert_qcow2_to_raw(qcow_path, raw_path)
    log.append(output)
    if not success:
        context["abort"] = True
    return success, "\n".join(log)


@dispatchtest_step
def test_copy_tree(src_dir=None, dest_dir=None, clean=True, **kwargs):
    """Copy a directory tree on the host, by default replacing the destination.

    Two uses, both of which keep a run from dirtying tracked files: giving an
    emulator a throwaway copy of its VM directory (86Box rewrites its cfg and
    CMOS into it), and giving a build a throwaway copy of src/ so the output
    never lands in the source tree.
    """
    log = []
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    src_dir = resolve_path(src_dir, vars_map)
    dest_dir = resolve_path(dest_dir, vars_map)
    if not src_dir or not dest_dir:
        return False, "test_copy_tree: src_dir and dest_dir are required"
    if not os.path.isdir(src_dir):
        context["abort"] = True
        return False, f"source directory not found: {src_dir}"

    try:
        if _as_bool(clean) and os.path.isdir(dest_dir):
            shutil.rmtree(dest_dir)
        os.makedirs(os.path.dirname(os.path.abspath(dest_dir)) or ".", exist_ok=True)
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=not _as_bool(clean))
    except OSError as e:
        context["abort"] = True
        return False, "\n".join(log + [f"copy failed: {e}"])

    log.append(f"Copied {src_dir} -> {dest_dir}")
    return True, "\n".join(log)


@dispatchtest_step
def test_render_file(template_path=None, out_path=None, **kwargs):
    """Write out a config file with its {tokens} resolved against CONFIG.

    For a generated file that carries host paths and is NOT edited by hand.
    An emulator config a human tunes in a GUI is the opposite case: keep that
    in the project dir and point the emulator straight at it (see how
    __testlist__OWC_CLONETEST2_86box.py uses 86box.cfg), because regenerating
    it each run throws the hand-tuned hardware away.
    """
    log = []
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    template_path = resolve_path(template_path, vars_map)
    out_path = resolve_path(out_path, vars_map)
    if not template_path or not out_path:
        return False, "test_render_file: template_path and out_path are required"
    if not os.path.isfile(template_path):
        context["abort"] = True
        return False, f"template not found: {template_path}"

    with open(template_path, "r") as f:
        rendered, leftover = _resolve_tokens(f.read(), vars_map)

    if leftover:
        context["abort"] = True
        return False, (f"{template_path}: no value in CONFIG for "
                       f"{', '.join('{'+t+'}' for t in leftover)}")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        f.write(rendered)
    log.append(f"Rendered {template_path} -> {out_path}")
    log.append(f"ARTIFACT: {out_path}")
    return True, "\n".join(log)


@dispatchtest_step
def test_dosbox_conf(config_path=None, template_path=None, autoexec=None,
                     machine=None, memsize=None, cpu_cycles=None, **kwargs):
    """Build the dosbox-x .conf a run boots from.

    template_path is an existing full dosbox-x config (the ~250-line one it
    writes itself); only the [autoexec] lines are added on top, so a test never
    has to restate the whole file. Without a template a minimal config is
    generated from machine/memsize.

    `autoexec` is the lines to run at boot

    `cpu_cycles`, if given, is written as `[cpu]\\ncycles=<value>` 

    Written to config_path
    """
    log = []
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    config_path = resolve_path(config_path, vars_map)
    template_path = resolve_path(template_path or config.get("config_path"), vars_map)
    if not config_path:
        return False, "test_dosbox_conf: config_path is required"

    os.makedirs(os.path.dirname(os.path.abspath(config_path)) or ".", exist_ok=True)

    if template_path and os.path.isfile(template_path):
        shutil.copyfile(template_path, config_path)
        log.append(f"Based on template {template_path}")
    elif template_path:
        context["abort"] = True
        return False, f"dosbox template conf not found: {template_path}"
    else:
        machine = resolve_path(machine or config.get("machine") or "svga_s3", vars_map)
        memsize = resolve_path(memsize or config.get("memsize") or 16, vars_map)
        with open(config_path, "w") as f:
            f.write(f"[dosbox]\nmachine={machine}\nmemsize={memsize}\n\n[autoexec]\n")
        log.append(f"Generated a minimal config (machine={machine}, memsize={memsize})")

    conf = DosboxConf(config_path)
    conf.disable_quit_warning()

    cpu_cycles = resolve_path(cpu_cycles, vars_map) if cpu_cycles else None
    if cpu_cycles:
        conf.section_insert("[cpu]", f"cycles={cpu_cycles}")
        log.append(f"  cpu: cycles={cpu_cycles}")

    lines = [resolve_path(ln, vars_map) for ln in _as_lines(autoexec)]
    if lines:
        # autoexec_insert always inserts directly after [autoexec], so inserting
        # in reverse leaves them in the order the testlist wrote them.
        for line in reversed(lines):
            conf.autoexec_insert(line)
        for line in lines:
            log.append(f"  autoexec: {line}")
    conf.save(config_path)

    log.append(f"Wrote {config_path}")
    log.append(f"ARTIFACT: {config_path}")
    return True, "\n".join(log)





@dispatchtest_step
def test_start_dosbox(name="dosbox1", config_path=None, display=None,
                      timeout=20, takeascreenshot=False, **kwargs):
    """Launch dosbox-x on the config test_dosbox_conf wrote and wait for its
    window.

    display is left unset by default
    """
    log = []
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    config_path = resolve_path(config_path, vars_map) or None
    display = resolve_path(display, vars_map) or None

    instance = DosboxInstance(name, config_path, display=display)
    log.append(f"Starting DOSBox-X '{name}' with config={config_path}")
    if not instance.start():
        log.append("Failed to start DOSBox-X.")
        log.extend(instance.stdout_lines[:10])
        context["abort"] = True
        return False, "\n".join(log)

    if not instance.wait_for_ready(timeout=int(timeout)):
        log.append(f"Timeout ({timeout}s) waiting for the DOSBox-X window.")
        log.extend(instance.stdout_lines[:10])
        instance.stop()
        context["abort"] = True
        return False, "\n".join(log)

    context[name] = instance
    log.append(f"{name} is ready on display {instance.display}")
    _maybe_screenshot(instance, takeascreenshot, log, label=name)
    return True, "\n".join(log)


@dispatchtest_step
def test_start_86box(name="box86_1", vm_path=None, vm_template=None,
                     takeascreenshot=False,
                     display=None, timeout=30, **kwargs):
    """Launch 86Box on a VM directory (its -P root: 86box.cfg, nvr/, images).
    """
    log = []
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    vm_path = resolve_path(vm_path, vars_map)
    vm_template = resolve_path(vm_template, vars_map) or None
    display = resolve_path(display, vars_map) or None
    if not vm_path:
        return False, "test_start_86box: vm_path is required"

    if vm_template:
        if not os.path.isdir(vm_template):
            context["abort"] = True
            return False, f"VM template directory not found: {vm_template}"
        if os.path.isdir(vm_path):
            shutil.rmtree(vm_path)
        shutil.copytree(vm_template, vm_path)
        log.append(f"Copied VM template {vm_template} -> {vm_path}")
    elif not os.path.isdir(vm_path):
        context["abort"] = True
        return False, f"VM directory not found: {vm_path}"

    instance = Box86Instance(name, vm_path, display=display)
    log.append(f"Starting 86Box '{name}' with -P {vm_path}")
    if not instance.start():
        log.append("Failed to start 86Box.")
        log.extend(instance.stdout_lines[:10])
        context["abort"] = True
        return False, "\n".join(log)

    if not instance.wait_for_ready(timeout=int(timeout)):
        log.append(f"Timeout ({timeout}s) waiting for the 86Box window.")
        log.extend(instance.stdout_lines[:10])
        instance.stop()
        context["abort"] = True
        return False, "\n".join(log)

    context[name] = instance
    log.append(f"{name} is ready on display {instance.display}")
    _maybe_screenshot(instance, takeascreenshot, log, label=name)
    return True, "\n".join(log)


@dispatchtest_step
def test_sendcommand(cmd_text=None, special_keys=None, name=None, key_delay=None,
                     delay=0, takeascreenshot=False, **kwargs):
    """Type into a DOSBox-X / 86Box window 
    """
    log = []
    context = kwargs.get("context", {})
    instance, err = _gui_instance(context, name)
    if err:
        return False, err

    keys = _as_list(special_keys)
    kw = {"special_keys": keys or None}
    if key_delay not in (None, ""):
        kw["key_delay"] = int(key_delay)

    if not instance.send_command(cmd_text or None, **kw):
        # send_command returns False when the window never took focus
        context["abort"] = True
        return False, (f"[{instance.name}] could not send input — the window did not "
                       f"take focus (is another instance sharing display "
                       f"{instance.display}?)")

    if cmd_text:
        log.append(f"[{instance.name}] typed: {cmd_text}")
    if keys:
        log.append(f"[{instance.name}] sent keys: {' '.join(keys)}")

    if delay not in (None, "") and float(delay):
        time.sleep(float(delay))

    if _as_bool(takeascreenshot):
        ok, shot = instance.take_screenshot(test_step=_current_stepnum())
        log.append(f"[{instance.name}] screenshot: {shot}" if ok
                   else f"[{instance.name}] screenshot failed: {shot}")

    return True, "\n".join(log)


@dispatchtest_step
def test_fileexists(file_path=None, timeout=0, min_size=1, **kwargs):
    """Wait for a host file to exist and be at least min_size bytes.
    """
    log = []
    context = kwargs.get("context", {})
    config = kwargs.get("config", {})
    vars_map = build_vars(config)

    file_path = resolve_path(file_path, vars_map)
    if not file_path:
        return False, "test_fileexists: no file_path given"

    timeout, min_size = int(timeout), int(min_size)

    def big_enough():
        return os.path.isfile(file_path) and os.path.getsize(file_path) >= min_size

    deadline = time.time() + timeout
    dead = None
    while not big_enough() and time.time() < deadline:
        dead = _dead_gui_instance(context)
        if dead:
            break
        time.sleep(2)

    if not big_enough():
        context["abort"] = True
        if dead:
            log.append(f"[{dead}] exited (window closed?) before {file_path} appeared")
        if os.path.isfile(file_path):
            log.append(f"{file_path} is only {os.path.getsize(file_path)} bytes "
                       f"(wanted >= {min_size})")
        else:
            log.append(f"{file_path} does not exist"
                       + (f" after {timeout}s" if timeout else ""))
        return False, "\n".join(log)

    log.append(f"{file_path} exists ({os.path.getsize(file_path)} bytes)")
    log.append(f"ARTIFACT: {file_path}")
    return True, "\n".join(log)

@dispatchtest_step
def test_wait_for_seconds(seconds=1, reason=None, **kwargs):
    """clock pause
    """
    seconds = float(seconds)
    if seconds < 0:
        return False, f"test_wait_for_seconds: seconds must be >= 0, got {seconds}"
    time.sleep(seconds)
    return True, f"waited {seconds:g}s" + (f" ({reason})" if reason else "")

