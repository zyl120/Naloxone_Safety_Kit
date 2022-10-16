# This is the file for reed sensor reading

import RPi.GPIO as GPIO
import logging


def is_door_closed(reedPin):
    logging.info("poll sensor now!")
    if GPIO.input(reedPin):
        return True
    else:
        return False
