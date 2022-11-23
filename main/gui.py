import datetime
import tkinter as tk
from tkinter import ttk
import sv_ttk
from PIL import ImageTk, Image
from tkcalendar import Calendar
import signal
import os
import sys


def gui_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def create_information_strip(window):
    now = datetime.datetime.now()
    date_time_string = now.strftime("%b %d %-I:%M %p")
    canvas = tk.Canvas(window, width=800, height=25, bg="black")
    temperature_led = canvas.create_polygon(0, 0, 120, 0, 120, 25, 0, 25)
    temperature_label = canvas.create_text(
        60, 15, text="Temperature", fill="white", font=("Helvetica", "14"))

    network_led = canvas.create_polygon(120, 0, 240, 0, 240, 25, 120, 25)
    network_label = canvas.create_text(
        180, 15, text="Server", fill="white", font=("Helvetica", "14"))

    naloxone_led = canvas.create_polygon(240, 0, 360, 0, 360, 25, 240, 25)
    naloxone_label = canvas.create_text(
        300, 15, text="Naloxone", fill="white", font=("Helvetica", "14"))

    door_led = canvas.create_polygon(360, 0, 480, 0, 480, 25, 360, 25)
    door_label = canvas.create_text(
        420, 15, text="Door", fill="white", font=("Helvetica", "14"))

    phone_led = canvas.create_polygon(480, 0, 600, 0, 600, 25, 480, 25)
    phone_label = canvas.create_text(
        540, 15, text="Phone", fill="white", font=("Helvetica", "14"))

    date_time_label = canvas.create_text(
        720, 15, text=date_time_string, fill="white", font=("Helvetica", "14"))

    return canvas, temperature_led, temperature_label, naloxone_led, naloxone_label, network_led, network_label, door_led, door_label, phone_led, phone_label, date_time_label


def update_information_strip(window, shared_array, canvas, temperature_led, temperature_label, network_led, network_label, naloxone_led, naloxone_label, door_led, door_label, phone_led, phone_label,  date_time_label):
    temperature = 20
    server = True
    naloxone_expired = False
    naloxone_overheat = False
    door = True
    phone = 2
    with shared_array.get_lock():
        temperature = shared_array[1]
        server = shared_array[6]
        naloxone_expired = shared_array[9]
        naloxone_overheat = shared_array[10]
        door = shared_array[3]
        phone = shared_array[5]

    if (temperature < 20):
        canvas.itemconfig(temperature_led, fill="blue")
    elif (temperature >= 20 and temperature < 25):
        canvas.itemconfig(temperature_led, fill="green")
    elif (temperature >= 25 and temperature < 40):
        canvas.itemconfig(temperature_led, fill="green")
    elif (temperature > 40):
        canvas.itemconfig(temperature_led, fill="red")
    if (server):
        canvas.itemconfig(network_led, fill="green")
    elif (not server):
        canvas.itemconfig(network_led, fill="red")
    if (naloxone_expired or naloxone_overheat):
        canvas.itemconfig(naloxone_led, fill="red")
    else:
        canvas.itemconfig(naloxone_led, fill="green")
    if (door):
        canvas.itemconfig(door_led, fill="red")
    else:
        canvas.itemconfig(door_led, fill="green")
    if (phone == 0):
        canvas.itemconfig(phone_led, fill="red")
    elif (phone == 1):
        canvas.itemconfig(phone_led, fill="green")
    elif (phone == 2):
        canvas.itemconfig(phone_label, fill="black")
        canvas.itemconfig(phone_led, fill="black")
    now = datetime.datetime.now()
    date_time_string = now.strftime("%b %d %-I:%M %p")
    canvas.itemconfig(date_time_label, text=date_time_string)
    window.after(1000, update_information_strip, window, shared_array, canvas, temperature_led, temperature_label,
                 network_led, network_label, naloxone_led, naloxone_label, door_led, door_label, phone_led, phone_label, date_time_label)


def w_strip_status_code_to_string(status_code):
    if (status_code == 0):
        return "Naloxone Safety Kit"
    elif (status_code == 1):
        return "Naloxone Expired"
    elif (status_code == 2):
        return "Naloxone Overheat"
    elif (status_code == 100):
        return "Placing Phone Call Now!!!"
    elif (status_code == 101):
        return "Countdown: 1 Second"
    elif (status_code == 102):
        return "Countdown: 2 Seconds"
    elif (status_code == 103):
        return "Countdown: 3 Seconds"
    elif (status_code == 104):
        return "Countdown: 4 Seconds"
    elif (status_code == 105):
        return "Countdown: 5 Seconds"
    elif (status_code == 106):
        return "Countdown: 6 Seconds"
    elif (status_code == 107):
        return "Countdown: 7 Seconds"
    elif (status_code == 108):
        return "Countdown: 8 Seconds"
    elif (status_code == 109):
        return "Countdown: 9 Seconds"
    elif (status_code == 110):
        return "Countdown: 10 Seconds"
    return "invalid code"


