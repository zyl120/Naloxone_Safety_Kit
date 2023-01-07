# This is the main function for the design project Internet-based Naloxone
# safety kit.

import os
import sys
from time import sleep
from multiprocessing import shared_memory
import subprocess
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
import tkinter.font as font
from tkcalendar import Calendar
import datetime
import sv_ttk
from PIL import ImageTk, Image


DOOR_PIN = 17
DHT_PIN = 27
NUM_CHILD_PROCESSES = 4
main_pid = 0
gpio_pid = 0
call_pid = 0
network_pid = 0
alarm_pid = 0
naloxone_pid = 0
gui_pid = 0
shm_block = 0


def parent_signal_handler(signum, frame):
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    # Used as a single handler to close all child processes.
    if (signum == signal.SIGINT):
        os.kill(gpio_pid, signal.SIGINT)
        os.waitpid(gpio_pid, 0)

        os.kill(call_pid, signal.SIGINT)
        os.waitpid(call_pid, 0)

        os.kill(network_pid, signal.SIGINT)
        os.waitpid(network_pid, 0)

        os.kill(alarm_pid, signal.SIGINT)
        os.waitpid(alarm_pid, 0)

        os.kill(naloxone_pid, signal.SIGINT)
        os.waitpid(naloxone_pid, 0)

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
        shm_block.buf[5] = True  # write buffer[5]


def child_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        shm_block.close()
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def write_twilio_file(sid, token, from_, to, address, message):
    # write the twilio config file to the hard drive
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
        # window.quit()
        window.destroy()


def enter_info_window():
    touch_keyboard = subprocess.Popen(['matchbox-keyboard'])
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
    for i in range(4):
        window.rowconfigure(i, weight=1)
    for i in range(4):
        window.columnconfigure(i, weight=1)

    account_sid_label = ttk.Label(
        window, text="SID").grid(row=0, column=0)
    account_sid_entry = ttk.Entry(
        window, textvariable=sid).grid(row=0, column=1)

    account_token_label = ttk.Label(
        window, text="Token").grid(row=0, column=2)
    account_token_entry = ttk.Entry(
        window, show="*", textvariable=token).grid(row=0, column=3)

    from_phone_label = ttk.Label(
        window, text="From").grid(row=1, column=0)
    from_phone_entry = ttk.Entry(
        window, textvariable=from_).grid(row=1, column=1)

    to_phone_label = ttk.Label(
        window, text="To").grid(row=1, column=2)
    to_phone_entry = ttk.Entry(
        window, textvariable=to).grid(row=1, column=3)

    address_label = ttk.Label(window, text="Addr").grid(
        row=2, column=0)
    address_entry = ttk.Entry(
        window, textvariable=address).grid(row=2, column=1)

    message_label = ttk.Label(window, text="Msg").grid(
        row=2, column=2)
    message_textbox = ttk.Entry(
        window, textvariable=message).grid(row=2, column=3)

    save_changes_button = ttk.Button(window, text="Save Changes", command=lambda: write_twilio_file(sid.get(
    ), token.get(), from_.get(), to.get(), address.get(), message.get())).grid(row=3, column=0, columnspan=2)
    save_changes_and_exit_button = ttk.Button(window, text="Save & Exit", command=lambda: save_and_exit(sid.get(
    ), token.get(), from_.get(), to.get(), address.get(), message.get(), window)).grid(row=3, column=2, columnspan=2)

    window.mainloop()


def oobe():
    # the process to first read the twilio config file
    try:
        file = open("/home/pi/Naloxone_Safety_Kit/main/twilio.txt", "r")
    except OSError:
        print("Missing file, enter OOBE")
        enter_info_window()
    with file:
        lines = file.read().splitlines()
        print("read {} lines".format(len(lines)))
        if (len(lines) != 8):
            enter_info_window()
        else:
            for line in lines:
                print(line)
    sys.exit(0)


def fork_oobe():
    pid = os.fork()
    if (pid > 0):
        os.waitpid(pid, 0)
    else:
        oobe()


