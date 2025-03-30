from flask import Flask, request, jsonify, render_template
from flask_pymongo import PyMongo
from kafka import KafkaProducer
import json

app = Flask(__name__)

# MongoDB Connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/MINI_PROJECT"  
mongo = PyMongo(app)

# Kafka Producer Setup
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

@app.route("/")
def worker_dashboard():
    machines = list(mongo.db.machines.find({}, {"_id": 0, "id": 1, "machine_name": 1}))
    return render_template("./index.html", machines=machines)

# Route to handle machine usage submission
@app.route("/submit_usage", methods=["POST"])
def submit_usage():
    data = request.json
    data["event_type"] = "machine_usage"
    
    producer.send("machine_usage_topic", data)
    
    return jsonify({"message": "Machine usage data sent to Kafka"}), 200

# Route to handle error reporting
@app.route("/report_error", methods=["POST"])
def report_error():
    data = request.json
    data["event_type"] = "error_report"
    
    # Send data to Kafka topic
    producer.send("machine_error_topic", data)
    
    return jsonify({"message": "Error report sent to Kafka"}), 200

if __name__ == "__main__":
    app.run(debug=True)
