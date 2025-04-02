import csv
import happybase
import uuid
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HBASE_HOST = '192.168.137.73'  
HBASE_PORT = 9090  
HBASE_TABLE="error_logs"
COLUMN_FAMILY = 'logs'  

# CSV Configuration
CSV_FILE_PATH = 'hvac_error_logs_unstructured.csv'  # Replace with your CSV file path
ROW_KEY_COLUMN = None  # Set this to the column name to use as row key, or None to generate UUIDs

def connect_to_hbase():
    try:
        connection = happybase.Connection(HBASE_HOST,port=HBASE_PORT)
        
        if HBASE_TABLE.encode('utf-8') not in connection.tables():
            logger.info(f"Table {HBASE_TABLE} does not exist, creating it...")
            connection.create_table(
                HBASE_TABLE,
                {f'{COLUMN_FAMILY}': dict()}
            )
        
        logger.info(f"Connected to HBase, using table: {HBASE_TABLE}")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to HBase: {e}")
        return None

def generate_row_key(row_data=None, index=None):
    
    if ROW_KEY_COLUMN and ROW_KEY_COLUMN in row_data:
       
        return str(row_data[ROW_KEY_COLUMN])
    elif index is not None:
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{timestamp}_{index}"
    else:
        
        return str(uuid.uuid4())

def import_csv_to_hbase():
   
    connection = connect_to_hbase()
    if not connection:
        return False
    
    table = connection.table(HBASE_TABLE)
    batch_size = 1000
    batch = table.batch(batch_size=batch_size)
    
    try:
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            
            row_count = 0
            for index, row in enumerate(csv_reader):
                row_count += 1
                row_key = generate_row_key(row, index)
                
                # Convert all values to strings and prefix with column family
                hbase_row = {
                    f'{COLUMN_FAMILY}:{key}': str(value) 
                    for key, value in row.items() 
                    if value  # Skip empty values
                }
                
                # Add to batch
                batch.put(row_key.encode('utf-8'), hbase_row)
                
                # Log progress
                if row_count % batch_size == 0:
                    logger.info(f"Processed {row_count} rows")
            
            # Send any remaining rows
            batch.send()
            logger.info(f"Import completed. Total rows imported: {row_count}")
    
    except Exception as e:
        logger.error(f"Error importing CSV to HBase: {e}")
        return False
    finally:
        connection.close()
    
    return True

if __name__ == "__main__":
    logger.info(f"Starting import of {CSV_FILE_PATH} to HBase table {HBASE_TABLE}")
    success = import_csv_to_hbase()
    if success:
        logger.info("Import completed successfully")
    else:
        logger.error("Import failed")