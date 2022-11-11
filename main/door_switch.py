import os
#import RPi.GPIO as GPIO
from time import sleep
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Say
from twilio.base.exceptions import TwilioRestException

DOOR_PIN = 17

def read_door_switch():
    # if GPIO.input(DOOR_PIN):
    #     return True
    # else:
    #     return False
    return False


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
