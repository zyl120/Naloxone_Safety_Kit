from tkinter import *
import os
import logging
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Say
from twilio.base.exceptions import TwilioRestException


def phone_call(address, message, to_phone_number, loop, voice):
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    resonse = VoiceResponse()
    resonse.say("Message: " + message + " Address: " +
                address, voice=voice, loop=loop)
    print(resonse)
    client = Client(account_sid, auth_token)
    try:
        call = client.calls.create(
            twiml=resonse,
            to=to_phone_number,
            from_='+18647138522'
        )
    except TwilioRestException as e:
        logging.error("Twilio Call: ERROR - {}".format(str(e)))
    else:
        logging.info("Twilio Call: Call ID: %s", call.sid)
    print(call.sid)


class phone_call_ui:
    def __init__(self, master):
        self.master = master
        master.title("Naloxone Safety Kit")

        self.label_1 = Label(master, text="Emergency Contact")
        self.label_1.pack()
        self.contact_textbox = Text(master, height=1, width=40)
        self.contact_textbox.pack()
        self.contact_textbox.insert("1.0", "+15189615258")

        self.label_2 = Label(master, text="Address")
        self.label_2.pack()
        self.address_textbox = Text(master, height=1, width=40)
        self.address_textbox.pack()
        self.address_textbox.insert("1.0", "115 Hoy Rd, Ithaca, NY 14850")

        self.label_3 = Label(master, text="Message")
        self.label_3.pack()
        self.message_textbox = Text(master, height=3, width=40)
        self.message_textbox.pack()
        self.message_textbox.insert("1.0", "Naloxone safety kit is opened.")

        self.voice = StringVar()
        self.voice.set("woman")
        self.voice1 = Radiobutton(
            root, text="Voice 1", variable=self.voice, value="woman")
        self.voice1.pack()

        self.voice2 = Radiobutton(
            root, text="Voice 2", variable=self.voice, value="man")
        self.voice2.pack()

        self.loop = Scale(master, from_=0, to=100, orient=HORIZONTAL)
        self.loop.pack()

        self.call_button = Button(
            master, text="Call", command=self.call_emergency)
        self.call_button.pack()

    def call_emergency(self):
        phone_call(self.address_textbox.get("1.0", "end-1c"), self.message_textbox.get("1.0", "end-1c"),
                   self.contact_textbox.get("1.0", "end-1c"), int(self.loop.get()), self.voice.get())


if __name__ == "__main__":
    root = Tk()
    my_gui = phone_call_ui(root)
    root.mainloop()
