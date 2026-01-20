import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #auto import /testsrc/mytests dir as modules
TESTSRC_BASEDIR = "/testsrc"                # root dir of git repo vice-specific test src
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"    # vicehelpers.py lives here

# make app helpers dir visible
if TESTSRC_HELPERDIR  not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR )

from apphelpers import register_buildtest, register_testfile
from dosboxhelpers import DosboxInstance
import time



register_testfile(
    id="Dosbox",
    types=["build"],
    system="dosbox",
    platform="MSDOS i386",
)(sys.modules[__name__])



instance_name = "dosbox1"  
projname = "dosboxtest"
archtype = 'i386'
src_dir = '/testsrc/sourcedir/' + projname
out_dir = src_dir + "/output"
config = src_dir + "/vice_nosound.cfg"
sourcecode_dir = src_dir + "/sourced"
src_dos_dir = "src"
config_file = 'dosbox1.conf'
config_path = src_dir + "/" +  config_file


@register_buildtest("Build 1 - Start Dosbox using class")
def test1_start_dosbox(context):
    log = []
    instance = DosboxInstance(instance_name, config_path)

    if not instance.start():
        success, msg = instance.collect_logs("reports/dosbox_stdout.log")
        log.append("Failed to start DOSBox-X.")
        log.append(msg)
        context["abort"] = True
        return False, "\n".join(log)

    if instance.wait_for_ready(timeout=10):
        context[instance_name] = instance
        log.append(f"Started {instance_name} with config={config_path}")
        log.append(f"{instance_name} is ready.")
        return True, "\n".join(log)
    else:
        log.append("Timeout waiting for DOSBox-X to initialize.")
        instance.stop()
        return False, "\n".join(log)


@register_buildtest("Build 2 - take screenshot")
def test2_bootdos(context):
    instance = context.get(instance_name)
    if not instance:
        return False, f"No Dosbox instance '{instance_name}' available in context"
    log = []

    
    # send something to console
    instance.send_command("dir", special_keys=["Return"])
    instance.send_command("hello")
    success = instance.take_screenshot(test_step=2)
    if not success:
        log.append(f"[{instance.name}] Screenshot failed ")
    else:
        log.append(f"[{instance.name}] Screenshot taken, ")

    log.append("Checked DOS prompt")

    return True, "\n".join(log)



@register_buildtest("Build 14 - terminate all")
def test14_stopall(context):
    log = []
    print("teardown")
    #time.sleep(1)

    instance = context.get(instance_name)
    log.append(f"Stopping {instance_name}")
    instance.stop()
    log.append(f"{instance_name} has exited.")
    if not log:
        log.append("No QEMU instances found to stop.")
    return True, "\n".join(log)
