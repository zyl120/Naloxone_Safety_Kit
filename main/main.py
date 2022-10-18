# This is the main function for the Naloxone safety kit design project
#
# PIN 11-> reed door sensor
#

from call import phone_call
from reed_sensor import is_door_closed
from alarm import say_alarm
import RPi.GPIO as GPIO
import time
import logging
import sys
reedPin = 17
address = "115 Hoy Rd, Ithaca, NY 14850"
message = "safety kit is opened."
phone = "+15189615258"
loop = 10
voice = "woman"


if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(reedPin, GPIO.IN)  # Set the input pin for reed sensor

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    while True:
        time.sleep(1)  # poll the sensor every second
        status = is_door_closed(reedPin)
        logging.info("door closed: " + str(status))
        if (status):
            # if the door is closed, go back to the top of the loop
            continue
        else:
            reading_array = []  # used to record sensor readings in 10 seconds
            for i in range(100):
                status = is_door_closed(reedPin)
                logging.info("delay interval: " + str(i + 1) +
                             ", door closed: " + str(status))
                reading_array.append(status)
                time.sleep(0.1)
            closed_door_prob = sum(reading_array) / len(reading_array)
            # calculate the probability that the door is closed to avoid false alarm
            logging.info("closed door probability: " +
                         str(closed_door_prob * 100) + "%")
            if (closed_door_prob < 0.2):
                logging.info("attempt to call emergency")
                call_success = phone_call(address, message, phone, loop, voice)
                #call_success = False
                if call_success:
                    logging.info("phone call placed successfully")
                else:
                    # if phone call is not placed successfully, say the alarm instead
                    logging.warning(
                        "fail to make phone call, say alarm instead")
                    say_alarm(message, loop, voice)
                while (not is_door_closed(reedPin)):
                    # wait for the door to be closed
                    continue
