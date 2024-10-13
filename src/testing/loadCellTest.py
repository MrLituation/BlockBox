import time
import RPi.GPIO as GPIO
from hx711 import HX711

# Define GPIO pins for DT and SCK
DT_PIN = 5  # Connect DT to GPIO 5
SCK_PIN = 6  # Connect SCK to GPIO 6

# Initialize HX711
hx711 = HX711(DT_PIN, SCK_PIN)

# Set reference unit (calibration factor, adjust this value after calibration)
hx711.set_reference_unit(-21263) 

# Reset and tare the scale (this zeroes the scale)
hx711.reset()
hx711.tare()

if hx711.is_ready():
    print("ready")
else:
    print("not ready")

# Function to read weight from the load cell
def read_weight():
    # Read the weight and return the average of 5 readings for accuracy
    weight = hx711.get_weight(5)
    hx711.power_down()
    hx711.power_up()
    return weight

# Continuously read and print the weight from the load cell
try:
    while True:
        weight = read_weight()
        print(f"Weight: {weight} grams")
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
