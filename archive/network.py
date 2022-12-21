import os
import sys
from time import sleep
import signal
from PyQt5 import QtCore


def network_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def ping():
    hostname = "www.twilio.com"  # ping twilio directly
    response = os.system("ping -c 1 " + hostname)

    # and then check the response...
    if response == 0:
        return True
    else:
        return False


def network_manager(shared_array):
    while True:
        server_status = ping()
        currentTime = QtCore.QTime().currentTime()
        with shared_array.get_lock():
            shared_array[6] = server_status
            shared_array[16] = currentTime.hour()
            shared_array[17] = currentTime.minute()
        sleep(600)  # check for network connection every 10 minutes.


def fork_network(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: network_pid={}".format(pid))
    else:
        network_pid = os.getpid()
        os.sched_setaffinity(network_pid, {network_pid % os.cpu_count()})
        print("network" + str(network_pid) + str(network_pid % os.cpu_count()))
        signal.signal(signal.SIGINT, network_signal_handler)
        network_manager(shared_array)
    return pid
