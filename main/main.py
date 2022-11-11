# This is the main function for the design project Internet-based Naloxone
# safety kit. 

import os
from temperature_fan import temperature_fan

def fork_temperature():
    pid = os.fork()
    if pid > 0:
        # this is the parent process
        print("parent pid=" + str(pid))
    else:
        # this is the child process
        print("child pid=" + str(pid))


if __name__ == "__main__":
    fork_temperature()
