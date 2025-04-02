import csv
import random
from datetime import datetime, timedelta
import os

def generate_machine_logs(filename, num_rows=100000):
    
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
    
    # Manufacturing stages (used for different machine types)
    manufacturing_stages = [
        "Installation", "Testing", "Cooling", "Heating", "Maintenance", "Shutdown"
    ]
    
    # Create header without LogID
    header = [
        "Date", "MachineName", "StartTime", "EndTime", 
        "ManufacturingStage", "ProductionAmount", "Unit", 
        "MaintenanceStatus", "ErrorsReported", "DefectivesProduced"
    ]
    
    # Units of measurement based on machine type
    units = {
        "HVAC Compressor": "units",
        "Cooling Tower": "gallons",
        "Air Handler": "cubic meters",
        "Chiller": "tons",
        "Heat Pump": "kW",
        "Air Scrubber": "units",
        "Duct Fan": "cubic feet",
        "Variable Speed Drive": "units",
        "Humidifier": "gallons",
        "Dehumidifier": "gallons",
        "Refrigerant Recovery": "gallons",
        "Exhaust Fan": "cubic feet",
        "Steam Boiler": "bar",
        "Air Conditioning": "tons",
        "Filtration Unit": "gallons"
    }
    
    # Maintenance status options
    maintenance_status = ["Operational", "Needs Maintenance", "Under Maintenance"]
    
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
            
            # Determine unit based on machine type
            unit_of_measure = "units"
            for machine_type, unit in units.items():
                if machine_type in machine:
                    unit_of_measure = unit
                    break
            
            # Random start time (in 24h format)
            hour = random.randint(6, 21)  # 6 AM to 9 PM operation
            minute = random.randint(0, 59)
            start_time = f"{hour:02d}:{minute:02d}"
            
            # Operation duration between 30 minutes and 3 hours
            duration_minutes = random.randint(30, 180)
            
            # Calculate end time
            start_datetime = datetime.strptime(f"{log_date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            end_time = end_datetime.strftime("%H:%M")
            
            # Manufacturing stage (could be any of the HVAC-related stages)
            stage = random.choice(manufacturing_stages)
            
            # Production amount (based on machine type and duration)
            if "Compressor" in machine:
                production = random.randint(10, 50)
            elif "Cooling Tower" in machine:
                production = round(random.uniform(50.0, 200.0), 2)
            elif "Air Handler" in machine:
                production = random.randint(100, 500)
            elif "Chiller" in machine:
                production = random.randint(20, 100)
            elif "Heat Pump" in machine:
                production = round(random.uniform(15.0, 80.0), 2)
            elif "Air Scrubber" in machine:
                production = random.randint(10, 50)
            elif "Duct Fan" in machine:
                production = random.randint(100, 400)
            elif "Variable Speed Drive" in machine:
                production = random.randint(50, 200)
            elif "Humidifier" in machine:
                production = random.randint(30, 150)
            elif "Dehumidifier" in machine:
                production = random.randint(30, 150)
            elif "Refrigerant Recovery" in machine:
                production = random.randint(10, 50)
            elif "Exhaust Fan" in machine:
                production = random.randint(150, 600)
            elif "Steam Boiler" in machine:
                production = random.randint(10, 50)
            elif "Air Conditioning" in machine:
                production = random.randint(20, 100)
            elif "Filtration Unit" in machine:
                production = random.randint(30, 150)
            
            # Adjust production by duration factor
            production = int(production * (duration_minutes / 60))
            
            # Maintenance status (mostly operational)
            maint_status = random.choices(
                maintenance_status, 
                weights=[0.85, 0.10, 0.05], 
                k=1
            )[0]
            
            # Number of errors reported
            if maint_status == "Operational":
                errors_reported = random.choices(
                    [0, 1, 2, 3, 4, 5],
                    weights=[0.7, 0.15, 0.08, 0.04, 0.02, 0.01],
                    k=1
                )[0]
            else:
                errors_reported = random.choices(
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    weights=[0.05, 0.1, 0.15, 0.2, 0.15, 0.1, 0.1, 0.05, 0.05, 0.03, 0.02],
                    k=1
                )[0]
            
            # Number of defective products
            if maint_status == "Operational" and errors_reported <= 1:
                defect_percentage = random.uniform(0, 0.03)
            elif maint_status == "Operational" and errors_reported > 1:
                defect_percentage = random.uniform(0.02, 0.07)
            else:
                defect_percentage = random.uniform(0.05, 0.15)
            
            defectives_produced = int(production * defect_percentage)
            
            # Assemble the row (without LogID)
            row = [
                log_date,             # Date
                machine,              # MachineName
                start_time,           # StartTime
                end_time,             # EndTime
                stage,                # ManufacturingStage
                production,           # ProductionAmount
                unit_of_measure,      # Unit
                maint_status,         # MaintenanceStatus
                errors_reported,      # ErrorsReported
                defectives_produced   # DefectivesProduced
            ]
            
            writer.writerow(row)
            
            # Print progress
            if (i + 1) % 1000 == 0:
                print(f"Generated {i + 1} rows...")
    
    file_size = os.path.getsize(filename) / (1024 * 1024)  # Size in MB
    print(f"CSV generation complete: {num_rows} rows written to {filename} (Size: {file_size:.2f} MB)")

# Run the generator
if __name__ == "__main__":
    output_file = "hvac_machine_logs.csv"
    row_count = 100000
    
    generate_machine_logs(output_file, row_count)