def create_information_strip(window):
    now = datetime.datetime.now()
    date_time_string = now.strftime("%b %d %-I:%M %p")
    canvas = tk.Canvas(window, width=800, height=25, bg="black")
    temperature_led = canvas.create_polygon(0, 0, 150, 0, 150, 25, 0, 25)
    temperature_label = canvas.create_text(
        75, 15, text="Temperature", fill="white", font=("Helvetica", "15"))

    network_led = canvas.create_polygon(150, 0, 300, 0, 300, 25, 150, 25)
    network_label = canvas.create_text(
        225, 15, text="Server", fill="white", font=("Helvetica", "15"))

    naloxone_led = canvas.create_polygon(300, 0, 450, 0, 450, 25, 300, 25)
    naloxone_label = canvas.create_text(
        375, 15, text="Naloxone", fill="white", font=("Helvetica", "15"))

    door_led = canvas.create_polygon(450, 0, 600, 0, 600, 25, 450, 25)
    door_label = canvas.create_text(
        525, 15, text="Door", fill="white", font=("Helvetica", "15"))

    date_time_label = canvas.create_text(
        720, 15, text=date_time_string, fill="white", font=("Helvetica", "15"))

    return canvas, temperature_led, temperature_label, naloxone_led, naloxone_label, network_led, network_label, door_led, door_label, date_time_label


def update_information_strip(window, buffer, canvas, temperature_led, temperature_label, network_led, network_label, naloxone_led, naloxone_label, door_led, door_label, date_time_label):
    if (buffer[2] < 20):
        canvas.itemconfig(temperature_led, fill="blue")
    elif (buffer[2] > 20 and buffer[2] < 25):
        canvas.itemconfig(temperature_led, fill="green")
    elif (buffer[2] >= 25 and buffer[2] <= 40):
        canvas.itemconfig(temperature_led, fill="green")
    elif (buffer[2] > 40):
        canvas.itemconfig(temperature_led, fill="red")
    if (buffer[9]):
        canvas.itemconfig(network_led, fill="green")
    elif (not buffer[9]):
        canvas.itemconfig(network_led, fill="red")
    if (buffer[15] or buffer[16]):
        canvas.itemconfig(naloxone_led, fill="red")
    else:
        canvas.itemconfig(naloxone_led, fill="green")
    if (buffer[5]):
        canvas.itemconfig(door_led, fill="red")
    else:
        canvas.itemconfig(door_led, fill="green")
    now = datetime.datetime.now()
    date_time_string = now.strftime("%b %d %-I:%M %p")
    canvas.itemconfig(date_time_label, text=date_time_string)
    window.after(1000, update_information_strip, window, buffer, canvas, temperature_led, temperature_label,
                 network_led, network_label, naloxone_led, naloxone_label, door_led, door_label, date_time_label)


def w_strip_status_code_to_string(status_code):
    if (status_code == 0):
        return "Naloxone Safety Kit"
    elif (status_code == 1):
        return "Naloxone Expired"
    elif (status_code == 2):
        return "Naloxone Overheat"
    return "invalid code"


def create_warning_strip(window, buffer):
    canvas = tk.Canvas(window, width=800, height=50, bg="black")
    text_to_display = w_strip_status_code_to_string(buffer[19])
    info_text = canvas.create_text(
        400, 30, text=text_to_display, fill="white", font=("Helvetica", "18"))
    if (buffer[18] == 0):
        canvas.configure(bg="black")
        info_text = canvas.create_text(
            400, 30, text=text_to_display, fill="white", font=("Helvetica", "18"))
    elif (buffer[18] == 1):
        canvas.configure(bg="black")
        info_text = canvas.create_text(
            400, 30, text=text_to_display, fill="red", font=("Helvetica", "18"))
    elif (buffer[18] == 2):
        canvas.configure(bg="red")
        info_text = canvas.create_text(
            400, 30, text=text_to_display, fill="white", font=("Helvetica", "18"))
    return canvas, info_text


def update_warning_strip(window, canvas, info_text, buffer):
    text_to_display = w_strip_status_code_to_string(buffer[19])
    if (buffer[18] == 0):
        canvas.config(bg="black")
        canvas.itemconfig(info_text, fill="white", text=text_to_display)
    elif (buffer[18] == 1):
        canvas.config(bg="black")
        canvas.itemconfig(info_text, fill="red", text=text_to_display)
    elif (buffer[18] == 2):
        canvas.config(bg="red")
        canvas.itemconfig(info_text, fill="white", text=text_to_display)
    window.after(1000, update_warning_strip, window, canvas,
                 info_text, buffer)


def wait_for_door_open(window, buffer):
    if (buffer[5]):
        shm_block.close()
        # window.quit()
        window.destroy()
    else:
        window.after(1000, wait_for_door_open, window, buffer)


def exit_door_open_window(window, buffer):
    if (buffer[5]):
        popup = tk.Toplevel()
        popup.geometry("240x240")
        s = ttk.Style()
        s.configure('.', font=('Helvetica', 20))
        popup.wm_title("Door Error!!!")
        label = ttk.Label(popup, text="Close the door first")
        label.pack()
        button = ttk.Button(popup, text="OK", command=lambda: popup.destroy())
        button.pack()
        popup.mainloop()
    else:
        shm_block.close()
        window.destroy()


