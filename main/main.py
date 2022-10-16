# This is the main function for the Naloxone safety kit design project
#
# PIN 11-> reed door sensor
#

from call import phone_call
from reed_sensor import is_door_closed
import RPi.GPIO as GPIO
import time
reedPin = 17
address = "115 Hoy Rd, Ithaca, NY 14850"
message = "Naloxone safety kit is opened."
phone = "+15189615258"
loop = 0
voice = "woman"


if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(reedPin, GPIO.IN)
    while True:
        time.sleep(1)
        status = is_door_closed(reedPin)
        print(status)
        if (status):
            # if the door is closed, go back to the top of the loop
            continue
        else:
            # time.sleep(10) # first wait for 10 second before calling
            reading_array = []
            for _ in range(100):
                status = is_door_closed(reedPin)
                print(status)
                reading_array.append(status)
                time.sleep(0.1)
            closed_door_prob = sum(reading_array) / len(reading_array)
            # calculate the probability that the door is closed to avoid false alarm
            print(closed_door_prob)
            if (closed_door_prob < 0.2):
                print("phone call placed")
                phone_call(address, message, phone, loop, voice)
                while (not is_door_closed(reedPin)):
                    continue
