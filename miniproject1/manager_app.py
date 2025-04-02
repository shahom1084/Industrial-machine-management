from flask import Flask, jsonify, request
from flask_cors import CORS
import happybase
import logging
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# HBase Configuration
HBASE_HOST = '192.168.137.73'
HBASE_PORT = 9090

def connect_to_hbase():
    try:
        connection = happybase.Connection(HBASE_HOST, port=HBASE_PORT)
        logger.info("Connected to HBase")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to HBase: {e}")
        return None

# Query Functions
def fetch_machine_efficiency(limit=5000):
    connection = connect_to_hbase()
    if not connection:
        return []
    table = connection.table('machine_logs')
    data = {}
    for i, (key, row) in enumerate(table.scan(columns=[b'logs:MachineName', b'logs:ProductionAmount', b'logs:DefectivesProduced'])):
        if i >= limit: 
            break
        production = int(row[b'logs:ProductionAmount'].decode('utf-8'))
        defects = int(row[b'logs:DefectivesProduced'].decode('utf-8'))
        efficiency = (production - defects) / production * 100 if production > 0 else 0
        machine_name = row[b'logs:MachineName'].decode('utf-8')
        
        if machine_name not in data:
            data[machine_name] = {
                'machine_name': machine_name,
                'production_amount': production,
                'defectives_produced': defects,
                'efficiency': efficiency
            }
    connection.close()
    return list(data.values())

def fetch_uptime_downtime(limit=5000):
    connection = connect_to_hbase()
    if not connection:
        return {}
    table = connection.table('machine_logs')
    uptime_data = {}
    for i, (key, row) in enumerate(table.scan(columns=[b'logs:MachineName', b'logs:StartTime', b'logs:EndTime', b'logs:MaintenanceStatus'])):
        if i >= limit:
            break
        machine = row[b'logs:MachineName'].decode('utf-8')
        start = datetime.strptime(row[b'logs:StartTime'].decode('utf-8'), '%Y-%m-%d %H:%M:%S')
        end = row.get(b'logs:EndTime', b'').decode('utf-8')
        end = datetime.strptime(end, '%Y-%m-%d %H:%M:%S') if end else datetime.now()
        status = row[b'logs:MaintenanceStatus'].decode('utf-8')
        duration = (end - start).total_seconds() / 3600  # Hours
        if machine not in uptime_data:
            uptime_data[machine] = {'uptime': 0, 'downtime': 0}
        if status.lower() == 'operational':
            uptime_data[machine]['uptime'] += duration
        else:
            uptime_data[machine]['downtime'] += duration
    connection.close()
    return uptime_data

def fetch_number_of_errors(limit=5000):
    connection = connect_to_hbase()
    if not connection:
        return {}
    table = connection.table('error_logs')
    error_counts = {}
    for i, (key, row) in enumerate(table.scan(columns=[b'logs:MachineName'])):
        if i >= limit:
            break
        machine = row[b'logs:MachineName'].decode('utf-8')
        error_counts[machine] = error_counts.get(machine, 0) + 1
    connection.close()
    return error_counts

def fetch_production_trend(limit=5000):
    connection = connect_to_hbase()
    if not connection:
        return {}
    table = connection.table('machine_logs')
    data = {}
    for i, (key, row) in enumerate(table.scan(columns=[b'logs:Date', b'logs:ProductionAmount', b'logs:DefectivesProduced'])):
        if i >= limit:
            break
        date = row[b'logs:Date'].decode('utf-8')
        production = int(row[b'logs:ProductionAmount'].decode('utf-8'))
        defects = int(row[b'logs:DefectivesProduced'].decode('utf-8'))
        if date not in data:
            data[date] = {'production': 0, 'defects': 0}
        data[date]['production'] += production
        data[date]['defects'] += defects
    connection.close()
    return data

def fetch_error_distribution(limit=100):
    # Connect to HBase (assuming the `connect_to_hbase` function is defined elsewhere)
    connection = connect_to_hbase()
    
    if not connection:
        return {}

    # Access the HBase table
    table = connection.table('error_logs')

    # Dictionary to store the error distribution by ErrorDesc
    error_dist = {}

    # Scan through the table (only looking at the 'ErrorDesc' column)
    for i, (key, row) in enumerate(table.scan(columns=[b'logs:ErrorDesc'])):
        if i >= limit:
            break

        # Get the error description, decode it to string
        error_desc = row[b'logs:ErrorDesc'].decode('utf-8')
        
        # Update the count for the specific error description
        error_dist[error_desc] = error_dist.get(error_desc, 0) + 1

    # Close the HBase connection
    connection.close()

    # Return the error distribution
    return error_dist