def door_closed_window():
    buffer = shm_block.buf
    window = tk.Tk()
    sv_ttk.set_theme("dark")
    window.geometry("800x480")
    window.title("Internet-based Naloxone Safety Kit")
    text = "DO NOT USE NALOXONE, CALL +11234567890 FOR REPLACEMENT"
    warning_level = 2
    i_strip, temperature_led, temperature_label, naloxone_led, naloxone_label, network_led, network_label, door_led, door_label, date_time_label = create_information_strip(
        window)
    i_strip.pack(side=tk.TOP)

    img = Image.open(r"image.png")
    img = ImageTk.PhotoImage(img)
    label = ttk.Label(window, image=img)
    label.pack()
    w_strip, info_text = create_warning_strip(
        window, buffer)
    w_strip.pack(side=tk.BOTTOM)
    update_information_strip(window, buffer, i_strip, temperature_led, temperature_label, network_led,
                             network_label, naloxone_led, naloxone_label, door_led, door_label, date_time_label)
    update_warning_strip(window, w_strip, info_text, buffer)
    wait_for_door_open(window, buffer)
    window.mainloop()


def mute_alarm():
    buffer = shm_block.buf
    while True:
        if (not buffer[10]):
            buffer[10] = True
            buffer[11] = False  # reset the synthesis request
            buffer[10] = False
            break


def date_selector(date):
    print(date)


def door_open_window():
    buffer = shm_block.buf
    window = tk.Tk()
    sv_ttk.set_theme("dark")
    s = ttk.Style()
    s.configure('.', font=('Helvetica', 20))
    window.title("Emergency: Touch Enabled")
    window.geometry("800x480")
    for i in range(2):
        window.columnconfigure(i, weight=1, uniform="a")
    for i in range(1, 4):
        window.rowconfigure(i, weight=1, uniform="a")

    today = datetime.date.today()
    year = today.year
    month = today.month
    day = today.day

    info_strip, temperature_led, temperature_label, naloxone_led, naloxone_label, network_led, network_label, door_led, door_label, date_time_label = create_information_strip(
        window)
    info_strip.grid(row=0, column=0, columnspan=2)

    w_strip, info_text = create_warning_strip(window, buffer)
    w_strip.grid(row=4, column=0, columnspan=2)

    mute_alarm_button = ttk.Button(window, text="Mute Alarm", command=lambda: mute_alarm()).grid(
        row=1, column=0, padx=10, pady=10, sticky="nesw")
    set_naloxone_expire_date_button = ttk.Button(
        window, text="Set Expiry Date", command=lambda: date_selector(cal.get_date())).grid(row=2, column=0, padx=10, pady=10, sticky="nesw")
    cal = Calendar(window, font="11", selectmode="day", background="black", disabledbackground="black", bordercolor="black",
                   headersbackground="black", normalbackground="black", foreground="white",
                   normalforeground="white", headersforeground="white",
                   cursor="hand1", year=year, month=month, day=day)
    cal.grid(row=1, column=1, rowspan=3, sticky="nesw")
    reset_button = ttk.Button(window, text="Close Door & Reset", command=lambda: exit_door_open_window(window, buffer)).grid(
        row=3, column=0, padx=10, pady=10, sticky="nesw")
    update_information_strip(window, buffer, info_strip, temperature_led, temperature_label, network_led,
                             network_label, naloxone_led, naloxone_label, door_led, door_label, date_time_label)
    update_warning_strip(window, w_strip, info_text, buffer)
    window.mainloop()


def graphical_user_interface():
    buffer = shm_block.buf
    # door_closed_window()

    if (not buffer[5]):
        door_closed_window()
    else:
        door_open_window()


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


def gpio_manager():
    GPIO.setup(DOOR_PIN, GPIO.IN)
    buffer = shm_block.buf
    while True:
        if not buffer[0]:
            temp = read_temperature_sensor()
            pwm = calculate_pwm(temp)
            buffer[0] = True
            buffer[2] = temp  # write to buffer[2]
            # write to buffer[1]
            if (temp >= 40):
                buffer[1] = True
            else:
                buffer[1] = False
            # write buffer[3]
            buffer[3] = pwm
            control_fan(pwm)
            buffer[0] = False
        if not buffer[4]:
            # write buffer[4]
            buffer[4] = True
            buffer[5] = read_door_switch()  # write buffer[5]
            buffer[4] = False
        sleep(0.1)


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
        if (buffer[5] and not buffer[6]):  # read buffer[5]
            buffer[6] = True
            print("INFO: phone placed")
            #result = make_phone_call()
            result = True
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
        sleep(600)  # check for network connection every 10 minutes.


