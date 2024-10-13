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

4. ** Run NGROK tunnel **
   
   ngrok http 5000

5. **Update blockbox.py with ngrok URL**
   

6. ** Set up .env file**

   # .env file

   # Telegram Bot Tokens and Chat IDs
   BUYER_TELEGRAM_TOKEN=your_buyer_bot_token
   BUYER_CHAT_ID=your_buyer_chat_id

   SELLER_TELEGRAM_TOKEN=your_seller_bot_token
   SELLER_CHAT_ID=your_seller_chat_id

   # OTP Secret Key
   OTP_SECRET=your_otp_secret_key

   # Blockchain Configuration
   INFURA_URL=https://sepolia.infura.io/v3/your_infura_project_id
   SELLER_ADDRESS=your_seller_ethereum_address

   # API Key for Flask Server Authentication
   API_KEY=your_api_key_for_flask_server

7. ** Run blockbox.py **




