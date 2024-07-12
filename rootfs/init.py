#!/usr/bin/python3
import json
import os
import signal
import subprocess
import sys
import time

exiting = False


def start():
    try:
        print("Loading debug info...")
        debug_hostname = os.getenv("PYCHARM_DEBUG_HOST")
        debug_port = os.getenv("PYCHARM_DEBUG_PORT")
        if debug_hostname != "" and debug_port != "":
            debuginfo = json.dumps({"host": debug_hostname, "port": int(debug_port)})
            with open("/.pycharm-debug", "w") as f:
                f.write(debuginfo)
            print("Wrote /.pycharm-debug.")
        else:
            print("No PyCharm debug info, skipping /.pycharm-debug. Please set PYCHARM_DEBUG_HOST and PYCHARM_DEBUG_PORT to enable remote debugging.")
    except Exception as e:
        print("Could not write /.pycharm-debug: " + str(e))

    result = subprocess.run(
        ["/usr/bin/omd", "start"]
    )
    if result.returncode != 0:
        raise Exception("OMD failed to start")


def stop():
    """
    This function stops all OMD sites.
    """
    global exiting
    if exiting:
        return
    exiting = True
    result = subprocess.run(
        ["/usr/bin/omd", "stop"]
    )
    if result.returncode != 0:
        raise Exception("OMD failed to stop")


def status() -> bool:
    """
    This function returns True if omd status returns true.
    """
    result = subprocess.run(
        ["/usr/bin/omd", "status"]
    )
    return result.returncode == 0


def signal_handler(signum, frame):
    stop()
    sys.exit(0)


def child_handler(signum, frame):
    os.waitpid(-1, 0)


if __name__ == "__main__":
    start()
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGCLD, child_handler)
    while True:
        if not status():
            stop()
            sys.exit(1)
        time.sleep(10)
