# This is the main function for the design project Internet-based Naloxone
# safety kit.

import os
import sys
from time import sleep
from multiprocessing import Array
import signal
from gui import fork_gui


main_pid = 0
gui_pid = 0


def parent_signal_handler(signum, frame):
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    # Used as a single handler to close all child processes.
    if (signum == signal.SIGINT):

        os.kill(gui_pid, signal.SIGINT)
        os.waitpid(gui_pid, 0)
        print("INFO: other processes terminated")

        print("INFO: main process {} exited.".format(os.getpid()))
        sys.exit(0)


def child_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def process_monitor():
    pid, status = os.waitpid(0, os.WNOHANG)
    global naloxone_pid, gui_pid
    if (pid != 0):
        print("ERROR: {} crashed, fork...".format(pid))
        if (pid == gui_pid):
            gui_pid = fork_gui()


if __name__ == "__main__":
    main_pid = os.getpid()
    print("INFO: main_pid={}".format(os.getpid()))
    gui_pid = fork_gui()
    signal.signal(signal.SIGINT, parent_signal_handler)

    while True:
        process_monitor()
        sleep(1)
