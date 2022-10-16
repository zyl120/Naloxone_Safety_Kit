import RPi.GPIO as GPIO


def is_door_closed(reedPin):
    if GPIO.input(reedPin):
        return True
    else:
        return False