def create_warning_strip(window):
    canvas = tk.Canvas(window, width=800, height=50, bg="black")
    s = ttk.Style()
    s.configure("s2.TButton", font=('Helvetica', 12))
    info_bg = canvas.create_polygon(0, 0, 800, 0, 800, 50, 0, 50)
    warning_level = 0
    warning_code = 0
    # with shared_array.get_lock():
    #     warning_level = shared_array[11]
    #     warning_code = shared_array[12]
    text_to_display = w_strip_status_code_to_string(warning_code)
    info_text = canvas.create_text(
        400, 30, text=text_to_display, fill="white", font=("Helvetica", "20"))
    if (warning_level == 0):
        info_bg = canvas.create_polygon(
            0, 0, 800, 0, 800, 50, 0, 50, fill="black")
        info_text = canvas.create_text(
            400, 30, text=text_to_display, fill="white", font=("Helvetica", "20"))
    elif (warning_level == 1):
        info_bg = canvas.create_polygon(
            0, 0, 800, 0, 800, 50, 0, 50, fill="black")
        info_text = canvas.create_text(
            400, 30, text=text_to_display, fill="red", font=("Helvetica", "20"))
    elif (warning_level == 2):
        info_bg = canvas.create_polygon(
            0, 0, 800, 0, 800, 50, 0, 50, fill="red")
        info_text = canvas.create_text(
            400, 30, text=text_to_display, fill="white", font=("Helvetica", "20"))
    return canvas, info_text, info_bg


def update_warning_strip(window, canvas, info_text, info_bg, shared_array):
    warning_level = 0
    warning_code = 0
    with shared_array.get_lock():
        warning_level = shared_array[11]
        warning_code = shared_array[12]
    text_to_display = w_strip_status_code_to_string(warning_code)
    if (warning_level == 0):
        canvas.itemconfig(info_text, fill="white", text=text_to_display)
        canvas.itemconfig(info_bg, fill="black")
    elif (warning_level == 1):
        canvas.itemconfig(info_text, fill="red", text=text_to_display)
        canvas.itemconfig(info_bg, fill="black")
    elif (warning_level == 2):
        canvas.itemconfig(info_text, fill="white", text=text_to_display)
        canvas.itemconfig(info_bg, fill="red")
    canvas.tag_raise(info_bg)
    canvas.tag_raise(info_text)
    window.after(100, update_warning_strip, window, canvas,
                 info_text, info_bg, shared_array)


def wait_for_door_open(window, shared_array):
    door = False
    with shared_array.get_lock():
        door = shared_array[3]
    if (door):
        window.destroy()
    else:
        window.after(1000, wait_for_door_open, window, shared_array)


def exit_door_open_window(window, shared_array):
    door = False
    with shared_array.get_lock():
        door = shared_array[3]
    if (door):
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
        with shared_array.get_lock():
            shared_array[4] = False
            shared_array[5] = 2
            shared_array[7] = False
            shared_array[8] = False
            shared_array[11] = 0
            shared_array[12] = 0
        window.destroy()


def door_closed_window(shared_array):
    window = tk.Tk()
    sv_ttk.set_theme("dark")
    window.geometry("800x480")
    window.title("Internet-based Naloxone Safety Kit")
    i_strip, temperature_led, temperature_label, naloxone_led, naloxone_label, network_led, network_label, door_led, door_label, phone_led, phone_label, date_time_label = create_information_strip(
        window)
    i_strip.pack(side=tk.TOP)

    img = Image.open(r"image.png")
    img = ImageTk.PhotoImage(img)
    label = ttk.Label(window, image=img)
    label.pack()
    w_strip, info_text, info_bg = create_warning_strip(
        window)
    w_strip.pack(side=tk.BOTTOM)
    update_information_strip(window, shared_array, i_strip, temperature_led, temperature_label, network_led,
                             network_label, naloxone_led, naloxone_label, door_led, door_label, phone_led, phone_label, date_time_label)
    update_warning_strip(window, w_strip, info_text, info_bg, shared_array)
    wait_for_door_open(window, shared_array)
    window.mainloop()


def mute_alarm(shared_array):
    with shared_array.get_lock():
        shared_array[8] = True


def date_selector(date):
    print(date)


