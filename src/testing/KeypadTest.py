import RPi.GPIO as GPIO
import time

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)

# Rows (connected to GPIO pins)
row_pins = [17, 27, 22, 10]  # GPIOs 17, 27, 22, 10 for rows (R1, R2, R3, R4)

# columns (connected to GPIO pins)
col_pins = [9, 11, 13, 19]  # GPIOs 9, 11, 13, 19 for columns (C1, C2, C3, C4)

# Define the key layout
keys = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"]
]

# Set up rows as output pins
for row in row_pins:
    GPIO.setup(row, GPIO.OUT)
    GPIO.output(row, GPIO.LOW)

# Set up columns as inputs with pull-down resistors
for col in col_pins:
    GPIO.setup(col, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Function to detect key presses
def get_key():
    for row_num, row_pin in enumerate(row_pins):
        # Set the current row high
        GPIO.output(row_pin, GPIO.HIGH)

        # Check each column to see if a key is pressed
        for col_num, col_pin in enumerate(col_pins):
            if GPIO.input(col_pin) == GPIO.HIGH:
                # Key is pressed, print the corresponding key
                print(f"Key pressed: {keys[row_num][col_num]}")
                while GPIO.input(col_pin) == GPIO.HIGH:
                    time.sleep(0.1)  # Wait until key is released

        # Resetting the current row to LOW again
        GPIO.output(row_pin, GPIO.LOW)

# Main loop to continuously check for key presses
try:
    while True:
        get_key()
        time.sleep(0.1)  # delay to control pressed key scanning speed
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on exit
