import RPi.GPIO as GPIO
import Adafruit_DHT as dht
from time import sleep
import signal
import os
import sys
import random
from gpiozero import CPUTemperature


DOOR_PIN = 17

def gpio_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)

def read_door_switch():
    if GPIO.input(DOOR_PIN):
        return True
    else:
        return False


def gpio_manager(shared_array):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DOOR_PIN, GPIO.IN)
    while True:
        door_status = read_door_switch()
        with shared_array.get_lock():
            shared_array[3] = door_status
        sleep(0.5)


def fork_gpio(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: gpio_pid={}".format(pid))
    else:
        gpio_pid = os.getpid()
        os.sched_setaffinity(gpio_pid, {gpio_pid % os.cpu_count()})
        print("gpio" + str(gpio_pid) + str(gpio_pid % os.cpu_count()))
        signal.signal(signal.SIGINT, gpio_signal_handler)
        gpio_manager(shared_array)
    return pid
