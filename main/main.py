# This is the main function for the design project Internet-based Naloxone
# safety kit.

import os
from time import sleep
import psutil
from multiprocessing import shared_memory
import numpy as np
import RPi.GPIO as GPIO
import Adafruit_DHT as dht

DOOR_PIN = 17
DHT_PIN = 27

def phone_call(address, message, to_phone_number, loop, voice):
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
    return
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

def door_switch(shm_d):
    while True:
        switch_status = read_door_switch()
        if(not shm_d.buf[4]):
            shm_d.buf[4] = True
            shm_d.buf[5] = switch_status
            shm_d.buf[4] = False
        sleep(1)

def ping():
    hostname = "https://api.twilio.com"  # ping twilio directly
    response = os.system("ping -c 1 " + hostname)

    # and then check the response...
    if response == 0:
        #print(hostname, 'is up!')
        return True
    else:
        #print(hostname, 'is down!')
        return False

def server_connection(shm_c):
    while True:
        server_status = ping()
        if(not shm_c.buf[8]):
            shm_c.buf[8] = True # critical section for server status
            shm_c.buf[9] = server_status
            shm_c.buf[8] = False # critical section ends for server status
        sleep(3600)

# Read from the DHT22 temperature sensor connected to GPIO27.
def read_temperature_sensor():
    #humidity, temperature = dht.read_retry(dht.DHT22, DHT_PIN)
    #temperature = 20
    list1 = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
    temperature = random.choice(list1)
    return temperature

def calculate_pwm(temperature):
    #print("control pwm")
    list1 = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
    pwm = random.choice(list1)
    return pwm


def control_fan(pwm):
    return True
    #print("controling fan pwm")


def temperature_fan(shm_b):
    while True:
        temperature = read_temperature_sensor()
        pwm = calculate_pwm(temperature)
        control_fan(pwm)
        if(not shm_b.buf[0]):
            shm_b.buf[0] = True # critical section for temperature and pwm
            shm_b.buf[2] = temperature
            if(temperature >= 40):
                shm_b.buf[1] = True
            else:
                shm_b.buf[1] = False
            shm_b.buf[3] = pwm
            shm_b.buf[0] = False # critical section for temperature and pwm
        sleep(2)

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

def shared_memory_print(shm):
    buffer = shm.buf
    for i in range(12):
        print(buffer[i], end=" ")
    print("")

def process_monitoring(temperature_fan_pid, server_connection_pid, door_switch_pid):
    _, temperature_fan_exit_status = os.waitpid(
                    temperature_fan_pid, os.WNOHANG)
    #print("temp process died? " + str(temperature_fan_exit_status))
    if (temperature_fan_exit_status != 0):
        print("fork temperature fan process")
        temperature_fan_pid = fork_temperature(shm_a)

    _, server_connection_exit_status = os.waitpid(
                    server_connection_pid, os.WNOHANG)
    #print("server process died? " +
    #                  str(server_connection_exit_status))
    if (server_connection_exit_status != 0):
        print("fork server connection process")
        server_connection_pid = fork_server_connection(shm_a)

    _, door_switch_exit_status = os.waitpid(
                    door_switch_pid, os.WNOHANG)
    #print("server process died? " + str(door_switch_exit_status))
    if (door_switch_exit_status != 0):
        print("fork door switch process")
        door_switch_pid = fork_door_switch(shm_a)


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
                process_monitoring(temperature_fan_pid, server_connection_pid, door_switch_pid)
                shared_memory_print(shm_a)
