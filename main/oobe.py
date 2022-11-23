import subprocess
import tkinter as tk
from tkinter import ttk
import sv_ttk
import os
import sys


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


def oobe_manager():
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
        oobe_manager()