def door_open_window(shared_array):
    window = tk.Tk()
    sv_ttk.set_theme("dark")
    s = ttk.Style()
    s.configure("s1.TButton", font=('Helvetica', 24))
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

    info_strip, temperature_led, temperature_label, naloxone_led, naloxone_label, network_led, network_label, door_led, door_label, phone_led, phone_label, date_time_label = create_information_strip(
        window)
    info_strip.grid(row=0, column=0, columnspan=2)

    w_strip, info_text, info_bg = create_warning_strip(window)
    w_strip.grid(row=4, column=0, columnspan=2)

    mute_alarm_button = ttk.Button(window, text="Mute Alarm", style="s1.TButton", command=lambda: mute_alarm(shared_array)).grid(
        row=1, column=0, padx=10, pady=10, sticky="nesw")
    set_naloxone_expire_date_button = ttk.Button(
        window, text="Set Expiry Date", style="s1.TButton", command=lambda: date_selector(cal.get_date())).grid(row=2, column=0, padx=10, pady=10, sticky="nesw")
    cal = Calendar(window, font="11", selectmode="day", background="black", disabledbackground="black", bordercolor="black",
                   headersbackground="black", normalbackground="black", foreground="white",
                   normalforeground="white", headersforeground="white",
                   cursor="hand1", year=year, month=month, day=day)
    cal.grid(row=1, column=1, rowspan=3, sticky="nesw")
    reset_button = ttk.Button(window, text="Close Door & Reset", style="s1.TButton", command=lambda: exit_door_open_window(window, shared_array)).grid(
        row=3, column=0, padx=10, pady=10, sticky="nesw")
    update_information_strip(window, shared_array, info_strip, temperature_led, temperature_label, network_led,
                             network_label, naloxone_led, naloxone_label, door_led, door_label, phone_led, phone_label, date_time_label)
    update_warning_strip(window, w_strip, info_text, info_bg, shared_array)
    window.mainloop()


def update_countdown_window(window, shared_array, status_code):
    with shared_array.get_lock():
        shared_array[11] = 2
        shared_array[12] = status_code
        if (status_code == 100):
            shared_array[4] = True
            shared_array[8] = False
    if (status_code == 100):
        window.destroy()
    else:
        window.after(1000, update_countdown_window,
                     window, shared_array, status_code-1)


def count_down_window(shared_array):
    window = tk.Tk()
    sv_ttk.set_theme("dark")
    s = ttk.Style()
    s.configure("s1.TButton", font=('Helvetica', 24))
    window.title("Select an option")
    window.geometry("800x480")
    for i in range(2):
        window.columnconfigure(i, weight=1, uniform="a")
    for i in range(1, 3):
        window.rowconfigure(i, weight=1, uniform="a")

    info_strip, temperature_led, temperature_label, naloxone_led, naloxone_label, network_led, network_label, door_led, door_label, phone_led, phone_label, date_time_label = create_information_strip(
        window)
    info_strip.grid(row=0, column=0, columnspan=2)

    w_strip, info_text, info_bg = create_warning_strip(window)
    w_strip.grid(row=4, column=0, columnspan=2)

    stop_countdown_button = ttk.Button(window, style="s1.TButton", text="Stop\nCountdown").grid(
        row=1, column=0, padx=10, pady=10, sticky="nesw")
    help_button = ttk.Button(window, style="s1.TButton", text="Help").grid(
        row=1, column=1, padx=10, pady=10, sticky="nesw")
    set_expiry_date_button = ttk.Button(window, style="s1.TButton", text="Set\nExpiry Date").grid(
        row=2, column=0, padx=10, pady=10, sticky="nesw")

    update_countdown_window(window, shared_array, 110)

    update_information_strip(window, shared_array, info_strip, temperature_led, temperature_label, network_led,
                             network_label, naloxone_led, naloxone_label, door_led, door_label, phone_led, phone_label, date_time_label)
    update_warning_strip(window, w_strip, info_text, info_bg, shared_array)
    window.mainloop()


def gui_manager(shared_array):
    door_opened = 0
    status_code = 0
    while True:
        with shared_array.get_lock():
            door_opened = shared_array[3]
            status_code = shared_array[12]
        if (not door_opened):
            door_closed_window(shared_array)
            # door_closed_window(shared_array)
        elif (status_code != 100):
            count_down_window(shared_array)
        else:
            door_open_window(shared_array)


def fork_gui(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: gui_pid={}".format(pid))
    else:
        gui_pid = os.getpid()
        signal.signal(signal.SIGINT, gui_signal_handler)
        gui_manager(shared_array)
    return pid