def fetch_maintenance_replacement(limit=5000):
    connection = connect_to_hbase()
    if not connection:
        return {}
    # Fetch errors
    error_table = connection.table('error_logs')
    error_counts = {}
    for i, (key, row) in enumerate(error_table.scan(columns=[b'logs:MachineName'])):
        if i >= limit:
            break
        machine = row[b'logs:MachineName'].decode('utf-8')
        error_counts[machine] = error_counts.get(machine, 0) + 1
    
    # Fetch machine health
    machine_table = connection.table('machine_logs')
    health_data = {}
    for i, (key, row) in enumerate(machine_table.scan(columns=[b'logs:MachineName', b'logs:MaintenanceStatus', b'logs:ErrorsReported'])):
        if i >= limit:
            break
        machine = row[b'logs:MachineName'].decode('utf-8')
        status = row[b'logs:MaintenanceStatus'].decode('utf-8')
        errors_reported = int(row[b'logs:ErrorsReported'].decode('utf-8'))
        error_freq = error_counts.get(machine, 0)
        maintenance_date = datetime.now() + timedelta(days=7) if error_freq > 5 or errors_reported > 5 else None
        replacement_date = datetime.now() + timedelta(days=30) if error_freq > 10 or errors_reported > 10 else None
        health_data[machine] = {
            'status': status,
            'errors_reported': errors_reported,
            'error_freq': error_freq,
            'maintenance_date': maintenance_date.strftime('%Y-%m-%d') if maintenance_date else 'N/A',
            'replacement_date': replacement_date.strftime('%Y-%m-%d') if replacement_date else 'N/A'
        }
    connection.close()
    return health_data

# Visualization Functions
def plot_efficiency(data):
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    machines = [d['machine_name'] for d in data]
    efficiencies = [d['efficiency'] for d in data]
    ax.bar(machines, efficiencies, color='teal')
    ax.set_title('Machine Efficiency (%)')
    ax.set_xlabel('Machine Name')
    ax.set_ylabel('Efficiency (%)')
    x_pos = range(len(machines))
    ax.set_xticks(x_pos)  # Set the x-tick positions
    ax.set_xticklabels(machines, rotation=45)
    plt.show()
    return get_chart_image(fig)

def plot_uptime_downtime(data):
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    machines = list(data.keys())
    uptime = [data[m]['uptime'] for m in machines]
    downtime = [data[m]['downtime'] for m in machines]
    bar_width = 0.35
    x = range(len(machines))
    ax.bar([i - bar_width/2 for i in x], uptime, bar_width, label='Uptime (hrs)', color='green')
    ax.bar([i + bar_width/2 for i in x], downtime, bar_width, label='Downtime (hrs)', color='red')
    ax.set_title('Machine Uptime vs Downtime')
    ax.set_xlabel('Machine Name')
    ax.set_xticks(x)
    ax.set_xticklabels(machines, rotation=45)
    ax.legend()
    plt.show()
    
    return get_chart_image(fig)

def plot_number_of_errors(data):
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    machines = list(data.keys())
    errors = [data[m] for m in machines]
    ax.bar(machines, errors, color='orange')
    ax.set_title('Number of Errors per Machine')
    ax.set_xlabel('Machine Name')
    ax.set_ylabel('Error Count')
    ax.set_xticklabels(machines, rotation=45)
    plt.show()
    
    return get_chart_image(fig)

def plot_production_trend(data):
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    dates = sorted(data.keys())
    production = [data[d]['production'] for d in dates]
    defects = [data[d]['defects'] for d in dates]
    ax.plot(dates, production, label='Production Amount', color='blue')
    ax.plot(dates, defects, label='Defectives Produced', color='red')
    ax.set_title('Production Trend Over Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('Count')
    ax.set_xticklabels(dates, rotation=45)
    ax.legend()
    plt.show()
    
    return get_chart_image(fig)

def plot_error_distribution(data):
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    errors = list(data.keys())
    counts = [data[e] for e in errors]
    ax.pie(counts, labels=errors, autopct='%1.1f%%', startangle=90)
    ax.set_title('Error Type Distribution')
    plt.show()
    
    return get_chart_image(fig)

def plot_maintenance_replacement(data):
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    machines = list(data.keys())
    error_freqs = [d['error_freq'] for d in data.values()]
    ax.bar(machines, error_freqs, color='purple')
    ax.set_title('Error Frequency with Maintenance/Replacement Suggestions')
    ax.set_xlabel('Machine Name')
    ax.set_ylabel('Error Frequency')
    ax.set_xticklabels(machines, rotation=45)
    plt.show()
    
    return get_chart_image(fig)

def get_chart_image(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"

# API Endpoint
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    dashboard_type = request.args.get('type')
    if not dashboard_type:
        return jsonify({'error': 'Dashboard type is required'}), 400

    dashboards = {
        'efficiency': (fetch_machine_efficiency, plot_efficiency),
        'uptime': (fetch_uptime_downtime, plot_uptime_downtime),
        'errors': (fetch_number_of_errors, plot_number_of_errors),
        'production_trend': (fetch_production_trend, plot_production_trend),
        'error_distribution': (fetch_error_distribution, plot_error_distribution),
        'maintenance_replacement': (fetch_maintenance_replacement, plot_maintenance_replacement)
    }

    if dashboard_type not in dashboards:
        return jsonify({'error': 'Invalid dashboard type'}), 400

    fetch_func, plot_func = dashboards[dashboard_type]
    data = fetch_func()
    chart = plot_func(data)
    return jsonify({'data': data, 'chart': chart})

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5001)
plot_efficiency(fetch_machine_efficiency())
plot_error_distribution(fetch_error_distribution())