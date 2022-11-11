# This is the main function for the design project Internet-based Naloxone
# safety kit.

import os
from time import sleep
import psutil
from temperature_fan import temperature_fan
from server_connection import server_connection
from door_switch import door_switch
from multiprocessing import shared_memory

temperature_fan_pid = 0


def fork_temperature(shm):
    pid = os.fork()
    if pid > 0:
        # this is the parent process
        print("temperature pid=" + str(pid))
    else:
        # this is the child process
        print("child pid=" + str(pid))
        shm_b = shared_memory.SharedMemory(
            shm.name)  # open the shared memory block
        temperature_fan(shm_b)
    return pid


def fork_server_connection(shm):
    pid = os.fork()
    if pid > 0:
        # this is the parent process
        print("server pid=" + str(pid))
    else:
        # this is the child process
        print("child pid=" + str(pid))
        shm_c = shared_memory.SharedMemory(shm.name)
        server_connection(shm_c)
    return pid


def fork_door_switch(shm):
    pid = os.fork()
    if pid > 0:
        # this is the parent process
        print("door switch pid=" + str(pid))
    else:
        # this is the child process
        print("child pid=" + str(pid))
        shm_d = shared_memory.SharedMemory(shm.name)
        door_switch(shm_d)
    return pid


if __name__ == "__main__":
    shm_a = shared_memory.SharedMemory(create=True, size=12)
    buffer = shm_a.buf
    buffer[0] = False
    buffer[1] = False
    buffer[2] = 20

    buffer[4] = False
    buffer[5] = False

    buffer[8] = False
    buffer[9] = False
    temperature_fan_pid = fork_temperature(shm_a)
    if (temperature_fan_pid > 0):
        # parent process
        server_connection_pid = fork_server_connection(shm_a)
        if (server_connection_pid > 0):
            door_switch_pid = fork_door_switch(shm_a)
            while True:
                _, temperature_fan_exit_status = os.waitpid(
                    temperature_fan_pid, os.WNOHANG)
                print("temp process died? " + str(temperature_fan_exit_status))
                if (temperature_fan_exit_status != 0):
                    print("fork temperature fan process")
                    temperature_fan_pid = fork_temperature(shm_a)

                _, server_connection_exit_status = os.waitpid(
                    server_connection_pid, os.WNOHANG)
                print("server process died? " +
                      str(server_connection_exit_status))
                if (server_connection_exit_status != 0):
                    print("fork server connection process")
                    server_connection_pid = fork_server_connection(shm_a)

                _, door_switch_exit_status = os.waitpid(
                    door_switch_pid, os.WNOHANG)
                print("server process died? " + str(door_switch_exit_status))
                if (door_switch_exit_status != 0):
                    print("fork door switch process")
                    door_switch_pid = fork_door_switch(shm_a)

                # read from the shared memory
                if (shm_a.buf[0] == False):
                    # critical section for temperature and pwm
                    shm_a.buf[0] == True
                    print("above or equals 40? " + str(shm_a.buf[1]))
                    print("temp: " + str(shm_a.buf[2]))
                    shm_a.buf[0] = False  # critical section ends
                if (shm_a.buf[4] == False):
                    shm_a.buf[4] == True  # critical section for door switch
                    print("door opened? " + str(shm_a.buf[5]))
                    shm_a.buf[4] = False  # critical section ends
                if (shm_a.buf[8] == False):
                    # critical section for server connection
                    shm_a.buf[8] = True
                    print("server ok? " + str(shm_a.buf[9]))
                    shm_a.buf[8] = False  # critical section ends
                sleep(3)
