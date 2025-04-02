from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here' 
   
# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['MINI_PROJECT']
machines_collection = db['machines']
usage_collection = db['machine_usage']

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    return User(username)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Demo account credentials
        if username == 'demo' and password == 'demo123':
            user = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials. Please use demo/demo123')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    machines = list(machines_collection.find({}, {'_id': 0}))
    active_usage = list(usage_collection.find({
        'worker': current_user.id,
        'end_time': None
    }))
    return render_template('dashboard.html', machines=machines, active_usage=active_usage)

@app.route('/api/start_machine', methods=['POST'])
@login_required
def start_machine():
    data = request.json
    machine_id = data.get('machine_id')
    purpose = data.get('purpose')
    stage = data.get('stage')
    
    usage_data = {
        'machine_id': machine_id,
        'worker': current_user.id,
        'purpose': purpose,
        'stage': stage,
        'start_time': datetime.now(),
        'end_time': None,
        'errors': []
    }
    
    usage_collection.insert_one(usage_data)
    return jsonify({'status': 'success'})

@app.route('/api/end_machine', methods=['POST'])
@login_required
def end_machine():
    data = request.json
    machine_id = data.get('machine_id')
    units_produced = data.get('units_produced')
    unit_of_measurement = data.get('unit_of_measurement')
    error_count = data.get('error_count')
    
    usage_collection.update_one(
        {
            'machine_id': machine_id,
            'worker': current_user.id,
            'end_time': None
        },
        {'$set': {
            'end_time': datetime.now(),
            'production_details': {
                'units_produced': units_produced,
                'unit_of_measurement': unit_of_measurement,
                'error_count': error_count
            }
        }}
    )
    return jsonify({'status': 'success'})
@app.route('/api/report_error', methods=['POST'])
@login_required
def report_error():
    data = request.json
    machine_id = data.get('machine_id')
    error_description = data.get('error_description')

    print(f"Received error report for Machine ID: {machine_id}, Description: {error_description}")  # Debugging

    
        
    usage_collection.insert_one({
            'machine_id': machine_id,
            'worker': "unknown",  
            'start_time': None,
            'end_time': None,
            'purpose': "Unknown",
            'stage': "Unknown",
            'errors': [{
                'description': error_description,
                'timestamp': datetime.now()
            }]
        })

    return jsonify({'status': 'success', 'message': 'Error reported successfully'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)