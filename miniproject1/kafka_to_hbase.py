# from kafka import KafkaConsumer
# import happybase
# import json
# import logging
# from time import sleep

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # Kafka Configuration
# KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
# KAFKA_TOPICS = ['machine_logs', 'error_logs']
# CONSUMER_GROUP_ID = 'hbase-consumer-group'

# # HBase Configuration
# HBASE_HOST = '192.168.137.73'
# HBASE_PORT = 9090
# HBASE_TABLES = {
#     'machine_logs': 'machine_logs',
#     'error_logs': 'error_logs'
# }

# def connect_to_kafka():
#     try:
#         consumer = KafkaConsumer(
#             *KAFKA_TOPICS,
#             bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
#             group_id=CONSUMER_GROUP_ID,
#             auto_offset_reset='earliest',
#             value_deserializer=lambda x: json.loads(x.decode('utf-8')),
#             enable_auto_commit=True
#         )
#         logger.info(f"Connected to Kafka, subscribing to: {KAFKA_TOPICS}")
#         return consumer
#     except Exception as e:
#         logger.error(f"Failed to connect to Kafka: {e}")
#         return None

# def connect_to_hbase():
#     """Establish connection to HBase and return connection and table objects"""
#     try:
#         connection = happybase.Connection(HBASE_HOST, port=HBASE_PORT)
#         all_tables = [t.decode('utf-8') for t in connection.tables()]
#         logger.info(f"All available tables: {all_tables}")
        
#         # Check if required tables exist
#         for topic, table_name in HBASE_TABLES.items():
#             if table_name not in all_tables:
#                 logger.error(f"Table {table_name} does not exist in HBase")
#                 connection.close()
#                 return None, None
        
#         tables = {
#             'machine_logs': connection.table('machine_logs'),
#             'error_logs': connection.table('error_logs')
#         }
#         logger.info("Connected to HBase, tables initialized")
#         return connection, tables
#     except Exception as e:
#         logger.error(f"Failed to connect to HBase: {e}")
#         return None, None

# def process_message(message, tables):
#     """Process a single Kafka message and insert into the appropriate HBase table"""
#     try:
#         if not isinstance(message.value, dict):
#             logger.warning(f"Skipping message: not a valid JSON object: {message.value}")
#             return
        
#         # Select the HBase table based on the Kafka topic
#         table = tables.get(message.topic)
#         if not table:
#             logger.warning(f"No HBase table defined for topic: {message.topic}")
#             return
        
#         # Use 'id' as row key if present, otherwise generate UUID
#         row_key = str(message.value.get('id', import_uuid().uuid4()))
        
#         # Prepare data for HBase
#         data = {
#             'logs:topic': message.topic,
#             'logs:timestamp': str(message.timestamp)
#         }
#         for key, value in message.value.items():
#             data[f'logs:{key}'] = str(value)

#         logger.info(f"Prepared data for row {row_key} in table {message.topic}: {data}")
        
#         # Insert into HBase
#         table.put(row_key.encode('utf-8'), data)
#         logger.info(f"Inserted message with key {row_key} into {message.topic}")
#     except Exception as e:
#         logger.error(f"Error processing message: {e}", exc_info=True)

# def main():
#     # Connect to Kafka
#     consumer = connect_to_kafka()
#     if not consumer:
#         logger.error("Exiting due to Kafka connection failure")
#         return
    
#     # Connect to HBase
#     connection, tables = connect_to_hbase()
#     if not connection or not tables:
#         logger.error("Exiting due to HBase connection failure")
#         return
    
#     # Process messages
#     try:
#         for message in consumer:
#             process_message(message, tables)
#     except KeyboardInterrupt:
#         logger.info("Interrupted by user, shutting down...")
#     finally:
#         logger.info("Closing connections")
#         consumer.close()
#         connection.close()

# if __name__ == "__main__":
#     retry_count = 0
#     max_retries = 5
#     while retry_count < max_retries:
#         try:
#             main()
#             break
#         except Exception as e:
#             retry_count += 1
#             wait_time = 2 ** retry_count
#             logger.error(f"Error in main process: {e}")
#             logger.info(f"Retrying in {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
#             sleep(wait_time)
    
#     if retry_count == max_retries:
#         logger.error("Maximum retries reached. Exiting.")

# # Lazy import for uuid inside process_message
# def import_uuid():
#     import uuid
#     return uuid
from kafka import KafkaConsumer
import json
import logging
import csv
import os
from time import sleep
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = '172.16.204.92:9092'  # Updated based on your log
KAFKA_TOPICS = ['machine_logs', 'error_logs']
CONSUMER_GROUP_ID = 'csv-consumer-group'

# CSV Configuration - specify full paths to ensure correct location
# Replace these with your actual file paths if different
CSV_FILES = {
    'machine_logs': os.path.abspath('machine_logs.csv'),
    'error_logs': os.path.abspath('error_logs.csv')
}

