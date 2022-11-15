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
import tkinter as tk
from tkinter import ttk


import sv_ttk


DOOR_PIN = 17
DHT_PIN = 27
NUM_CHILD_PROCESSES = 4
main_pid = 0
gpio_pid = 0
call_pid = 0
network_pid = 0
gui_pid = 0
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

        os.kill(gui_pid, signal.SIGINT)
        os.waitpid(gui_pid, 0)
        print("INFO: other processes terminated")

        # close and unlike the shared memory
        shm_block.close()
        shm_block.unlink()
        print("INFO: shared memory destroyed")

        print("INFO: main process {} exited.".format(os.getpid()))
        sys.exit(0)
    elif (signum == signal.SIGUSR1):
        shm_block.buf[5] = True


def child_signal_handler(signum, frame):
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        shm_block.close()
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def write_twilio_file(sid, token, from_, to, address, message):
    if (len(sid) == 0 or len(token) == 0 or len(from_) == 0 or len(to) == 0 or len(address) == 0 or len(message) == 0):
        print("ERROR: empty field(s) detected.")
        return False
    print(sid, token, from_, to, address, message)
    with open("/home/pi/Naloxone_Safety_Kit/main/twilio.txt", "w") as file:
        file.write("{}\n{}\n{}\n{}\n{}\n{}\n0\nwoman".format(
            sid, token, address, message, from_, to))
        file.close()
    return True


def save_and_exit(sid, token, from_, to, address, message, window):
    result = write_twilio_file(sid, token, from_, to, address, message)
    if (result):
        window.destroy()


def enter_info():
    window = tk.Tk()
    sv_ttk.set_theme("dark")
    window.geometry("800x240")
    window.title("Internet-based Naloxone Safety Kit OOBE")
    sid = tk.StringVar()
    token = tk.StringVar()
    from_ = tk.StringVar()
    to = tk.StringVar()
    address = tk.StringVar()
    message = tk.StringVar()
    for i in range(6):
        window.rowconfigure(i, weight=1)
    for i in range(4):
        window.columnconfigure(i, weight=1)

    account_sid_label = ttk.Label(
        window, text="Twilio Account SID").grid(row=0, column=0, pady=2, padx=2)
    account_sid_entry = ttk.Entry(
        window, width=25, textvariable=sid).grid(row=0, column=1, pady=2, padx=2)

    account_token_label = ttk.Label(
        window, text="Twilio Account Token").grid(row=1, column=0, pady=2, padx=2)
    account_token_entry = ttk.Entry(
        window, width=25, show="*", textvariable=token).grid(row=1, column=1, pady=2, padx=2)

    from_phone_label = ttk.Label(
        window, text="From Phone Number").grid(row=2, column=0, pady=2, padx=2)
    from_phone_entry = ttk.Entry(
        window, width=25, textvariable=from_).grid(row=2, column=1, pady=2, padx=2)

    to_phone_label = ttk.Label(
        window, text="To Phone Number").grid(row=3, column=0, pady=2, padx=2)
    to_phone_entry = ttk.Entry(
        window, width=25, textvariable=to).grid(row=3, column=1, pady=2, padx=2)

    address_label = ttk.Label(window, text="Address").grid(
        row=4, column=0, pady=2, padx=2)
    address_entry = ttk.Entry(
        window, width=25, textvariable=address).grid(row=4, column=1, pady=2, padx=2)

    message_label = ttk.Label(window, text="Message").grid(
        row=5, column=0, pady=2, padx=2)
    message_textbox = ttk.Entry(
        window, width=25, textvariable=message).grid(row=5, column=1, pady=2, padx=2)

    save_changes_button = ttk.Button(window, text="Save Changes", command=lambda: write_twilio_file(sid.get(
    ), token.get(), from_.get(), to.get(), address.get(), message.get())).grid(row=5, column=2, pady=2, padx=2)
    save_changes_and_exit_button = ttk.Button(window, text="Save Changes and Exit", command=lambda: save_and_exit(sid.get(
    ), token.get(), from_.get(), to.get(), address.get(), message.get(), window)).grid(row=5, column=3, pady=2, padx=2)

    window.mainloop()


def oobe():
    try:
        file = open("/home/pi/Naloxone_Safety_Kit/main/twilio.txt", "r")
    except OSError:
        print("Missing file, enter OOBE")
        enter_info()
        sys.exit(0)
    with file:
        lines = file.read().splitlines()
        print("read {} lines".format(len(lines)))
        if (len(lines) != 8):
            enter_info()
        else:
            for line in lines:
                print(line)


