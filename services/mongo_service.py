from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["enterprise_chatbot"]

users_collection = db["users"]

documents_collection = db["documents"]

chat_collection = db["chat_history"]