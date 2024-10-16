# Block Box

Block Box is a smart last mile locker system that solves the common problem every E-commerce consumer has of having to pay for an ordered item before reviewing the item. This system achieves this by integrating IoT technology with blockchain technology for efficient automated parcel verification processes using the weight of the parcel. Upon successful verification the system facilitates a secure smart contract-based transaction between the seller and the buyer.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Hardware Setup](#hardware-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Usage](#usage)
- [License](#license)

## Features

- Secure parcel locker controlled by a Raspberry Pi.
- Integration with Ethereum blockchain (Sepolia testnet) for transaction management.
- Real-time notifications via Telegram bots for buyers and sellers.
- OTP-based authentication for parcel collection.
- GUI developed with Tkinter for user interactions.
- Weight and door sensors for item verification.
- Secure payment processing using smart contracts on testnet.

## Prerequisites

- **Hardware**:
  - Raspberry Pi 4B.
  - HX711 Load Cell Amplifier and weight sensor.
  - Magnetic Reed Switch for door status detection.
  - Solenoid Lock controlled via GPIO.
  - 4x4 Matrix Keypad.
  - Internet connectivity for the Raspberry Pi.

- **Software**:
  - Python 3.8 or higher.
  - Git installed on the Raspberry Pi.

## Installation

1. **Clone the Repository**

   git clone https://github.com/yourusername/blockbox.git
   cd blockbox

2. **Recommended to set up virtual environment**

3. **Install all dependencies**

   pip install -r requirements.txt

4. **Run NGROK tunnel**
   
   ngrok http 5000

5. **Update blockbox.py with ngrok URL**
   

6. **Set up .env file**

   # .env file
   BUYER_TELEGRAM_TOKEN=buyer_bot_token
   ###
   BUYER_CHAT_ID=buyer_chat_id (same as seller if same device)
   ###
   SELLER_TELEGRAM_TOKEN=seller_bot_token
   ###
   SELLER_CHAT_ID=seller_chat_id (same as buyer if same device)
   ###
   OTP_SECRET=otp_secret_key (random)
   ### 
   INFURA_URL=https://sepolia.infura.io/v3/infura_project_id (replace with assigned ID from INFURA)
   ###
   SELLER_ADDRESS=seller_ethereum_address
   ###
   API_KEY=api_key_for_flask_server (random)

8. **Run blockbox.py**




