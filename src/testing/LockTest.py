import RPi.GPIO as GPIO
import time

# GPIO pin connected to MOSFET gate
LOCK_PIN = 2  # GPIO 12, adjust if using another pin

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(LOCK_PIN, GPIO.OUT)

# Function to engage the lock
def engage_lock():
    GPIO.output(LOCK_PIN, GPIO.HIGH)  # Set the MOSFET gate to HIGH, engages the lock
    print("Lock disengaged")

# Function to disengage the lock
def disengage_lock():
    GPIO.output(LOCK_PIN, GPIO.LOW)  # Set the MOSFET gate to LOW, disengages the lock
    print("Lock engaged")

# Testing the lock in a loop
try:
    while True:
        engage_lock()
        time.sleep(2)  # Keep the lock engaged for 5 seconds
        disengage_lock()
        time.sleep(2)  # Keep the lock disengaged for 5 seconds
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO when the program is stopped
