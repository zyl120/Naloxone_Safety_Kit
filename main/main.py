# This is the main function for the design project Internet-based Naloxone
# safety kit.

import os
import sys
from time import sleep
from multiprocessing import shared_memory
import RPi.GPIO as GPIO
import Adafruit_DHT as dht
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from twilio.base.exceptions import TwilioRestException
import logging
import random
import signal

DOOR_PIN = 17
DHT_PIN = 27
NUM_CHILD_PROCESSES = 3
main_pid = 0
gpio_pid = 0
call_pid = 0
network_pid = 0
shm_block = 0


def parent_signal_handler(signum, frame):
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        os.kill(gpio_pid, signal.SIGINT)
        os.waitpid(gpio_pid, 0)

        os.kill(call_pid, signal.SIGINT)
        os.waitpid(call_pid, 0)

        os.kill(network_pid, signal.SIGINT)
        os.waitpid(network_pid, 0)
        print("INFO: other processes terminated")

        # close and unlike the shared memory
        shm_block.close()
        shm_block.unlink()
        print("INFO: shared memory destroyed")

        print("INFO: main process {} exited.".format(os.getpid()))
        sys.exit(0)


def child_signal_handler(signum, frame):
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        shm_block.close()
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def make_phone_call(address, message, to_phone_number, loop, voice):
    # read account_sid and auth_token from environment variables
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]

    # create the response
    response = VoiceResponse()
    response.say("Message: " + message + " Address: " +
                 address, voice=voice, loop=loop)
    logging.info("resonse: " + str(response))

    # create client
    client = Client(account_sid, auth_token)
    print(response)

    # try to place the phone call
    try:
        call = client.calls.create(
            twiml=response,
            to=to_phone_number,
            from_='+18647138522'
        )
    except TwilioRestException as e:
        # if not successful, return False
        logging.error("Twilio Call: ERROR - {}".format(str(e)))
        return False
    else:
        # if successful, return True
        print(call.sid)
        logging.info("Twilio Call: Call ID: %s", call.sid)
        return True


def read_door_switch():
    if GPIO.input(DOOR_PIN):
        return True
    else:
        return False


def ping():
    hostname = "www.twilio.com"  # ping twilio directly
    response = os.system("ping -c 1 " + hostname)

    # and then check the response...
    if response == 0:
        #print(hostname, 'is up!')
        return True
    else:
        #print(hostname, 'is down!')
        return False


# Read from the DHT22 temperature sensor connected to GPIO27.
def read_temperature_sensor():
    #humidity, temperature = dht.read_retry(dht.DHT22, DHT_PIN)
    #temperature = 20
    list1 = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65]
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


def gpio_manager():
    GPIO.setup(DOOR_PIN, GPIO.IN)
    buffer = shm_block.buf
    while True:
        if not buffer[0]:
            temp = read_temperature_sensor()
            pwm = calculate_pwm(temp)
            buffer[0] = True
            buffer[2] = temp
            if (temp >= 40):
                buffer[1] = True
            else:
                buffer[1] = False
            buffer[3] = pwm
            control_fan(pwm)
            buffer[0] = False
        if not buffer[4]:
            buffer[4] = True
            buffer[5] = GPIO.input(DOOR_PIN)
            buffer[4] = False


def fork_gpio():
    pid = os.fork()
    if (pid > 0):
        print("INFO: gpio_pid={}".format(pid))
    else:
        gpio_pid = os.getpid()
        signal.signal(signal.SIGINT, child_signal_handler)
        gpio_manager()
    return pid


def call_manager():
    buffer = shm_block.buf
    while True:
        sleep(1)


def fork_call():
    pid = os.fork()
    if (pid > 0):
        print("INFO: call_pid={}".format(pid))
    else:
        call_pid = os.getpid()
        signal.signal(signal.SIGINT, child_signal_handler)
        call_manager()
    return pid


def network_manager():
    buffer = shm_block.buf
    while True:
        server_status = ping()
        if (not buffer[8]):
            buffer[8] = True  # critical section for server status
            buffer[9] = server_status
            buffer[8] = False  # critical section ends for server status
        sleep(3600)


def fork_network():
    pid = os.fork()
    if (pid > 0):
        print("INFO: network_pid={}".format(pid))
    else:
        network_pid = os.getpid()
        signal.signal(signal.SIGINT, child_signal_handler)
        network_manager()
    return pid


def print_shared_memory():
    buffer = shm_block.buf
    for i in range(12):
        print(buffer[i], end=" ")
    print("")


def process_monitor():
    pid, status = os.waitpid(0, os.WNOHANG)
    global gpio_pid, call_pid, network_pid
    if (pid != 0):
        print("ERROR: {} crashed, fork...".format(pid))
        if (pid == gpio_pid):
            gpio_pid = fork_gpio()
        elif (pid == call_pid):
            call_pid = fork_call()
        elif (pid == network_pid):
            network_pid = fork_network()


if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    main_pid = os.getpid()
    print("INFO: main_pid={}".format(os.getpid()))
    shm_block = shared_memory.SharedMemory(create=True, size=12)
    gpio_pid = fork_gpio()
    call_pid = fork_call()
    network_pid = fork_network()
    signal.signal(signal.SIGINT, parent_signal_handler)

    buffer = shm_block.buf
    buffer[0] = False
    buffer[1] = False
    buffer[2] = 20

    buffer[4] = False
    buffer[5] = False

    buffer[8] = False
    buffer[9] = False
    while True:
        print_shared_memory()
        process_monitor()
        sleep(1)
