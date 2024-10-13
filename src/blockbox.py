# Siyabonga Nhlapo
# Block Box is a locker system for a EEE4022S UCT design 

# Imports

# GUI and image handle python libraries
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# File format management
import json

# Functions for interacting with the operating system to be able to get 
# environment variables
import os

# Python library for OTP gen and verification
import pyotp

# Python library to be able to send message via Telegram bots
import telegram

# Library that allows user to be able to log system states and events. 
# Moreover, the RotatingFileHandler import ensures that the contents of
# the logged items do not grow indefinitely
import logging
from logging.handlers import RotatingFileHandler

# Import for functions that require timing
import time

# Weight sensor amplifier
from hx711 import HX711

# GPIO pin control
import RPi.GPIO as GPIO

# The threading python module enables project multitheading
from threading import Thread, Lock, Event

# Keypad control
import board
import digitalio
from adafruit_matrixkeypad import Matrix_Keypad

# Web server creation via flask, render_template for HTML file, Jsonify
# for JSON endpoint formatting, request for HTTP requests
from flask import Flask, render_template, jsonify, request

# Environment variable loading
from dotenv import load_dotenv

# For generating readable transaction IDs
import random
import string  

# Python blockchain integration (Ethereum Network) with Block Box.
from web3 import Web3
import web3

# HTTP requests to all general web servers and not necessarify flask 
# web servers. Not context-specific like flask request
import requests

# Loading environment variables from .env file which is in the same 
# directory as the project

load_dotenv()

# This is the URL that is taken from NGROK, note that this would have 
# to be changed every 8Hrs or so as NGROK's tunneling service expires, 
# otherwise a static URL would have to be incorporated
FLASK_API_URL = "https://e020-105-233-133-57.ngrok-free.app"

# CONSTANT DEFINITION
LOCK_PIN = 2 # Solenoid lock is GPIO pin 2
DOOR_SENSOR_PIN = 16 # Magnetic reed sensor is GPIO pin 16
DATA_PIN = 5 # Data pin (DT) of HX711 is connected to GPIO pin 5
SCK_PIN = 6 # Clock pin (SCL) of HX711 is connected to GPIO pin 6
KEYPAD_ROWS_PINS = [17, 27, 22, 10]
KEYPAD_COLS_PINS = [9, 11, 13, 19]
OTP_TIMEOUT = 600  # 10 minutes timeout(expiration time) for OTP
WEIGHT_TOLERANCE = 0.1  # 100 gram tolerance for weight sensor

logger = logging.getLogger("BlockBox") #Initialise BlockBox Log file
logger.setLevel(logging.INFO) #Only messages with an INFO level and 
# above will be logged so warnings and errors are included but debug 
# excluded 
handler = RotatingFileHandler("blockbox.log", maxBytes=5*1024*1024, 
backupCount=5) # 5MB max log file size. Note that 1MB = 1024KB and 
# 1KB = 1024 Bytes, this is a MB to Bytes conversion. Also note that 5 
# backup files are created.
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') #Timestamp - Logger name - level - log message 
handler.setFormatter(formatter) #All log messages are set to have 
# the above-mentioned format
logger.addHandler(handler) # Handler attached to BlockBox logs

# Telegram Handler Class
class TelegramHandler:
    def __init__(self, token, chat_id, role): # Handler to send
        # messages via telegram
        # token - Authentication token from telegram botFather
        # chat_id - Which chat is the bot sending messages to
        # role - String which reps role of the bot (Buyer or seller)
        self.token = token
        self.chat_id = chat_id
        self.role = role
        try:
            self.bot = telegram.Bot(token=self.token) 
            logger.info(f"{role.capitalize()} Telegram Bot initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize {role} Telegram Bot: {e}")
            raise # raise triggers an exception, however, when it is 
            # used without parameter/arguments it is used to re-raise a
            # previous exception and make sure the program does not
            # continue operating and silently ignore the exception at 
            # higher levels of the code.

    def send_message(self, message):
        try:
            self.bot.send_message(chat_id=self.chat_id, text=message)
            logger.info(f"{self.role.capitalize()} message sent successfully.")
        except Exception as e:
            logger.error(f"Error sending {self.role} message: {e}")
            with state_lock: # system_state is a shared resource that 
                # is multi-threaded, therefore, state_lock ensures that
                #only one thread can modify system_state at a time. 
                system_state['error_logs'].append(f"Error sending {self.role} message: {e}")
            raise # Raise again without argument -> re-raise

# Hardware Controller Class
class HardwareController:
    # This class concerns itself with the setup and operational 
    # controll of the hardware components (lock, door sensor, weight 
    # module) of the Block Box System.
    def __init__(self): #Initalisation of class upon instance creation
        GPIO.setmode(GPIO.BCM) # Broadcom numbering used for GPIO which
        # refers to the pin numbers of RPi
        self.setup_gpio() #Calling setup_gpio method below
        self.hx711 = HX711(DATA_PIN, SCK_PIN) # Initialisation of an
        # an instance of the HX711 class'''
        self.hx711.set_reference_unit(-21263) # The reference unit
        # in the arguments of the set_reference_unit is one that found
        # when calibrating this system using known weight. This value 
        # is known as the calibration factor and ranges according to setup
        # of the scale.
        self.hx711.reset() # Scale reset to start with clean state
        self.hx711.tare() # Zeroing of load cell readings
        logger.info("Hardware Controller initialized.") #Logging

    def setup_gpio(self):
        try:
            GPIO.setup(LOCK_PIN, GPIO.OUT) # Lock GPIO pin configured 
            # as an output pin
            GPIO.output(LOCK_PIN, GPIO.HIGH) # The pin is initially
            # set to HIGH and a HIGH signal disengages the lock, 
            # therefore, lock is unlocked at startup

            GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)# Door MAG reed sensor GPIO pin  
            # configured as an input pin with the the internal pull-up
            # resistor active
            logger.info("GPIO pins for lock and door sensor set up successfully.") # Success log
        except Exception as e:
            logger.critical(f"Failed to set up lock and/or door GPIO pins: {e}") # Failure log
            raise # Re-raise

    def lock_door(self):
        try:
            GPIO.output(LOCK_PIN, GPIO.LOW)  # Lock engaged (locked)
            logger.info("The door is currently LOCKED.") # Success log
            update_system_state('door_status', 'Locked') # State change
        except Exception as e:
            logger.error(f"Error locking door: {e}")
            with state_lock: # Lock Thread event for single data append
                system_state['error_logs'].append(f"Error locking door: {e}")

    def unlock_door(self):
        try:
            GPIO.output(LOCK_PIN, GPIO.HIGH)# Lock disengaged (unlocked)
            logger.info("The door is currently UNLOCKED.")# Success log
            update_system_state('door_status', 'Unlocked')# State change
        except Exception as e:
            logger.error(f"Error unlocking door: {e}")
            with state_lock:# Lock Thread event for single data append
                system_state['error_logs'].append(f"Error unlocking door: {e}")

    def is_door_closed(self):
        try:
            return GPIO.input(DOOR_SENSOR_PIN) == GPIO.LOW # Boolean 
            # returned to check if the lock is engaged (locked state)
        except Exception as e:
            logger.error(f"Error reading door sensor: {e}")
            with state_lock:# Lock Thread event for single data append
                system_state['error_logs'].append(f"Error reading door sensor: {e}")
            return False

    def read_weight(self):
        try:
            weight = self.hx711.get_weight(5) # the weight value is an 
            # average of 5 measurements for better accuracy
            self.hx711.power_down() # Power down and power up of load
            # cells between readings to save power
            self.hx711.power_up()
            weight = max(weight, 0.0)  # Ensures that the weight value 
            # from the load cells cannot be negative.
            logger.debug(f"Actual weight: {weight:.2f} kg") # This line 
            # of code is only for development debug purposes and will 
            # only be logged if LEVEL changed from INFO to DEBUG
            return weight
        except Exception as e:
            logger.error(f"Error reading weight: {e}")
            with state_lock:
                system_state['error_logs'].append(f"Error reading weight: {e}")
            return 0.0 # Value of zero returned when there is an issue
            # reading the weight value

    def cleanup(self):
        try:
            GPIO.cleanup() # GPIO pins are taken back to default states
            logger.info("GPIO cleanup successful.")
        except Exception as e:
            logger.error(f"Error during GPIO cleanup: {e}")