def fork_oobe():
    pid = os.fork()
    if (pid > 0):
        os.waitpid(pid, 0)
    else:
        oobe()


def change_led(window, canvas, temperature_led, network_led, pwm_text, buffer):
    canvas.itemconfig(pwm_text, text="PWM: {}".format(buffer[3]))
    if (buffer[2] < 20):
        canvas.itemconfig(temperature_led, fill="blue")
    elif (buffer[2] > 20 and buffer[2] < 25):
        canvas.itemconfig(temperature_led, fill="green")
    elif (buffer[2] >= 25 and buffer[2] <= 40):
        canvas.itemconfig(temperature_led, fill="yellow")
    elif (buffer[2] > 40):
        canvas.itemconfig(temperature_led, fill="red")
    if (buffer[9]):
        canvas.itemconfig(network_led, fill="green")
    elif (not buffer[9]):
        canvas.itemconfig(network_led, fill="red")

    window.after(1000, change_led, window, canvas,
                 temperature_led, network_led, pwm_text, buffer)


def graphical_user_interface():
    buffer = shm_block.buf
    window = tk.Tk()
    window.title("Internet-based Naloxone Safety Kit")
    # Create 200x300 Canvas widget
    canvas = tk.Canvas(window, width=200, height=300, bg="black")
    canvas.pack()

    temperature_label = canvas.create_text(
        100, 40, text="TEMPERATURE", fill="white")
    temperature_led = canvas.create_oval(
        75, 50, 125, 100)  # Create a circle on the Canvas
    network_label = canvas.create_text(100, 140, text="NETWORK", fill="white")
    network_led = canvas.create_oval(75, 150, 125, 200)
    pwm_text = canvas.create_text(
        100, 210, text="PWM: {}".format(buffer[3]), fill="white")
    change_led(window, canvas, temperature_led, network_led, pwm_text, buffer)
    window.mainloop()


def fork_gui():
    pid = os.fork()
    if (pid > 0):
        print("INFO: gui_pid={}".format(pid))
    else:
        gui_pid = os.getpid()
        signal.signal(signal.SIGINT, child_signal_handler)
        graphical_user_interface()
    return pid


def make_phone_call():
    # read account_sid and auth_token from environment variables
    file = open("/home/pi/Naloxone_Safety_Kit/main/twilio.txt", "rt")
    account_sid = file.readline()
    auth_token = file.readline()
    address = file.readline()
    message = file.readline()
    from_phone_number = file.readline()
    to_phone_number = file.readline()
    loop = file.readline()
    voice = file.readline()
    file.close()

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
            from_=from_phone_number
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


def read_door_switch():
    if GPIO.input(DOOR_PIN):
        return True
    else:
        return False


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
            buffer[5] = read_door_switch()
            buffer[4] = False
        sleep(1)


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
        if (buffer[5] and not buffer[6]):
            buffer[6] = True
            print("INFO: phone placed")
            result = make_phone_call()
            buffer[7] = result
            buffer[6] = False
            sleep(10000)
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
    global gpio_pid, call_pid, network_pid, gui_pid
    if (pid != 0):
        print("ERROR: {} crashed, fork...".format(pid))
        if (pid == gpio_pid):
            gpio_pid = fork_gpio()
        elif (pid == call_pid):
            call_pid = fork_call()
        elif (pid == network_pid):
            network_pid = fork_network()
        elif (pid == gui_pid):
            gui_pid = fork_gui()


if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    main_pid = os.getpid()
    print("INFO: main_pid={}".format(os.getpid()))
    fork_oobe()
    shm_block = shared_memory.SharedMemory(create=True, size=12)
    gpio_pid = fork_gpio()
    call_pid = fork_call()
    network_pid = fork_network()
    gui_pid = fork_gui()
    signal.signal(signal.SIGINT, parent_signal_handler)
    signal.signal(signal.SIGUSR1, parent_signal_handler)

    buffer = shm_block.buf
    buffer[0] = False  # temperature mutex
    buffer[1] = False  # temperature above threshold
    buffer[2] = 20  # temperature reading
    buffer[3] = 0  # fan PWM
    buffer[4] = False  # door switch mutex
    buffer[5] = False  # door switch triggered
    buffer[6] = False  # phone status mutex
    buffer[7] = False  # phone placed?
    buffer[8] = False  # server status mutex
    buffer[9] = False  # server connection okay?
    buffer[10] = False  # audio synthesis mutex
    buffer[11] = False  # audio synthesis requested?
    while True:
        print_shared_memory()
        process_monitor()
        sleep(1)
