import csv
import random
from datetime import datetime, timedelta
import os

def generate_error_logs(filename, num_rows=50000):
    
    # Machine names based on HVAC industry machines
    machine_names = [
        "HVAC Compressor Model-X", "HVAC Cooling Tower CT-500", 
        "HVAC Air Handler AH-220", "HVAC Chiller Unit CU-800", 
        "HVAC Heat Pump HP-300", "HVAC Air Scrubber AS-400", 
        "HVAC Duct Fan DF-600", "HVAC Variable Speed Drive VSD-9", 
        "HVAC Humidifier H-120", "HVAC Dehumidifier DH-300", 
        "HVAC Refrigerant Recovery System RRS-5", "HVAC Exhaust Fan EF-400", 
        "HVAC Steam Boiler SB-600", "HVAC Air Conditioning Unit ACU-1200", 
        "HVAC Filtration Unit FU-200"
    ]

    # More unstructured error descriptions with some frequent patterns
    error_descriptions = {
        "HVAC Compressor": ["Overheating", "Compressor Issue", "Faulty Compressor", "Compressor Low Pressure", "Heating Problem", "Thermal Shutdown"],
        "Cooling Tower": ["Pump Failure", "Vibration", "Pump is Not Running", "Water Flow Blocked", "Noise Issue", "Excessive Vibration"],
        "Air Handler": ["Clogged Filter", "Blower Malfunction", "Filter Issue", "Motor Breakdown", "Sensor Not Responding", "No Power"],
        "Chiller": ["Coolant Loss", "Chiller Shut Down", "Overheating", "Temperature Fluctuation", "High Pressure", "Compressor Stop"],
        "Heat Pump": ["Thermostat Error", "Valve Stuck", "No Heating", "Heater Failure", "Fan Issue", "Low Heat Output"],
        "Air Scrubber": ["Airflow Problem", "Motor Burnout", "Air Filter Blocked", "Failure in Fan", "Air Quality Low"],
        "Duct Fan": ["Fan Not Running", "Blade Misalignment", "Noisy Fan", "Fan Motor Malfunction", "Excessive Noise", "Power Supply Issue"],
        "Variable Speed Drive": ["Overload", "Power Surge", "Frequency Error", "Controller Issue", "Speed Regulation Failure", "Communication Error"],
        "Humidifier": ["No Water", "Heater Malfunction", "Water Level Low", "Failed Sensor", "Humidification Error", "Heating Failure"],
        "Dehumidifier": ["Drain Blockage", "No Cooling", "Low Performance", "Water Drain Failure", "Low Humidity", "Compressor Not Working"],
        "Refrigerant Recovery": ["Leak", "High Temperature", "Vacuum Problem", "Pressure Loss", "Compressor Shutdown", "Cooling Issue"],
        "Exhaust Fan": ["Slipping Belt", "Motor Failure", "Overheating", "Fan Speed Low", "Fan Failure", "Excessive Vibration"],
        "Steam Boiler": ["Overheating", "Pressure High", "Low Water", "Boiler Shut Down", "Control Valve Malfunction", "Water Leakage"],
        "Air Conditioning": ["Low Refrigerant", "Cooling Failure", "Compressor Error", "Thermostat Problem", "Fan Not Spinning", "Temperature Not Stable"],
        "Filtration Unit": ["Clogged Filter", "Pump Malfunction", "Air Filter Saturation", "Flow Disruption", "No Air Flow", "Filter Rupture"]
    }

    # Create header
    header = ["Date", "MachineName", "StartTime", "EndTime", "ErrorNo", "ErrorDesc"]

    # Create the CSV file
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        
        # Base date for our logs (past 6 months)
        base_date = datetime.now() - timedelta(days=180)

        for i in range(num_rows):
            # Random date
            log_date = (base_date + timedelta(days=random.randint(0, 179))).strftime("%Y-%m-%d")
            
            # Select random machine
            machine = random.choice(machine_names)

            # Determine error type based on machine
            error_desc = "Unknown Error"
            for key, errors in error_descriptions.items():
                if key in machine:
                    error_desc = random.choice(errors)
                    break

            # Randomly adjust the format of the error description to make it unstructured
            if random.random() < 0.5:
                error_desc = error_desc.lower()
            if random.random() < 0.3:
                error_desc = error_desc.replace(" ", "_")
            if random.random() < 0.2:
                error_desc = error_desc + "_(Unusual)"

            # Assign an error number (randomized for uniqueness)
            error_no = random.randint(100, 999)

            # Random start time (errors can occur anytime)
            hour = random.randint(0, 23)  # 24-hour format
            minute = random.randint(0, 59)
            start_time = f"{hour:02d}:{minute:02d}"

            # Error duration (between 5 min to 3 hours)
            duration_minutes = random.randint(5, 180)

            # Calculate end time
            start_datetime = datetime.strptime(f"{log_date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            end_time = end_datetime.strftime("%H:%M")

            # Assemble the row
            row = [log_date, machine, start_time, end_time, error_no, error_desc]

            writer.writerow(row)
            
            # Print progress every 5000 rows
            if (i + 1) % 5000 == 0:
                print(f"Generated {i + 1} error log rows...")

    file_size = os.path.getsize(filename) / (1024 * 1024)  # Size in MB
    print(f"CSV generation complete: {num_rows} rows written to {filename} (Size: {file_size:.2f} MB)")

# Run the generator
if __name__ == "__main__":
    output_file = "hvac_error_logs_unstructured.csv"
    row_count = 300000  # Generating 300,000 rows
    
    generate_error_logs(output_file, row_count)
