from time import sleep
import signal
import os
import sys
import configparser
from PyQt5 import QtCore

def naloxone_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def naloxone_manager(shared_array):
    config = configparser.ConfigParser()
    config.read("safety_kit.conf")
    expiration_date = QtCore.QDate.fromString(config["naloxone_info"]["naloxone_expiration_date"])
    print(expiration_date.toString())
    while True:
        with shared_array.get_lock():
            shared_array[13] = expiration_date.year()
            shared_array[14] = expiration_date.month()
            shared_array[15] = expiration_date.day()
            today = QtCore.QDate.currentDate()
            if(today > expiration_date):
                print("INFO: naloxone expired")
                shared_array[9] = 1
            if (shared_array[0]):
                shared_array[10] = True
                shared_array[11] = max(2, shared_array[11])
                shared_array[12] = max(2, shared_array[12])
        sleep(600)


def fork_naloxone(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: naloxone_manager={}".format(pid))
    else:
        signal.signal(signal.SIGINT, naloxone_signal_handler)
        naloxone_manager(shared_array)
    return pid
