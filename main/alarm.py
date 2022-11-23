from time import sleep
import os
import sys
import signal


def alarm_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def alarm_manager(shared_array):
    alarm_needed = False
    mute = False
    while True:
        with shared_array.get_lock():
            alarm_needed = shared_array[7]
            mute = shared_array[8]
        if (alarm_needed and not mute):
            print("synthesizing")
            sleep(10)


def fork_alarm(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: alarm_synthesizer={}".format(pid))
    else:
        alarm_pid = os.getpid()
        signal.signal(signal.SIGINT, alarm_signal_handler)
        alarm_manager(shared_array)
    return pid
