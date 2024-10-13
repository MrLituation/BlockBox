import RPi.GPIO as GPIO
import time

DOOR_SENSOR_PIN = 16

GPIO.setmode(GPIO.BCM)
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN)

try:
    while True:
        sensor_value = GPIO.input(DOOR_SENSOR_PIN)
        print(f"Sensor Value: {sensor_value}")
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()



