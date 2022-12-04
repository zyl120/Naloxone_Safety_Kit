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
    expiration_date = QtCore.QDate().currentDate()
    while True:
        config.read("safety_kit.conf")
        old_expiration_date = expiration_date
        expiration_date = QtCore.QDate.fromString(config["naloxone_info"]["naloxone_expiration_date"])
        max_temp = int(config["naloxone_info"]["absolute_maximum_temperature"])
        #print(expiration_date.toString())
        with shared_array.get_lock():
            shared_array[13] = expiration_date.year()
            shared_array[14] = expiration_date.month()
            shared_array[15] = expiration_date.day()
            shared_array[18] = max_temp
            today = QtCore.QDate.currentDate()
            if(old_expiration_date != expiration_date and today < expiration_date):
                # when placed new naloxone, clear error flags
                shared_array[0] = False
                shared_array[9] = False
                shared_array[10] = False
                continue
            else:
                if(today > expiration_date):
                    print("INFO: naloxone expired")
                    shared_array[9] = True
                else:
                    shared_array[9] = False
                if (shared_array[0]):
                    # overheat
                    shared_array[10] = True
        sleep(5)


def fork_naloxone(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: naloxone_manager={}".format(pid))
    else:
        naloxone_pid = os.getpid()
        os.sched_setaffinity(naloxone_pid, {naloxone_pid % os.cpu_count()})
        print("naloxone" + str(naloxone_pid) + str(naloxone_pid % os.cpu_count()))
        signal.signal(signal.SIGINT, naloxone_signal_handler)
        naloxone_manager(shared_array)
    return pid
