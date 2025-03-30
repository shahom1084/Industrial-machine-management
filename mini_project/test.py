from pymongo import MongoClient

# Connect to MongoDB (Modify connection string if needed)
client = MongoClient("mongodb://localhost:27017/")

# Select the database
db = client["MINI_PROJECT"]

# Select the collection
collection = db["machines"]

# Fetch all documents
machines = collection.find({}, {"machine_name": 1, "_id": 0})

# Print machine names
for machine in machines:
    print(machine.get("machine_name", "No Name Found"))