# OTP Managerment Class
class OTPManager:
    def __init__(self, secret_key, valid_duration=OTP_TIMEOUT): 
        self.secret_key = secret_key # Key to synchronise the OTPs btw 
        # system and the user
        self.valid_duration = valid_duration # Time in seconds that OTP
        # is valid
        self.totp = pyotp.TOTP(self.secret_key, interval=self.valid_duration) # instance of pyotp.TOTP class 
        # that takes in a secret key and a time in seconds and makes an
        # OTP
        
        self.otp_creation_time = None # Showcases that no OTP created 
        # yet as there is no timestamp
        logger.info("OTPManager initialized.")

    def generate_otp(self):
        self.otp_creation_time = time.time() # Saving current time step
        # for OTP gen tracking
        otp = self.totp.now() # Collection of current OTP
        logger.info(f"OTP generated: {otp}")
        return otp

    def verify_otp(self, otp_entered): # Purpose of this method is to
        # cross check the user inputted OTP and the OTP of the system
        # to ensure that these two match.
        if self.is_otp_expired(): # expired OTP method below
            logger.warning("OTP verification failed: OTP expired.")
            return False # Verification unsuccessful if OTP had already
            # expired.
        result = self.totp.verify(otp_entered, valid_window=1)
        # verify() method checks whether system OTP from pyotp.TOTP is 
        # the same as entered otp allowing a small clock window of 1s 
        # in checking the validity
        logger.info(f"OTP verification result: {result}")
        return result

    def is_otp_expired(self): # This method checks if the OTP has
        # expired by checking the current time and subtracting the time
        # when the OTP was created and making sure that if that time is 
        # greater than the allowed validity time of the OTP then the OTP
        # has expired.
        if self.otp_creation_time is None:
            return True #The OTP is set as expired if it was never
            #created
        expired = ((time.time() - self.otp_creation_time) > 
        self.valid_duration)
        if expired:
            logger.info("OTP has expired.")
        return expired

# Flask Web Server Class 
class FlaskServer(Thread): # Thread class inheritance
    # This class is responsible for serving an HTML interface and a JSON
    # API which can then be used to integrate the system with a
    # Blockchain system. The server is ran in a separate thread.
    def __init__(self, app, host='0.0.0.0', port=5000):
        Thread.__init__(self) # Calling constructor of Thread class to 
        # initialise it properly
        self.daemon = True # daemon thread implies that server thread 
        # terminates when the programme terminates.
        self.app = app # Common flask application instance that defines 
        # the web server's behaviour
        self.host = host # 0.0.0.0 as host makes server accesible from
        # all network interfaces. Therefore, external devices can access
        # the system which is cruciaL!
        self.port = port # Port specification on where server runs

    def run(self):
        logger.info("Starting Flask web server.")
        self.app.run(host=self.host, port=self.port, debug=False, 
        use_reloader=False) #app.run() starts server when thread starts
        # debug turned off because function is used for development
        # purposes. Similarly with use_reloader as this is a development
        # tool that causes the flask server change in real-time with 
        # code-changes.


app = Flask(__name__) # Flask application instance creation

@app.route('/') # This is the root URL definition of the web server
def index():
    with state_lock: # thread-safe access to modify system state
        return render_template('index.html', system_state=system_state)
        # The current system_state is passed to the .html template in 
        # the templates folder which lies in the project directory. Note
        # that system_state is essentially a database carrying system 
        # information

@app.route('/system_state') # Route to an endpoint 
def get_system_state():
    #Provide the system state in JSON format.
    with state_lock:
        return jsonify(system_state) # State of the system converted to
        # JSON which is useful for APIs and/or blockchain based systems 
        # to fetch the data and be able to use it.

