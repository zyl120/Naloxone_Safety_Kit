import Adafruit_DHT as dht
from time import sleep

DHT_PIN = 27

# Read from the DHT22 temperature sensor connected to GPIO27.
def read_temperature_sensor():
    humidity, temperature = dht.read_retry(dht.DHT22, DHT_PIN)
    # Print Temperature and Humidity on Shell window
    print('Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(t, h))
    #sleep(5)  # Wait 5 seconds and read again
    return temperature

def calculate_pwm(temperature):
    print("control pwm")


def control_fan(pwm):
    print("controling fan pwm")


def temperature_fan():
    temperature = read_temperature_sensor()
    pwm = calculate_pwm(temperature)
    control_fan(pwm)

if __name__ == '__main__':
    print("testing temperature and fan functions")
