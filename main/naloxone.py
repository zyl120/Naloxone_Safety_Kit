from time import sleep
import signal
import os
import sys


def naloxone_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def naloxone_manager(shared_array):
    while True:
        with shared_array.get_lock():
            if (shared_array[0]):
                shared_array[10] = True
                shared_array[11] = max(2, shared_array[11])
                shared_array[12] = max(2, shared_array[12])
        sleep(10)


def fork_naloxone(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: naloxone_manager={}".format(pid))
    else:
        signal.signal(signal.SIGINT, naloxone_signal_handler)
        naloxone_manager(shared_array)
    return pid
