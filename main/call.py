from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from twilio.base.exceptions import TwilioRestException
from time import sleep
import os
import sys
import signal
import configparser


def call_signal_handler(signum, frame):
    # close child processes
    print("INFO: {} received sig {}.".format(os.getpid(), signum))
    if (signum == signal.SIGINT):
        print("INFO: child process {} exited.".format(os.getpid()))
        sys.exit(0)


def make_phone_call():
    config = configparser.ConfigParser()
    config.read("safety_kit.conf")
    account_sid = config["twilio"]["twilio_sid"]
    auth_token = config["twilio"]["twilio_token"]
    address = config["emergency_info"]["emergency_address"]
    message = config["emergency_info"]["emergency_message"]
    from_phone_number = config["twilio"]["twilio_phone_number"]
    to_phone_number = config["emergency_info"]["emergency_phone_number"]
    loop = "0"
    voice = "woman"


    # create the response
    response = VoiceResponse()
    response.say("Message: " + message + " Address: " +
                 address, voice=voice, loop=loop)
    print("INFO: resonse: " + str(response))

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
        print("ERROR: Twilio Call: ERROR - {}".format(str(e)))
        return False
    else:
        # if successful, return True
        print(call.sid)
        print("ERROR: Twilio Call: Call ID: %s", call.sid)
        return True


def call_manager(shared_array):
    call_attempt = 0
    call_result = False
    while True:
        with shared_array.get_lock():
            call_result = shared_array[5]
            if (shared_array[4] and call_result != 1 and not shared_array[8] and call_attempt <= 3):
                call_attempt += 1
                print("INFO: phone call attempt {}".format(call_attempt))
                #result = make_phone_call()
                result = True
                shared_array[5] = result
                if (result):
                    shared_array[4] = False
                    call_attempt = 0
            elif (shared_array[4] and call_result == 0 and not shared_array[8] and call_attempt > 3):
                shared_array[4] = False
                shared_array[7] = True
                call_attempt = 0
        sleep(1)


def fork_call(shared_array):
    pid = os.fork()
    if (pid > 0):
        print("INFO: call_pid={}".format(pid))
    else:
        signal.signal(signal.SIGINT, call_signal_handler)
        call_manager(shared_array)
    return pid
