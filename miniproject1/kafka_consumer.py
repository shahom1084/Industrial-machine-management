from kafka import KafkaConsumer
import json
from datetime import datetime

# Kafka configuration
kafka_bootstrap_servers = ['localhost:9092']
machine_logs_topic = 'machine_logs'
error_logs_topic = 'error_logs'

# Initialize Kafka consumers
machine_consumer = KafkaConsumer(
    machine_logs_topic,
    bootstrap_servers=kafka_bootstrap_servers,
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True
)

error_consumer = KafkaConsumer(
    error_logs_topic,
    bootstrap_servers=kafka_bootstrap_servers,
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True
)

def print_machine_log(log):
    """Print formatted machine log"""
    print("\n=== Machine Log ===")
    print(f"Machine ID: {log['machine_id']}")
    print(f"Worker: {log['worker']}")
    print(f"Start Time: {log['start_time']}")
    print(f"End Time: {log.get('end_time', 'Not ended')}")
    print(f"Purpose: {log['purpose']}")
    print(f"Stage: {log['stage']}")
    if 'production_details' in log:
        print("\nProduction Details:")
        print(f"Units Produced: {log['production_details']['units_produced']}")
        print(f"Unit of Measurement: {log['production_details']['unit_of_measurement']}")
        print(f"Error Count: {log['production_details']['error_count']}")
    print("=" * 50)

def print_error_log(log):
    """Print formatted error log"""
    print("\n=== Error Log ===")
    print(f"Machine ID: {log['machine_id']}")
    print(f"Worker: {log['worker']}")
    print(f"Error Description: {log['error_description']}")
    print(f"Error Time: {log['timestamp']}")
    print(f"Start Time: {log['start_time']}")
    print(f"End Time: {log.get('end_time', 'Not ended')}")
    print(f"Purpose: {log['purpose']}")
    print(f"Stage: {log['stage']}")
    if 'production_details' in log:
        print("\nProduction Details:")
        print(f"Units Produced: {log['production_details']['units_produced']}")
        print(f"Unit of Measurement: {log['production_details']['unit_of_measurement']}")
        print(f"Error Count: {log['production_details']['error_count']}")
    print("=" * 50)

def consume_messages():
    """Consume and display messages from both topics"""
    print(f"Starting to consume messages at {datetime.now()}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            # Check for machine logs
            for message in machine_consumer.poll(timeout_ms=1000).values():
                for record in message:
                    print_machine_log(record.value)
            
            # Check for error logs
            for message in error_consumer.poll(timeout_ms=1000).values():
                for record in message:
                    print_error_log(record.value)
                    
    except KeyboardInterrupt:
        print("\nStopping consumer...")
    finally:
        machine_consumer.close()
        error_consumer.close()

if __name__ == "__main__":
    consume_messages() 