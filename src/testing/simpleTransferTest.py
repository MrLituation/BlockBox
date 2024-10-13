#Credits: youtube.com/watch?v=0rzDcair0rg0
#Channel - Replit  

from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()

INFURA_URL = os.getenv('INFURA_URL')
PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')
TO_ADDRESS = Web3.to_checksum_address('0xD35968B093383a25E4761905396477997E0C6108')  # Replace with recipient's address

web3 = Web3(Web3.HTTPProvider(INFURA_URL))

if not web3.is_connected():
    print("Web3 is not connected. Check your INFURA_URL.")
    exit()

account = web3.eth.account.from_key(PRIVATE_KEY)
sender_address = account.address
print(f"Sender Address: {sender_address}")

balance = web3.eth.get_balance(sender_address)
eth_balance = web3.from_wei(balance, 'ether')
print(f"ETH Balance: {eth_balance} ETH")

if eth_balance < 0.01:
    print("Insufficient funds for transfer.")
    exit()

try:
    nonce = web3.eth.get_transaction_count(sender_address, 'latest')
    print(f"Nonce: {nonce}")

    tx = {
        'nonce': nonce,
        'to': TO_ADDRESS,
        'value': web3.to_wei(0.01, 'ether'),  # Sending 0.01 ETH
        'gas': 25000,
        'gasPrice': web3.to_wei('1100', 'gwei'),  # Set higher gas price
        'chainId': 11155111,  # Sepolia
    }

    signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction sent with hash: {tx_hash.hex()}")

    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    print(f"Transaction receipt: {receipt}")

    if receipt.status == 1:
        print("Transfer succeeded.")
    else:
        print("Transfer failed.")
except Exception as e:
    print(f"An error occurred: {e}")
