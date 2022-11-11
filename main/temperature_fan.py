#import Adafruit_DHT as dht

from time import sleep
import random

DHT_PIN = 27

# Read from the DHT22 temperature sensor connected to GPIO27.
def read_temperature_sensor():
    #humidity, temperature = dht.read_retry(dht.DHT22, DHT_PIN)
    #temperature = 20
    list1 = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
    temperature = random.choice(list1)
    return temperature

def calculate_pwm(temperature):
    #print("control pwm")
    pwm = 0
    return pwm


def control_fan(pwm):
    return True
    #print("controling fan pwm")


def temperature_fan(shm_b):
    while True:
        temperature = read_temperature_sensor()
        pwm = calculate_pwm(temperature)
        control_fan(pwm)
        if(not shm_b.buf[0]):
            shm_b.buf[0] = True # critical section for temperature and pwm
            shm_b.buf[2] = temperature
            if(temperature >= 40):
                shm_b.buf[1] = True
            else:
                shm_b.buf[1] = False
            shm_b.buf[0] = False # critical section for temperature and pwm
        sleep(5)

if __name__ == '__main__':
    print("testing temperature and fan functions")
