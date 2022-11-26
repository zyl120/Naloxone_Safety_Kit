import RPi.GPIO as GPIO
import Adafruit_DHT as dht
from time import sleep
import signal
import os
import sys
import random


DOOR_PIN = 17
DHT_PIN = 27


def gpio_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


# Read from the DHT22 temperature sensor connected to GPIO27.
def read_temperature_sensor():
    #humidity, temperature = dht.read_retry(dht.DHT22, DHT_PIN)
    #temperature = 20
    list1 = [5, 10, 15, 20, 25, 30, 35, 40]
    temperature = random.choice(list1)
    return temperature


def calculate_pwm(temperature):
    #print("control pwm")
    list1 = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65]
    pwm = random.choice(list1)
    return pwm


def control_fan(pwm):
    return True
    #print("controling fan pwm")


def read_door_switch():
    if GPIO.input(DOOR_PIN):
        return True
    else:
        return False


def gpio_manager(shared_array):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DOOR_PIN, GPIO.IN)
    while True:
        temp = read_temperature_sensor()
        pwm = calculate_pwm(temp)
        control_fan(pwm)
        door_status = read_door_switch()
        with shared_array.get_lock():
            shared_array[1] = temp
            if (temp > shared_array[18]):
                # once destroyed by overheat, never change it back.
                shared_array[0] = True
            shared_array[2] = pwm
            shared_array[3] = door_status
        sleep(3)


def fork_gpio(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: gpio_pid={}".format(pid))
    else:
        signal.signal(signal.SIGINT, gpio_signal_handler)
        gpio_manager(shared_array)
    return pid
