# This is the main function for the design project Internet-based Naloxone
# safety kit.

import os
import sys
from time import sleep
from multiprocessing import Array
import signal
from network import fork_network
from naloxone import fork_naloxone
from gpio import fork_gpio
from gui import fork_gui


main_pid = 0
gpio_pid = 0
network_pid = 0
naloxone_pid = 0
gui_pid = 0


def parent_signal_handler(signum, frame):
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    # Used as a single handler to close all child processes.
    if (signum == signal.SIGINT):
        os.kill(gpio_pid, signal.SIGINT)
        os.waitpid(gpio_pid, 0)

        os.kill(network_pid, signal.SIGINT)
        os.waitpid(network_pid, 0)

        os.kill(naloxone_pid, signal.SIGINT)
        os.waitpid(naloxone_pid, 0)

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


def print_shared_memory(shared_array):
    with shared_array.get_lock():
        for i in range(19):
            print(shared_array[i], end=" ")
        print("")


def process_monitor(shared_array):
    pid, status = os.waitpid(0, os.WNOHANG)
    global gpio_pid, network_pid, naloxone_pid, gui_pid
    if (pid != 0):
        print("ERROR: {} crashed, fork...".format(pid))
        if (pid == gpio_pid):
            gpio_pid = fork_gpio(shared_array)
        elif (pid == network_pid):
            network_pid = fork_network(shared_array)
        elif (pid == naloxone_pid):
            naloxone_pid = fork_naloxone(shared_array)
        elif (pid == gui_pid):
            gui_pid = fork_gui(shared_array)


if __name__ == "__main__":
    main_pid = os.getpid()
    print("INFO: main_pid={}".format(os.getpid()))
    shared_array = Array("i", (0, 20, 20, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2000, 1, 20, 0, 0, 40, 0))
    gpio_pid = fork_gpio(shared_array)
    network_pid = fork_network(shared_array)
    naloxone_pid = fork_naloxone(shared_array)
    gui_pid = fork_gui(shared_array)
    signal.signal(signal.SIGINT, parent_signal_handler)

    while True:
        #print_shared_memory(shared_array)
        process_monitor(shared_array)
        sleep(1)