# Blockchain Integration
class BlockchainIntegration:
    def __init__(self):
        # Loading blockchain-related environment variables
        self.infura_url = os.getenv('INFURA_URL') # Using INFURA node 
        # provider to connect to Ethereum network.
        self.seller_address = os.getenv('SELLER_ADDRESS') # The seller 
        # is set as the system is not aiming to create a whole market-
        # place but only showcase the interaction of blockchain in the 
        # last-mile delivery process so using one set account for the 
        # seller is more than enough for the scope of the project.
        self.api_key = os.getenv('API_KEY') # API key is set in .env
        # file and it is a unique identifier that allows application to 
        # authenticate itself with an external service. In this case a
        # random key was generated and then fixed in .env file.

        # Validation check of the above variables
        if not all([self.infura_url, self.seller_address, self.api_key]):
            logger.critical("One or more essential blockchain environment variables are missing.")
            raise EnvironmentError("Missing blockchain configuration in environment variables.")

        # Initialisation of Web3
        self.web3 = Web3(Web3.HTTPProvider(self.infura_url))
        
        if not self.web3.is_connected():
            logger.critical("Web3 is not connected. Check infura URL.")
            raise ConnectionError("Failed to connect to Web3.")
        # If no errors occur then log good connection    
        logger.info("Connected to Ethereum blockchain via Infura.")

    def get_eth_price_usd(self):
        #Get current ETH/USD price using Chainlink.
        try:
            # Chainlink ETH/USD price feed contract address on Sepolia 
            # testnet
            price_feed_address = (Web3.to_checksum_address
            ('0x694AA1769357215DE4FAC081bf1f309aDC325306')) # Hardcoded
            # contract address for ETH/USD from Chainlink docs
            # ABI for the AggregatorV3Interface from Chainlink docs
            aggregator_abi = '[{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"description","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint80","name":"_roundId","type":"uint80"}],"name":"getRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"latestRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"version","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
            price_feed = self.web3.eth.contract(address=price_feed_address, abi=aggregator_abi)# Connection
            # to price feed data using contract address and abi
            
            # Pulling the latest real-time price feed
            latest_data = price_feed.functions.latestRoundData().call()
            
            # Getting the number of decimals that chainlink uses for
            # their price data to be used to divide in eth_price_usd 
            # for real value
            decimals = price_feed.functions.decimals().call()
            eth_price_usd = latest_data[1] / (10 ** decimals)
            logger.info(f"Fetched ETH/USD price: {eth_price_usd}")
            return eth_price_usd
        except Exception as e:
            logger.error(f"Failed to get ETH/USD price: {e}")
            raise

    def get_usd_zar_rate(self):
        #Get USD/ZAR exchange rate from an API.
        try:
            #Https get request to pull ZAR data from exchange rate API
            response = requests.get('https://api.exchangerate-api.com/v4/latest/ZAR') 
            rates = response.json()['rates'] # converting to python 
            # JSON dictionary and then searching for rates
            usd_per_zar = rates['USD']  # pulling USD/ZAR from rates
            return usd_per_zar
        except Exception as e:
            logger.error(f"Failed to get ZAR/USD exchange rate: {e}")
            raise

    def calculate_eth_amount(self, zar_amount):
        # Calculation of the amount of ETH needed for the user ZAR value.
        eth_price_usd = self.get_eth_price_usd() # Getting ETH/USD
        usd_zar_rate = self.get_usd_zar_rate() # Getting USD/ZAR
        usd_amount = zar_amount * usd_zar_rate  # Convert ZAR to USD 
        # because ZAR*USD/ZAR is just USD
        eth_amount = usd_amount / eth_price_usd # Eth = USD*ETH/USD
        return eth_amount

    def set_transaction(self, buyer_address, item_price_zar):
        # Verify buyer's balance against item price.
        try:
            # Using method defined above and taking zar to eth
            eth_amount = self.calculate_eth_amount(item_price_zar)
            # Taking eth to wei for more precise comparison
            wei_amount = self.web3.to_wei(eth_amount, 'ether')
            
            # Check buyer's balance
            buyer_balance = self.web3.eth.get_balance(buyer_address)
            
            if buyer_balance < wei_amount: # If inputed value (value of
                # the item being sold) is greater than the balance of
                # the buyer than return false as the buyer cannot take 
                # place in the transaction.
                return {
                    'success': False,
                    'message': f"Insufficient balance. Required: {eth_amount:.6f} ETH"
                }
            
            return {
                'success': True,
                'eth_amount': eth_amount,
                'wei_amount': wei_amount
            }
        except Exception as e:
            logger.error(f"Error in set_transaction: {e}")
            return {'success': False, 'message': str(e)}

    def trigger_payment(self, buyer_private_key, item_price_zar):
        #Execution of the Ethereum transaction from buyer to seller.
        try:
            buyer_account = self.web3.eth.account.from_key(buyer_private_key)
            # Using method defined above and taking zar to eth
            eth_amount = self.calculate_eth_amount(item_price_zar)
            # Taking eth to wei for more precise item amount
            wei_amount = self.web3.to_wei(eth_amount, 'ether')
            
            # Prepare transaction
            transaction = {
                'nonce': self.web3.eth.get_transaction_count
                (buyer_account.address, 'latest'), # the amount of 
                #transactions on the account
                'to': self.seller_address, # Where the money is going
                'value': int(wei_amount), # Money to be sent
                'gas': 25000,  # Gas limit for ETH transfer, 21000 
                # is the commonly used value but slightly increases here
                'gasPrice': self.web3.to_wei('1000', 'gwei'),
                # Market gasPrice average for funds transfer normally 
                # ranges from 400 Gwei in low demand and about 900 Gwei
                # in peak time, therefore, 1000 was selected to work 
                # well as of 06/10/2024 but this is expected to increase
                # as the testnet grows.
                'chainId': 11155111  # Sepolia testnet ID
            }
            
            # Sign transaction using the private key of the buyer
            signed_txn = self.web3.eth.account.sign_transaction(transaction, buyer_private_key)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1: # 1 means transaction sent
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'eth_amount': eth_amount
                }
            else:
                return {'success': False,'message': "Transaction failed on the blockchain."
}
        except Exception as e:
            logger.error(f"Error in trigger_payment: {e}")
            return {'success': False, 'message': str(e)}

