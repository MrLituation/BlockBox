
import time
import sys
from hx711 import HX711  

# GPIO pins based on setup
DOUT_PIN = 5  # Corresponding to HX711 DT
SCK_PIN = 6   # Corresponding to HX711 SCK

# instance of the HX711 class
scale = HX711(DOUT_PIN, SCK_PIN)

# value that changes as one calibrates
calibration_factor = -23700 

# Setup function
def setup():
    print("HX711 calibration for four load cells")
    print("Remove all weight from the scale")
    print("After readings begin, place known weight on scale")
    print("Press + or a to increase calibration factor")
    print("Press - or z to decrease calibration factor")
    
    # Initialize the scale
    scale.set_reference_unit(calibration_factor)
    scale.tare()  # Reset the scale to 0

    zero_factor = scale.read_average()  # Get a baseline reading
    print(f"Zero factor: {zero_factor}")

# Main loop function
def loop():
    global calibration_factor

    scale.set_reference_unit(calibration_factor)  # Adjust to this calibration factor

    # Read the value from the scale
    reading = scale.get_weight()

    print(f"Reading: {reading:.1f} kg")  # Display in kilograms
    print(f"Calibration factor: {calibration_factor}")

    # Adjust calibration factor via terminal input
    input_char = input("Press +/a or -/z")
    if input_char in ['+', 'a']:
       calibration_factor += 25
       print("Increased calibration factor")
    elif input_char in ['-', 'z']:
       calibration_factor -= 25
       print("Decreased calibration factor")

# Start the setup
setup()

# Run the main loop
try:
    while True:
        loop()
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