# Define fixed CSV headers for each topic
CSV_HEADERS = {
    'machine_logs': [
        'Date', 'MachineName', 'StartTime', 'EndTime', 'ManufacturingStage',
        'ProductionAmount', 'Unit', 'MaintenanceStatus', 'ErrorsReported', 'DefectivesProduced'
    ],
    'error_logs': [
        'Date', 'MachineName', 'StartTime', 'EndTime', 'ErrorNo', 'ErrorDesc'
    ]
}

def connect_to_kafka():
    try:
        # Use the broker address from your logs
        consumer = KafkaConsumer(
            *KAFKA_TOPICS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP_ID,
            auto_offset_reset='latest',  # Changed to 'latest' to only get new messages
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            enable_auto_commit=True
        )
        logger.info(f"Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}, subscribing to: {KAFKA_TOPICS}")
        return consumer
    except Exception as e:
        logger.error(f"Failed to connect to Kafka: {e}")
        return None

def validate_csv_files():
    """Validate existing CSV files have the correct headers or create them if they don't exist"""
    for topic, filepath in CSV_FILES.items():
        headers = CSV_HEADERS[topic]
        logger.info(f"Validating CSV file: {filepath}")
        
        # Print the absolute path to help debugging
        abs_path = os.path.abspath(filepath)
        logger.info(f"Absolute path: {abs_path}")
        
        # Get directory info
        dir_path = os.path.dirname(abs_path)
        logger.info(f"Directory: {dir_path}")
        if dir_path and not os.path.exists(dir_path):
            logger.info(f"Creating directory: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
        
        # Check if file exists
        if not os.path.exists(filepath):
            # Create new file with headers
            logger.info(f"Creating new CSV file: {filepath}")
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                logger.info(f"Created file with headers: {headers}")
        else:
            # File exists, check current row count
            with open(filepath, 'r', newline='') as f:
                reader = csv.reader(f)
                rows = sum(1 for row in reader)
                logger.info(f"Existing file {filepath} has {rows} rows (including header)")

def write_to_csv(message):
    """Write a Kafka message to the appropriate CSV file with the defined format"""
    try:
        if not isinstance(message.value, dict):
            logger.warning(f"Skipping message: not a valid JSON object: {message.value}")
            return
        
        # Debug: print message content
        logger.debug(f"Processing message: {message.value}")
        
        # Get the CSV file and headers corresponding to the topic
        filepath = CSV_FILES.get(message.topic)
        headers = CSV_HEADERS.get(message.topic)
        
        if not filepath or not headers:
            logger.warning(f"No CSV configuration defined for topic: {message.topic}")
            return
        
        # Map the message data to the expected CSV columns
        if message.topic == 'machine_logs':
            row_data = [
                message.value.get('Date', ''),
                message.value.get('MachineName', ''),
                message.value.get('StartTime', ''),
                message.value.get('EndTime', ''),
                message.value.get('ManufacturingStage', ''),
                message.value.get('ProductionAmount', ''),
                message.value.get('Unit', ''),
                message.value.get('MaintenanceStatus', ''),
                message.value.get('ErrorsReported', ''),
                message.value.get('DefectivesProduced', '')
            ]
        elif message.topic == 'error_logs':
            row_data = [
                message.value.get('Date', ''),
                message.value.get('MachineName', ''),
                message.value.get('StartTime', ''),
                message.value.get('EndTime', ''),
                message.value.get('ErrorNo', ''),
                message.value.get('ErrorDesc', '')
            ]
        else:
            logger.warning(f"Unknown topic format: {message.topic}")
            return
        
        # Count rows before appending
        previous_count = 0
        try:
            with open(filepath, 'r', newline='') as f:
                previous_count = sum(1 for _ in csv.reader(f))
        except Exception as e:
            logger.warning(f"Could not count rows: {e}")
        
        # Open file in append mode
        with open(filepath, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(row_data)
            
        # Verify row was added
        try:
            with open(filepath, 'r', newline='') as f:
                current_count = sum(1 for _ in csv.reader(f))
                if current_count > previous_count:
                    logger.info(f"Successfully appended message to {filepath} (rows: {previous_count} → {current_count})")
                else:
                    logger.warning(f"Failed to append message - row count didn't increase: {previous_count}")
        except Exception as e:
            logger.warning(f"Could not verify row addition: {e}")
            
    except Exception as e:
        logger.error(f"Error writing message to CSV: {e}", exc_info=True)

def main():
    # Connect to Kafka
    consumer = connect_to_kafka()
    if not consumer:
        logger.error("Exiting due to Kafka connection failure")
        return
    
    # Validate CSV files
    validate_csv_files()
    
    logger.info("Starting to consume messages...")
    
    # Process messages
    try:
        for message in consumer:
            write_to_csv(message)
    except KeyboardInterrupt:
        logger.info("Interrupted by user, shutting down...")
    finally:
        logger.info("Closing Kafka connection")
        consumer.close()

if __name__ == "__main__":
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            main()
            break
        except Exception as e:
            retry_count += 1
            wait_time = 2 ** retry_count
            logger.error(f"Error in main process: {e}")
            logger.info(f"Retrying in {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
            sleep(wait_time)
    
    if retry_count == max_retries:
        logger.error("Maximum retries reached. Exiting.")