def fork_network():
    pid = os.fork()
    if (pid > 0):
        print("INFO: network_pid={}".format(pid))
    else:
        network_pid = os.getpid()
        signal.signal(signal.SIGINT, child_signal_handler)
        network_manager()
    return pid


def alarm_manager():
    buffer = shm_block.buf
    sleep(100000)
    # while (True):
    #     if (buffer[11]):
    #         # if we need a alarm, do now
    #         print("INFO: alarm played")
    #         # synthesize the alarm


def fork_alarm():
    pid = os.fork()
    if (pid > 0):
        print("INFO: alarm_synthesizer={}".format(pid))
    else:
        alarm_pid = os.getpid()
        signal.signal(signal.SIGINT, child_signal_handler)
        alarm_manager()
    return pid


def naloxone_manager():
    buffer = shm_block.buf
    while True:
        if (buffer[2] > 40):
            # overheat case
            while (buffer[14]):
                continue
            buffer[14] = True
            buffer[16] = True
            buffer[14] = False
            while (buffer[17]):
                continue
            buffer[17] = True
            buffer[18] = 2
            buffer[19] = 2
            buffer[17] = False
    sleep(100000)


def fork_naloxone():
    pid = os.fork()
    if (pid > 0):
        print("INFO: naloxone_manager={}".format(pid))
    else:
        naloxone_pid = os.getpid()
        signal.signal(signal.SIGINT, child_signal_handler)
        naloxone_manager()
    return pid


def print_shared_memory():
    buffer = shm_block.buf
    for i in range(20):
        print(str(buffer[i]), end=" ")
    print("")


def process_monitor():
    pid, status = os.waitpid(0, os.WNOHANG)
    global gpio_pid, call_pid, network_pid, alarm_pid, naloxone_pid, gui_pid
    if (pid != 0):
        print("ERROR: {} crashed, fork...".format(pid))
        if (pid == gpio_pid):
            gpio_pid = fork_gpio()
        elif (pid == call_pid):
            call_pid = fork_call()
        elif (pid == network_pid):
            network_pid = fork_network()
        elif (pid == alarm_pid):
            alarm_pid = fork_alarm()
        elif (pid == naloxone_pid):
            naloxone_pid = fork_naloxone()
        elif (pid == gui_pid):
            gui_pid = fork_gui()


if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    main_pid = os.getpid()
    print("INFO: main_pid={}".format(os.getpid()))
    fork_oobe()
    shm_block = shared_memory.SharedMemory(create=True, size=20)

    buffer = shm_block.buf
    # can only be written by GPIO process
    # read by all other processes
    buffer[0] = False  # temperature mutex
    buffer[1] = False  # temperature above threshold
    buffer[2] = 20  # temperature reading
    buffer[3] = 0  # fan PWM
    buffer[4] = False  # door switch mutex
    buffer[5] = False  # door switch triggered

    # can only be written by GPIO process
    # read by GUI and call processes
    buffer[6] = False  # phone request mutex
    buffer[7] = False  # phone request?

    # can only be written by network process
    # read by GUI and GPIO process
    buffer[8] = False  # server status mutex
    buffer[9] = False  # server connection okay?

    # can be written by GPIO process
    # read by audio synthesis process
    buffer[10] = False  # audio synthesis mutex
    buffer[11] = False  # audio synthesis requested?

    # can be written by GUI process
    # read by audio synthesis process to mute the alarm
    buffer[12] = False  # mute request mutex
    buffer[13] = False  # mute request?

    # can be written by naloxone process
    # can be read by GUI
    buffer[14] = False  # naloxone status locked?
    buffer[15] = False  # naloxone expired?
    buffer[16] = False  # naloxone overheat?

    # can be written by any process
    # can be read by GUI
    buffer[17] = False  # warning info locked?
    buffer[18] = 0  # warning level
    buffer[19] = 0  # warning information

    gpio_pid = fork_gpio()
    call_pid = fork_call()
    network_pid = fork_network()
    alarm_pid = fork_alarm()
    naloxone_pid = fork_naloxone()
    gui_pid = fork_gui()
    signal.signal(signal.SIGINT, parent_signal_handler)
    signal.signal(signal.SIGUSR1, parent_signal_handler)

    while True:
        print_shared_memory()
        process_monitor()
        sleep(0.5)