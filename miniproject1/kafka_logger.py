from kafka import KafkaProducer
from pymongo import MongoClient
import json
import time
from datetime import datetime

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['MINI_PROJECT']
usage_collection = db['machine_usage']

# Kafka configuration
kafka_bootstrap_servers = ['localhost:9092']
machine_logs_topic = 'machine_logs'
error_logs_topic = 'error_logs'

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Initialize Kafka producer with custom JSON encoder
producer = KafkaProducer(
    bootstrap_servers=kafka_bootstrap_servers,
    value_serializer=lambda v: json.dumps(v, cls=DateTimeEncoder).encode('utf-8')
)

def get_machine_logs():
    """Fetch all machine usage logs from MongoDB"""
    return list(usage_collection.find({}, {'_id': 0}))

def get_error_logs():
    """Extract error logs from machine usage data"""
    error_logs = []
    machine_logs = get_machine_logs()
    
    for log in machine_logs:
        if 'errors' in log and log['errors']:
            for error in log['errors']:
                error_log = {
                    'machine_id': log['machine_id'],
                    'worker': log['worker'],
                    'error_description': error['description'],
                    'timestamp': error['timestamp'],
                    'start_time': log['start_time'],
                    'end_time': log.get('end_time'),
                    'purpose': log['purpose'],
                    'stage': log['stage']
                }
                if 'production_details' in log:
                    error_log['production_details'] = log['production_details']
                error_logs.append(error_log)
    
    return error_logs

def send_to_kafka():
    """Send machine logs and error logs to Kafka"""
    try:
        # Get machine logs
        machine_logs = get_machine_logs()
        
        # Get error logs
        error_logs = get_error_logs()
        
        # Send machine logs to Kafka
        for log in machine_logs:
            producer.send(machine_logs_topic, value=log)
            print(f"Sent machine log to Kafka: {log['machine_id']}")
        
        # Send error logs to Kafka
        for error in error_logs:
            producer.send(error_logs_topic, value=error)
            print(f"Sent error log to Kafka: {error['machine_id']}")
        
        # Flush the producer to ensure all messages are sent
        producer.flush()
        print(f"Successfully sent {len(machine_logs)} machine logs and {len(error_logs)} error logs to Kafka")
        
    except Exception as e:
        print(f"Error sending logs to Kafka: {str(e)}")
    finally:
        producer.close()

def main():
    """Main function to run the Kafka logger"""
    print("Starting Kafka Logger...")
    while True:
        try:
            send_to_kafka()
            print(f"Waiting for next batch... Current time: {datetime.now()}")
            time.sleep(300)  # Wait for 5 minutes before next batch
        except KeyboardInterrupt:
            print("Stopping Kafka Logger...")
            break
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            time.sleep(60)  # Wait for 1 minute before retrying

if __name__ == "__main__":
    main() 