# Flask App ENDPOINTS
@app.route('/set_transaction', methods=['POST']) # Endpoint accepting 
# POST requests
def set_transaction():
    # Expects JSON with 'buyer_address' and 'item_price_zar'.
    try:
        data = request.json # Extracting JSON data from incoming request
        buyer_address = data.get('buyer_address') # Get buyer_address
        # from incoming data 
        item_price_zar = float(data.get('item_price_zar', 0)) # Get item
        # price in ZAR from incoming data and make the price zero if not
        # listed

        if not buyer_address or item_price_zar <= 0:
            return jsonify({'success': False, 'message': "Invalid buyer address and/or price"}), 400 
                # 400 is Bad request status code which is returned as
                # as well as the JSON formatted response

        blockchain = BlockchainIntegration() # Initialising an instance
        # of the BlockchainIntegration class.
        
        #Checking if buyer has sufficient funds
        result = blockchain.set_transaction(buyer_address, item_price_zar)
        
        if result['success']: # Returns a JSON response indicating if 
            # the transaction setup is successful and the buyer has 
            # the funds, moreover, showing you how much ETH is needed
            return jsonify({'success': True,'eth_amount': result['eth_amount'],'message': f"Transaction prepared. Required ETH: {result['eth_amount']:.6f}"}), 200 # 200 status code means all is well
        else:
            return jsonify({'success': False, 'message': result['message']}), 400 # 400 is Bad request status code 
            # which is returned as well as the JSON formatted response

    except Exception as e:
        logger.exception(f"Exception in set_transaction endpoint: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
        # 500 status code means an internal server error so the Flask 
        # must be checked 

@app.route('/trigger_payment', methods=['POST']) # Endpoint accepting
# POST requests
def trigger_payment():
    # Endpoint to trigger payment upon item pickup and it expects JSON 
    # with 'buyer_private_key' and 'item_price_zar'.
    
    try:
        data = request.json # Extracting JSON data from incoming request
        buyer_private_key = data.get('buyer_private_key')  # Get Buyer 
        # private key from incoming data 
        item_price_zar = float(data.get('item_price_zar', 0))# Get item
        # price in ZAR from incoming data and make the price zero if not
        # listed

        if not buyer_private_key or item_price_zar <= 0:
            return jsonify({'success': False, 'message': "Invalid private key or price"}), 400
            # 400 is Bad request status code which is returned as
            # as well as the JSON formatted response

        blockchain = BlockchainIntegration() # Initialising an instance
        # of the BlockchainIntegration class.
        
        #Checking if buyer has sufficient funds
        result = blockchain.trigger_payment(buyer_private_key, item_price_zar)

        if result['success']:
            return jsonify({'success': True,'tx_hash': result['tx_hash'],'eth_amount': result['eth_amount'],'message': f"Payment successful! {result['eth_amount']:.6f} ETH sent."}), 200 # 200 status code means all is well
        else:
            return jsonify({'success': False, 'message': result['message']}), 400 # 400 is Bad request status code 
            # which is returned as well as the JSON formatted response

    except Exception as e:
        logger.exception(f"Exception in trigger_payment endpoint: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500 
        # 500 status code means an internal server error so the Flask 
        # must be checked 

# Global State
state_lock = Lock() # The threading lock ensuring multiple threads 
# do not work on trying to update the same shared resouse (system_state)
# at the same time.
# Lock() essentially allows only one thread at a time to access a
# coded section
system_state = { # The definition of the global dictionary that stores 
# the curremt state of the underlying Block Box system.
    'door_status': 'Unknown', # Door status tracking
    'item_status': 'No item placed', # Item tracking using weight 
    'item_collected': False, # Boolean flag on whether Buyer took item
    'item_price': None,
    'transaction_id': None, # Stores current custom Transaction ID
    'item_in_box': False, # Boolean version of item_status
    'error_logs': [], # Where all the system state error logs that keep  
     # being "appended" are saved.
    'transaction_active': False, # Boolean flag to show if there is an
    # ongoing transaction.
}

def update_system_state(key, value):
    # function that helps update the system state in a thread-safe way
    with state_lock: # the with keyword ensures that lock is engaged 
        # before entering the section where state is updated
        system_state[key] = value
        logger.debug(f"System state updated: {key} = {value}")
        
hardware = HardwareController() # Initialisation of Hardware Controller

# Environment Variables loading and validation
def load_env_variables():
    #Loading env variables for telegram bot mimicking buyer
    TELEGRAM_TOKEN = os.environ.get("BUYER_TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("BUYER_CHAT_ID")
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.critical("Buyer Telegram bot token and/or chat ID not set in environment variables.")
        raise EnvironmentError("Missing Telegram Buyer bot config data. Review code and environment variables.")
         
    #Loading env variables for telegram bot mimicking seller
    SELLER_TELEGRAM_TOKEN = os.environ.get("SELLER_TELEGRAM_TOKEN")
    
    #Buyer and seller bot chat ID is the same if simulated on same device
    SELLER_CHAT_ID = os.environ.get("SELLER_CHAT_ID")
    if not SELLER_TELEGRAM_TOKEN or not SELLER_CHAT_ID:
        logger.critical("Seller Telegram bot token or chat ID not set in environment variables.")
        raise EnvironmentError("Missing Telegram Seller bot config data. Review code and environment variables.")


    OTP_SECRET = os.environ.get("OTP_SECRET")
    if not OTP_SECRET:
        logger.critical("OTP_SECRET is not set in environment variables.")
        raise EnvironmentError("Missing OTP_SECRET configuration value.")

    return TELEGRAM_TOKEN, CHAT_ID, SELLER_TELEGRAM_TOKEN, SELLER_CHAT_ID, OTP_SECRET

try:
    TELEGRAM_TOKEN, CHAT_ID, SELLER_TELEGRAM_TOKEN, SELLER_CHAT_ID, OTP_SECRET = load_env_variables()
except EnvironmentError as e:
    logger.critical(f"Environment variable error: {e}")
    exit(1)

# Initialisation of Telegram Bot Handlers
buyer_bot_handler = TelegramHandler(TELEGRAM_TOKEN, CHAT_ID, "buyer")
seller_bot_handler = TelegramHandler(SELLER_TELEGRAM_TOKEN, SELLER_CHAT_ID, "seller")

# Initialisation of OTP Manager with OTP_SECRET for user/system 
# validation
otp_manager = OTPManager(OTP_SECRET)

# Initialisation of Flask Server
flask_server = FlaskServer(app)
flask_server.start() # Start server in separate thread

# System Monitor Function
def monitor_system(stop_event): #stop_event is an instance of Python's 
    # event class part of threading module.
    # Continuously monitor and update the global system state based
    # on any hardware changes.
    while not stop_event.is_set(): #Loop runs as long as stop_event is 
        # FALSE
        # Update door status
        door_closed = hardware.is_door_closed()
        update_system_state('door_status', 'Closed' if door_closed else 'Open')

        # Update item status based on weight
        weight = hardware.read_weight()
        if weight > 0.1: # Only items greater than 100g are detected
            update_system_state('item_status', 'Item placed')
            update_system_state('item_in_box', True)
        else:
            update_system_state('item_status', 'No item placed')
            update_system_state('item_in_box', False)

        time.sleep(1)  # 1 sec pause before checking the system again

# Event to stop the monitor thread
monitor_stop_event = Event()
# Function to run in monitor_system which takes the new event as argument
monitor_thread = Thread(target=monitor_system, args=(monitor_stop_event,))
monitor_thread.daemon = True # When system stops, event stops, monitor
# then also stops
monitor_thread.start() # Starting the monitoring in a different thread

# Initialisation of GUI using Tkinter 
class BlockBoxGUI:
    def __init__(self, root, hardware, buyer_bot, seller_bot, otp_manager):
        self.root = root # Main GUI window
        self.hardware = hardware # Hardware controller instance
        self.buyer_bot = buyer_bot # Telegram buyer bot
        self.seller_bot = seller_bot # Telegram seller bot
        self.otp_manager = otp_manager # Instance of the OTPManager class
        self.transaction_active = False # Start with no ongoing transaction
        self.item_in_box = False # Start with nothing in box
        self.buyer_private_key = None  # Store buyer's private key 
        # temporarily during transaction ONLY as sensitive infomation

        self.setup_gui() # Calling method below to set GUI framework up

    def setup_gui(self):
        # Set up the main (root) GUI components.
        self.root.title("BlockBox System")
        self.root.geometry("1280x800") # 1200 pixels wide and 800 high
        self.root.configure(bg="#f0f0f0") # light grey background

        # Load and set the main window icon
        try:
            icon = Image.open("BlockLogo1.png")
            icon_resized = icon.resize((32, 32), Image.ANTIALIAS)# image
            # of the icon resized to 32x32 to maintain quiality do
            main_icon_photo = ImageTk.PhotoImage(icon_resized) # Display
            # image 
            self.root.iconphoto(False, main_icon_photo) # Resized image
            # is the icon of the main window
        except Exception as e:
            logger.error(f"Error when loading main window icon: {e}")

        # Frames for different parts of the user interface
        # All set to light grey
        self.intro_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.seller_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.buyer_frame = tk.Frame(self.root, bg="#f0f0f0")

        # pack() is a layout manger function and in this case frames are
        # packed inside main frame and told to expand accordingly should 
        # the main frame be resized. 
        self.intro_frame.pack(fill="both", expand=1)
        self.seller_frame.pack(fill="both", expand=1)
        self.buyer_frame.pack(fill="both", expand=1)

        self.seller_frame.pack_forget() # Hide seller frame initially
        self.buyer_frame.pack_forget() # Hide buyer frame initially

        self.create_intro() # Create popup message as shown below

    def create_intro(self):
        # Creation of the introductory popup asking for user role.
        intro_popup = tk.Toplevel(self.root)
        intro_popup.title("Welcome to Block Box!")
        intro_popup.geometry("500x350")
        intro_popup.configure(bg="#f0f0f0")
        intro_popup.grab_set()  # Make the popup modal which means no 
        # user interaction with the main frame until this is closed

        # Load the BlockBox icon image
        try:
            icon = Image.open("BlockLogo1.png")
            icon_resized = icon.resize((32, 32), Image.ANTIALIAS)
            icon_photo_resized = ImageTk.PhotoImage(icon_resized)
            
            # Bigger version of same icon
            icon_large = icon.resize((100, 100), Image.ANTIALIAS)
            icon_photo_large = ImageTk.PhotoImage(icon_large)
        except Exception as e:
            logger.error(f"Error loading BlockBox icon: {e}")
            icon_photo_resized = None
            icon_photo_large = None

        # Display the icon in the popup
        if icon_photo_large: # Check to make sure image is not NONE
            image_label = tk.Label(intro_popup, image=icon_photo_large, 
            bg="#f0f0f0") # Label widget creation to display image
            image_label.image = icon_photo_large  # A line that seems
            # redundant but neccesary as it ensures the image always has
            # an additional reference in cases where it may only have 
            # been referenced in label creation
            
            # Positoning 
            image_label.grid(row=0, column=0, columnspan=2, pady=10)

        # Introductory Text
        tk.Label(intro_popup, text="Are you a SELLER or a BUYER?",font=("Helvetica", 16, "bold"), bg="#f0f0f0").grid(row=1,column=0, columnspan=2, pady=20)

        # Determination of button states based on system state
        transaction_active = system_state.get('transaction_active', False)
        item_in_box = system_state.get('item_in_box', False)
        
        # The buyer button is only enabled if there is an ongoing 
        # transaction and an item is in the box
        buyer_button_state = "normal" if transaction_active and item_in_box else "disabled"

        # Seller Button definition, on the left on buyer button under
        # intro text, lambda defines after click 
        tk.Button(intro_popup, text="Seller", width=20, height=2,command=lambda: [intro_popup.destroy(),self.open_seller()],bg="#4CAF50", fg="white", font=("Helvetica", 12,"bold")).grid(row=2, column=0, padx=20, pady=10)

        # Buyer Button definition, on the right on seller button under
        # intro text, lambda defines after click
        buyer_button = tk.Button(intro_popup, text="Buyer", width=20, height=2, state=buyer_button_state, command=lambda: [intro_popup.destroy(), self.open_buyer()],bg="#008CBA", fg="white", font=("Helvetica", 12, "bold"))
        buyer_button.grid(row=2, column=1, padx=20, pady=10)

        # Disabled Buyer Button Label
        if buyer_button_state == "disabled":
            if item_in_box: 
                tk.Label(intro_popup, text="An item is still in the box. Please take it out before starting a new transaction.",fg="red", bg="#f0f0f0", wraplength=480, justify="center").grid(row=3, column=0,columnspan=2, pady=5)
            else:
                tk.Label(intro_popup, text="Buyer option unavailable until seller lists an item.",fg="red", bg="#f0f0f0").grid(row=3, column=0, columnspan=2, pady=5)

    def open_seller(self):
        # Open the seller interface
        if system_state.get('item_in_box', False): # Checking if there
            # is an item in the box, looking for TRUE. The false in 
            # arg is just a default value incase of no set state.
            messagebox.showerror("Error", "An item is still in the box. Please take it out before starting a new transaction.")
            return
            
        #Proceeds here if no item in box
        self.intro_frame.pack_forget() # Hide intro page
        self.seller_frame.pack(fill="both", expand=1) 

        # Generate a new transaction ID
        transaction_id = self.generate_transaction_id()
        # Update states with new ID
        update_system_state('transaction_id', transaction_id)
        update_system_state('transaction_active', True)
        self.transaction_active = True
        
        self.save_seller_data()

        # Ensure door is closed before moving to seller form screen
        if not self.hardware.is_door_closed():
            messagebox.showinfo("Info", "Please close the door before proceeding.")
            self.wait_for_door_close()

        # Lock the door
        self.hardware.lock_door()
        messagebox.showinfo("Ready", "Door is now locked. Please enter the item details.")

        self.create_seller_form() # Show seller form as described in next
        # method below

    def create_seller_form(self):
        # Method responsible for dynamically creating a form where seller
        # can enter details about their item like a sales pitch 
        for widget in self.seller_frame.winfo_children():
            widget.destroy() # Seller frame cleared before form creation
            # This is particularly useful in cases where the frame comes 
            # opens up again for another transaction.

        # Configuration of grid rows and column weights
        self.seller_frame.grid_rowconfigure(6, weight=1)
        self.seller_frame.grid_columnconfigure(1, weight=1)

        # Item name label and entry field definition
        tk.Label(self.seller_frame, text="Item Name:", font=("Helvetica", 14), bg="#f0f0f0").grid(row=0, column=0, padx=20, pady=10, sticky='w')
        self.item_name_entry = tk.Entry(self.seller_frame, font=("Helvetica", 14))
        self.item_name_entry.grid(row=0, column=1, padx=20, pady=10, sticky='ew')

        # Description label and entry field definition 
        tk.Label(self.seller_frame, text="Description:", font=("Helvetica", 14), bg="#f0f0f0").grid(row=1, column=0, padx=20, pady=10, sticky='nw')
        self.description_entry = tk.Text(self.seller_frame, font=("Helvetica", 14), height=4)
        self.description_entry.grid(row=1, column=1, padx=20, pady=10, sticky='ew')

        # Advertised weight label and entry field definition
        tk.Label(self.seller_frame, text="Advertised Weight (kg):", font=("Helvetica", 14), bg="#f0f0f0").grid(row=2, column=0, padx=20, pady=10, sticky='w')
        self.advertised_weight_entry = tk.Entry(self.seller_frame, font=("Helvetica", 14))
        self.advertised_weight_entry.grid(row=2, column=1, padx=20, pady=10, sticky='ew')

        # Item price label and entry field definition
        tk.Label(self.seller_frame, text="Price (Rands):", font=("Helvetica", 14), bg="#f0f0f0").grid(row=3, column=0, padx=20, pady=10, sticky='w')
        self.item_price_entry = tk.Entry(self.seller_frame, font=("Helvetica", 14))
        self.item_price_entry.grid(row=3, column=1, padx=20, pady=10, sticky='ew')

        # Buyer Ethereum Address label and entry field definition
        tk.Label(self.seller_frame, text="Buyer Ethereum Address:", font=("Helvetica", 14), bg="#f0f0f0").grid(row=4, column=0, padx=20, pady=10, sticky='w')
        self.buyer_address_entry = tk.Entry(self.seller_frame, font=("Helvetica", 14))
        self.buyer_address_entry.grid(row=4, column=1, padx=20, pady=10, sticky='ew')

        # Upload Image Button definition
        tk.Button(self.seller_frame, text="Upload Image", command=self.upload_image, bg="#2196F3", fg="white",
                  font=("Helvetica", 12, "bold")).grid(row=5, column=0, padx=20, pady=10, sticky='w')

        # Image Display label definition
        self.img_label = tk.Label(self.seller_frame, bg="#f0f0f0")
        self.img_label.grid(row=5, column=1, padx=20, pady=10, sticky='w')

        # Submit Button definition
        tk.Button(self.seller_frame, text="Submit", command=self.submit_seller_data, bg="#4CAF50", fg="white",
                  font=("Helvetica", 14, "bold")).grid(row=6, column=0, columnspan=2, padx=20, pady=20, sticky='ew')

    def upload_image(self):
        # Option to upload image of item stored in memory
        file_path = filedialog.askopenfilename(title="Select Image", filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if file_path:
            system_state["image_path"] = file_path
            img = Image.open(file_path)
            img.thumbnail((200, 200))
            img = ImageTk.PhotoImage(img)
            self.img_label.config(image=img)
            self.img_label.image = img
            logger.info(f"Image uploaded: {file_path}")

    def submit_seller_data(self):
        #Submit seller data and proceed with the transaction
        item_name = self.item_name_entry.get()
        description = self.description_entry.get("1.0", tk.END).strip()
        advertised_weight = self.advertised_weight_entry.get()
        item_price = self.item_price_entry.get()
        buyer_address = self.buyer_address_entry.get().strip()  # Capture buyer's Ethereum address

        try: # Ensure that weight and price are numbers only
            advertised_weight = float(advertised_weight)
            item_price = float(item_price)
        except ValueError:
            messagebox.showerror("Error", "Please enter valid NUMBERS for weight and price.")
            return

        if advertised_weight <= 0 or item_price <= 0: #non-negative numbers
            messagebox.showerror("Error", "Item weight and price must be greater than 0.")
            return

        if item_name and description and "image_path" in system_state and buyer_address:
            system_state["item_name"] = item_name
            system_state["description"] = description
            system_state["advertised_weight"] = advertised_weight
            system_state["item_price"] = item_price
            system_state["buyer_address"] = buyer_address  # Set buyer address in system_state
            self.save_seller_data()

            # Unlock the door to allow the seller to place the item
            self.hardware.unlock_door()
            messagebox.showinfo("Info", "Please open the door and place the item inside.")
            self.wait_for_door_open()
            self.wait_for_item_placement()
            messagebox.showinfo("Info", "Item detected. Please close the door.")

            # Wait for seller to close the door
            self.wait_for_door_close()
            self.hardware.lock_door()
            update_system_state('item_status', 'Item placed')

            # Generate OTP and send messages
            otp = self.otp_manager.generate_otp()
            try:
                # Send buyer the transaction ID and item info via Flask API
                item_price_zar = system_state.get('item_price')

                # Call the Flask API to set the transaction on the blockchain
                response = requests.post(
                    f"{FLASK_API_URL}/set_transaction",
                    headers={'x-api-key': os.getenv('API_KEY')},
                    json={
                        'buyer_address': buyer_address,
                        'item_price_zar': item_price_zar
                    }
                )

                if response.status_code == 200:
                    logger.info("Transaction set successfully.")
                else:
                    logger.error(f"Failed to set transaction: {response.json().get('message')}")
                    messagebox.showerror("Error", f"Failed to set transaction: {response.json().get('message')}")
                    return

                # Send OTP via Telegram
                self.send_otp_via_telegram(otp)
                # Send seller a summary and transaction ID
                seller_summary = (
                    f"Transaction ID: {system_state['transaction_id']}\n"
                    f"Item: {system_state['item_name']}\n"
                    f"Description: {system_state['description']}\n"
                    f"Price: {system_state['item_price']} Rands\n"
                    f"The item is ready for collection."
                )
                self.seller_bot.send_message(seller_summary)
                messagebox.showinfo("Success", "Item data saved, transaction set, OTP sent to buyer, and notification sent to seller!")
                # Automatically transition to buyer interface
                self.open_buyer()
            except Exception as e:
                logger.error(f"Failed to send messages or interact with blockchain: {e}")
                messagebox.showerror("Error", f"Failed to send messages or interact with blockchain address: {e}")
        else:
            messagebox.showerror("Error", "Please fill in all fields, upload an image, and provide the buyer's Ethereum address.")

    def send_otp_via_telegram(self, otp):
        # Send OTP and item info to the buyer via Telegram
        message = (
            f"Transaction ID: {system_state['transaction_id']}\n"
            f"Item: {system_state['item_name']}\n"
            f"Description: {system_state['description']}\n"
            f"Price: {system_state['item_price']} Rands\n"
            f"Your OTP to retrieve the item is: {otp}\n"
            f"This OTP will expire in 10 minutes."
        )
        self.buyer_bot.send_message(message)

    def generate_transaction_id(self):
        # Generation of a short, readable transaction ID
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    def save_seller_data(self):
        # Save seller data to a JSON file
        with open("seller_data.json", "w") as file:
            json.dump(system_state, file)
        logger.info("Seller data saved to seller_data.json.")

    def wait_for_door_close(self):
        # Wait until the door is closed
        while not self.hardware.is_door_closed():
            time.sleep(0.1)
        update_system_state('door_status', 'Closed')
        logger.info("Door closed.")

    def wait_for_door_open(self):
        # Wait until the door is opened
        while self.hardware.is_door_closed():
            time.sleep(0.1)
        update_system_state('door_status', 'Open')
        logger.info("Door opened.")

    def wait_for_item_placement(self):
        # Wait until the item is placed on the scale
        while True:
            weight = self.hardware.read_weight()
            if weight > 0.1:
                update_system_state('item_status', 'Item placed')
                break
            time.sleep(0.5)
        logger.info("Item placed on the scale.")

    def open_buyer(self):
        # Open the buyer interface.
        transaction_active = system_state.get('transaction_active', False)
        item_in_box = system_state.get('item_in_box', False)

        if not (transaction_active and item_in_box):
            messagebox.showerror("Error", "No active transaction or item is not available. Please wait for the seller to list an item.")
            self.create_intro()
            return

        self.intro_frame.pack_forget()
        self.seller_frame.pack_forget()
        self.buyer_frame.pack(fill="both", expand=1)
        self.display_seller_data()

    def display_seller_data(self):
        # Display the seller's item data to the buyer
        # Clear existing widgets in buyer_frame
        for widget in self.buyer_frame.winfo_children():
            widget.destroy()

        # Configure grid weights
        self.buyer_frame.grid_rowconfigure(7, weight=1)
        self.buyer_frame.grid_columnconfigure(1, weight=1)

        # Image Display
        if "image_path" in system_state and os.path.exists(system_state["image_path"]):
            img = Image.open(system_state["image_path"])
            img.thumbnail((200, 200))
            img = ImageTk.PhotoImage(img)
            self.buyer_img_label = tk.Label(self.buyer_frame, image=img, bg="#f0f0f0")
            self.buyer_img_label.image = img
            self.buyer_img_label.grid(row=0, column=1, rowspan=5, padx=20, pady=10, sticky='e')
        else:
            self.buyer_img_label = tk.Label(self.buyer_frame, bg="#f0f0f0")
            self.buyer_img_label.grid(row=0, column=1, rowspan=5, padx=20, pady=10, sticky='e')

        # Item Details
        tk.Label(self.buyer_frame, text=f"Item Name: {system_state.get('item_name', 'N/A')}",
                 font=("Helvetica", 16), bg="#f0f0f0").grid(row=0, column=0, padx=20, pady=10, sticky='w')
        tk.Label(self.buyer_frame, text=f"Description: {system_state.get('description', 'N/A')}",
                 font=("Helvetica", 14), bg="#f0f0f0").grid(row=1, column=0, padx=20, pady=10, sticky='w')
        tk.Label(self.buyer_frame, text=f"Advertised Weight: {system_state.get('advertised_weight', 'N/A')} kg",
                 font=("Helvetica", 14), bg="#f0f0f0").grid(row=2, column=0, padx=20, pady=10, sticky='w')
        tk.Label(self.buyer_frame, text=f"Price: {system_state.get('item_price', 'N/A')} Rands",
                 font=("Helvetica", 14), bg="#f0f0f0").grid(row=3, column=0, padx=20, pady=10, sticky='w')
        tk.Label(self.buyer_frame, text=f"Transaction ID: {system_state.get('transaction_id', 'N/A')}",
                 font=("Helvetica", 14), bg="#f0f0f0").grid(row=4, column=0, padx=20, pady=10, sticky='w')

        # OTP Entry Instructions
        tk.Label(self.buyer_frame, text="Enter OTP using the keypad:", font=("Helvetica", 14, "bold"), bg="#f0f0f0").grid(row=5, column=0, padx=20, pady=10, sticky='w')

        # Ethereum Private Key ENTRY
        tk.Label(self.buyer_frame, text="Your Ethereum Private Key:", font=("Helvetica", 14), bg="#f0f0f0").grid(row=6, column=0, padx=20, pady=10, sticky='w')
        self.private_key_entry = tk.Entry(self.buyer_frame, font=("Helvetica", 14), show="*")  # Hidden for security
        self.private_key_entry.grid(row=6, column=1, padx=20, pady=10, sticky='ew')

        # Verify Button definition
        tk.Button(self.buyer_frame, text="Verify Weight and OTP", command=self.verify_weight, bg="#4CAF50", fg="white",
                  font=("Helvetica", 14, "bold")).grid(row=7, column=0, columnspan=2, padx=20, pady=20, sticky='ew')

        # Result Label
        self.result_label = tk.Label(self.buyer_frame, text="", font=("Helvetica", 14), bg="#f0f0f0")
        self.result_label.grid(row=8, column=0, columnspan=2, padx=20, pady=10, sticky='w')

    def verify_weight(self):
        # Verify the weight of the item and the OTP entered by the buyer
        if not system_state.get('item_in_box', False):
            self.result_label.config(text="No item available for collection.", fg="red")
            return

        if self.otp_manager.is_otp_expired():
            self.result_label.config(text="OTP has expired. Please contact the seller.", fg="red")
            self.notify_buyer_otp_expired()
            return

        # Read weight
        actual_weight = self.hardware.read_weight()
        advertised_weight = system_state.get("advertised_weight", 0)

        print("Enter the 6-digit OTP using the keypad:")
        entered_otp = self.read_keypad_input()

        if self.otp_manager.verify_otp(entered_otp):
            if (advertised_weight - WEIGHT_TOLERANCE) <= actual_weight <= (advertised_weight + WEIGHT_TOLERANCE):
                self.result_label.config(text=f"Verification successful! Unlocking door for item collection.", fg="green")
                self.hardware.unlock_door()
                update_system_state('item_status', 'Item placed')

                # Get buyer's private key
                buyer_private_key = self.private_key_entry.get().strip()
                if not buyer_private_key:
                    self.result_label.config(text="Please enter your Ethereum private key.", fg="red")
                    return

                self.buyer_private_key = buyer_private_key  # Store temporarily for security reasons

                # Notify buyer to collect the item
                try:
                    self.buyer_bot.send_message("Please collect your item now. Once done, close the door.")
                except Exception as e:
                    logger.error(f"Error sending message to buyer: {e}")

                # Start monitoring item removal and door closure
                monitor_thread = Thread(target=self.monitor_item_collection)
                monitor_thread.start()
            else:
                self.result_label.config(text=f"Weight does not match. Actual: {actual_weight:.2f} kg", fg="orange")
                with state_lock:
                    system_state['error_logs'].append(f"Weight mismatch: Actual {actual_weight:.2f} kg")
                self.hardware.lock_door()
        else:
            self.result_label.config(text="Invalid OTP!", fg="red")
            with state_lock:
                system_state['error_logs'].append("Invalid OTP")
            self.hardware.lock_door()

    def read_keypad_input(self):
        # Read the OTP entered by the buyer using the keypad.
        otp_entered = ""
        while len(otp_entered) < 6:
            keys_pressed = keypad.pressed_keys
            if keys_pressed:
                for key in keys_pressed:
                    if key.isdigit():
                        otp_entered += key
                        print(f"OTP Entered So Far: {otp_entered}")
                        # Debounce
                        while keypad.pressed_keys:
                            time.sleep(0.1)
                        time.sleep(0.1)
            time.sleep(0.1)
        return otp_entered

    def monitor_item_collection(self):
        # Monitor the item removal and door closure after buyer verification.
        # Wait for buyer to open the door (already unlocked)
        while self.hardware.is_door_closed():
            time.sleep(0.1)
        logger.info("Buyer opened the door for collection.")

        # Start time for timeout
        start_time = time.time()
        timeout = 300  # 5 minutes to remove the item

        # Monitor item removal with timeout
        item_removed = False
        while time.time() - start_time < timeout:
            weight = self.hardware.read_weight()
            if weight <= WEIGHT_TOLERANCE:
                item_removed = True
                logger.info("Item has been removed from the scale.")
                break
            time.sleep(1)  # Check every second

        # Wait for buyer to close the door
        #while not self.hardware.is_door_closed(): # CHECK THIS LOGIC SIYA 
        #    time.sleep(0.1)
        #logger.info("Buyer closed the door after collection.")

        if item_removed:
            # Successful collection
            self.send_seller_message(f"The buyer has successfully collected the item.\nTransaction ID: {system_state['transaction_id']}")
            update_system_state('item_collected', True)
            try:
                self.buyer_bot.send_message("Thank you for your purchase!")
            except Exception as e:
                logger.error(f"Error sending thank you message to buyer: {e}")

            # Trigger payment via Flask API
            try:
                item_price_zar = system_state.get('item_price')
                response = requests.post(
                    f"{FLASK_API_URL}/trigger_payment",
                    headers={'x-api-key': os.getenv('API_KEY')},
                    json={
                        'buyer_private_key': self.buyer_private_key,
                        'item_price_zar': item_price_zar
                    }
                )

                if response.status_code == 200:
                    payment_data = response.json()
                    logger.info(f"Payment successful. TX Hash: {payment_data['tx_hash']}")
                    eth_amount = payment_data['eth_amount']
                    self.result_label.config(
                        text=f"Payment successful! {eth_amount:.6f} ETH sent.\nTX Hash: {payment_data['tx_hash'][:10]}...",
                        fg="green"
                    )
                else:
                    error_message = response.json().get('message', 'Unknown error')
                    logger.error(f"Failed to trigger payment: {error_message}")
                    self.result_label.config(text=f"Payment failed: {error_message}", fg="red")
            except Exception as e:
                logger.error(f"Error triggering payment: {e}")
                self.result_label.config(text=f"Error triggering payment: {e}", fg="red")

            # Reset system state
            system_state['item_in_box'] = False
            self.reset_system()
        else:
            # Buyer closed the door without removing the item
            self.send_seller_message(f"The buyer closed the door without collecting the item.\nTransaction ID: {system_state['transaction_id']}")
            try:
                self.buyer_bot.send_message("You did not collect your item. Please contact the seller.")
            except Exception as e:
                logger.error(f"Error sending notification to buyer: {e}")
            # Notify seller that an item is still in the box
            try:
                self.seller_bot.send_message("An item was not collected by the buyer. Please reclaim it.")
            except Exception as e:
                logger.error(f"Error notifying seller about uncollected item: {e}")
            # Reset door status but keep 'item_in_box' as True
            self.reset_system()

    def send_seller_message(self, msg):
        # Send a message to the seller via Telegram
        self.seller_bot.send_message(msg)

    def notify_buyer_otp_expired(self):
        # Notify the buyer that the OTP has expired.
        message = "Your OTP has expired. Please contact the seller to request a new OTP."
        try:
            self.buyer_bot.send_message(message)
            logger.info("Buyer notified of OTP expiration.")
        except Exception as e:
            logger.error(f"Error notifying buyer of OTP expiration: {e}")

    def reclaim_item(self):
        # Allow the seller to reclaim the uncollected item
        if system_state.get('item_in_box', False):
            # Reset the system state, assuming the seller has taken back the item
            self.send_seller_message(f"The seller has reclaimed the uncollected item.\nTransaction ID: {system_state['transaction_id']}")
            try:
                self.buyer_bot.send_message("The Seller has reclaimed the uncollected item.")
            except Exception as e:
                logger.error(f"Error sending reclamation message to buyer: {e}")
            # Reset system state
            system_state['item_in_box'] = False
            self.reset_system()
        else:
            messagebox.showinfo("Info", "No item to reclaim.")

    def reset_system(self):
        # Reset the system after a transaction is completed
        # Clear seller data
        system_state.clear()
        system_state['transaction_active'] = False
        system_state['item_in_box'] = False
        self.save_seller_data()

        # Reset other system states
        update_system_state('door_status', 'Unknown')
        update_system_state('item_status', 'No item placed')
        update_system_state('item_collected', False)
        update_system_state('item_price', None)
        update_system_state('transaction_id', None)
        update_system_state('error_logs', [])

        # Reset OTP creation time
        self.otp_manager.otp_creation_time = None

        # Clear GUI
        self.clear_buyer_gui()
        self.clear_seller_gui()

        # Show intro popup
        self.create_intro()

    def clear_buyer_gui(self):
        # Clear the buyer GUI elements.
        for widget in self.buyer_frame.winfo_children():
            widget.destroy()

    def clear_seller_gui(self):
        # Clear the seller GUI elements.
        for widget in self.seller_frame.winfo_children():
            widget.destroy()

    def add_reclaim_button(self):
        # Add a reclaim button to the seller interface if an item is in the box
        if system_state.get('item_in_box', False) and not hasattr(self.seller_frame, 'reclaim_button'):
            reclaim_button = tk.Button(self.seller_frame, text="Reclaim Item", command=self.reclaim_item, bg="#f44336", fg="white",
                                        font=("Helvetica", 12, "bold"))
            reclaim_button.grid(row=6, column=0, columnspan=2, padx=20, pady=20, sticky='ew')
            self.seller_frame.reclaim_button = reclaim_button  # Prevent multiple buttons

    # Handle GUI Closing
    def on_closing(self):
        # Handle the GUI window close event.
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            monitor_stop_event.set()
            hardware.cleanup()
            self.root.quit()
            self.root.destroy()

# Initialize Tkinter Root
root = tk.Tk()

# Initialize Keypad
ROWS = [
    digitalio.DigitalInOut(board.D17),  # GPIO 17 (Key_R1)
    digitalio.DigitalInOut(board.D27),  # GPIO 27 (Key_R2)
    digitalio.DigitalInOut(board.D22),  # GPIO 22 (Key_R3)
    digitalio.DigitalInOut(board.D10)   # GPIO 10 (Key_R4)
]

COLS = [
    digitalio.DigitalInOut(board.D9),   # GPIO 9 (Key_C1)
    digitalio.DigitalInOut(board.D11),  # GPIO 11 (Key_C2)
    digitalio.DigitalInOut(board.D13),  # GPIO 13 (Key_C3)
    digitalio.DigitalInOut(board.D19)   # GPIO 19 (Key_C4)
]

KEYS = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"]
]

keypad = Matrix_Keypad(COLS, ROWS, KEYS)

# Initialize GUI
blockbox_gui = BlockBoxGUI(root, hardware, buyer_bot_handler, seller_bot_handler, otp_manager)

# Set the on_closing method for the GUI
root.protocol("WM_DELETE_WINDOW", blockbox_gui.on_closing)

# Start Tkinter main loop
try:
    root.mainloop()
except Exception as e:
    logger.critical(f"Unhandled exception in Tkinter main loop: {e}")
    hardware.cleanup()
