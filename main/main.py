# This is the main function for the design project Internet-based Naloxone
# safety kit.

import os
from time import sleep
import psutil
from temperature_fan import temperature_fan

temperature_fan_pid = 0


def fork_temperature():
    pid = os.fork()
    if pid > 0:
        # this is the parent process
        print("parent pid=" + str(pid))
    else:
        # this is the child process
        print("child pid=" + str(pid))
        temperature_fan()
    return pid


if __name__ == "__main__":
    temperature_fan_pid = fork_temperature()
    while True:
        _, temperature_fan_exit_status = os.waitpid(
            temperature_fan_pid, os.WNOHANG)
        print(temperature_fan_exit_status)
        if (temperature_fan_exit_status != 0):
            print("fork...")
            temperature_fan_pid = fork_temperature()
        sleep(3)
