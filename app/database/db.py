from pymongo import MongoClient
from dotenv import load_dotenv
import os 

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["FluxPay"]  # Database name
merchant_collection = db["Merchants"]  # Collection for merchants/admins
transaction_collection = db["Transactions"]  # Collection for transactions