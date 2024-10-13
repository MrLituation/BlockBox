import RPi.GPIO as GPIO
import time

# PIR sensor is connected to GPIO 21
PIR_PIN = 21

# GPIO setup
GPIO.setmode(GPIO.BCM)  # Using BCM numbering
GPIO.setup(PIR_PIN, GPIO.IN)  # GPIO 21 as input pin for the PIR sensor

def test_pir_sensor():
    """Test the PIR sensor for motion detection."""
    print("Starting PIR sensor test. Waiting for motion...")
    
    try:
        while True:
            if GPIO.input(PIR_PIN):  # Motion detected
                print("Motion detected!")
            else:
                print("No motion")
            
            time.sleep(1)  # Check every 1 second 

    except KeyboardInterrupt:
        print("Test stopped by user")

    finally:
        GPIO.cleanup()  # Reset GPIO settings before exiting

# Run the test
test_pir_sensor()
