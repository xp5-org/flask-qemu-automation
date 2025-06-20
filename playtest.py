from helpers import register_playtest, load_snapshot
import time

@register_playtest("Test1 - playtest demo1")
def test1_playtestdummy(sock):
    stdout_lines = []
    log = []
    print("test1")

    # Load the snapshot by name
    load_snapshot(sock, "snap1")

    print("ran the snap load, sleeping for 15")
    time.sleep(15)
    # test code here, return (success, log_output)
    return True, "\n".join(log)