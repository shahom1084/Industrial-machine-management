from flask import Flask, jsonify, request
import logging
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
from datetime import datetime, timedelta
import seaborn as sns
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CSV File Paths (Update these paths based on your local setup)
MACHINE_LOGS_CSV = 'machine_logs.csv'
ERROR_LOGS_CSV = 'error_logs.csv'

# Data Fetching Functions
def fetch_machine_efficiency(limit=5000, filters=None):
    try:
        df = pd.read_csv(MACHINE_LOGS_CSV)
        logger.info("Loaded machine_logs.csv")
    except Exception as e:
        logger.error(f"Failed to load machine_logs.csv: {e}")
        return []

    # Apply filters if provided
    df = apply_filters(df, filters)

    # Limit the rows
    df = df.head(limit)

    # Group by MachineName and calculate efficiency
    data = {}
    for machine_name, group in df.groupby('MachineName'):
        production = group['ProductionAmount'].sum()
        defects = group['DefectivesProduced'].sum()
        efficiency = (production - defects) / production * 100 if production > 0 else 0
        date = group['Date'].iloc[0] if not group['Date'].empty else 'Unknown'
        
        data[machine_name] = {
            'machine_name': machine_name,
            'production_amount': production,
            'defectives_produced': defects,
            'efficiency': efficiency,
            'date': date
        }
    
    return list(data.values())

def fetch_uptime_downtime(limit=5000, filters=None):
    try:
        df = pd.read_csv(MACHINE_LOGS_CSV)
        logger.info("Loaded machine_logs.csv")
    except Exception as e:
        logger.error(f"Failed to load machine_logs.csv: {e}")
        return {}

    # Apply filters if provided
    df = apply_filters(df, filters)

    # Limit the rows
    df = df.head(limit)

    uptime_data = {}
    for _, row in df.iterrows():
        machine = row['MachineName']
        start = pd.to_datetime(row['StartTime'], errors='coerce')
        end = pd.to_datetime(row['EndTime'], errors='coerce') if pd.notna(row['EndTime']) else datetime.now()
        status = row['MaintenanceStatus']
        date = row.get('Date', 'Unknown')
        
        duration = (end - start).total_seconds() / 3600  # Hours
        
        if machine not in uptime_data:
            uptime_data[machine] = {'uptime': 0, 'downtime': 0, 'date': date, 'uptime_pct': 0}
            
        if status.lower() == 'operational':
            uptime_data[machine]['uptime'] += duration
        else:
            uptime_data[machine]['downtime'] += duration
            
        total_time = uptime_data[machine]['uptime'] + uptime_data[machine]['downtime']
        uptime_data[machine]['uptime_pct'] = (uptime_data[machine]['uptime'] / total_time * 100) if total_time > 0 else 0
        
    return uptime_data

def fetch_error_logs(limit=5000, filters=None):
    try:
        df = pd.read_csv(ERROR_LOGS_CSV)
        logger.info("Loaded error_logs.csv")
    except Exception as e:
        logger.error(f"Failed to load error_logs.csv: {e}")
        return []

    # Apply filters if provided
    df = apply_filters(df, filters)

    # Limit the rows
    df = df.head(limit)

    error_data = []
    for _, row in df.iterrows():
        error_data.append({
            'machine_name': row['MachineName'],
            'error_no': row['ErrorNo'],
            'error_desc': row['ErrorDesc'],
            'date': row.get('Date', 'Unknown'),
            'time': row.get('StartTime', 'Unknown')
        })
        
    return error_data

def fetch_error_distribution(limit=5000, filters=None):
    error_data = fetch_error_logs(limit, filters)
    error_dist = {}
    
    for error in error_data:
        error_desc = error['error_desc']
        error_dist[error_desc] = error_dist.get(error_desc, 0) + 1
        
    return error_dist

def fetch_error_frequency_by_machine(limit=5000, filters=None):
    error_data = fetch_error_logs(limit, filters)
    machine_errors = {}
    
    for error in error_data:
        machine = error['machine_name']
        machine_errors[machine] = machine_errors.get(machine, 0) + 1
        
    return machine_errors

def fetch_production_trend(limit=5000, filters=None):
    try:
        df = pd.read_csv(MACHINE_LOGS_CSV)
        logger.info("Loaded machine_logs.csv")
    except Exception as e:
        logger.error(f"Failed to load machine_logs.csv: {e}")
        return {}

    # Apply filters if provided
    df = apply_filters(df, filters)

    # Limit the rows
    df = df.head(limit)

    data = {}
    for _, row in df.iterrows():
        date = row['Date']
        production = int(row['ProductionAmount'])
        defects = int(row['DefectivesProduced'])
        machine = row['MachineName']
        
        if date not in data:
            data[date] = {'production': 0, 'defects': 0, 'machines': set()}
            
        data[date]['production'] += production
        data[date]['defects'] += defects
        data[date]['machines'].add(machine)
        
    # Convert sets to lists for JSON serialization
    for date in data:
        data[date]['machines'] = list(data[date]['machines'])
        
    return data

def fetch_maintenance_recommendation(limit=5000, filters=None):
    error_freq = fetch_error_frequency_by_machine(limit, filters)
    try:
        df = pd.read_csv(MACHINE_LOGS_CSV)
        logger.info("Loaded machine_logs.csv")
    except Exception as e:
        logger.error(f"Failed to load machine_logs.csv: {e}")
        return {}

    # Apply filters if provided
    df = apply_filters(df, filters)

    # Limit the rows
    df = df.head(limit)

    health_data = {}
    for _, row in df.iterrows():
        machine = row['MachineName']
        status = row['MaintenanceStatus']
        errors_reported = int(row['ErrorsReported'])
        date = row.get('Date', 'Unknown')
        
        error_freq_count = error_freq.get(machine, 0)
        
        # Determine maintenance needs
        maintenance_date = datetime.now() + timedelta(days=7) if error_freq_count > 5 or errors_reported > 5 else None
        replacement_date = datetime.now() + timedelta(days=30) if error_freq_count > 10 or errors_reported > 10 else None
        
        # Calculate health score (0-100)
        health_score = max(0, 100 - (error_freq_count * 5) - (errors_reported * 3))
        
        if machine not in health_data or errors_reported > health_data[machine]['errors_reported']:
            health_data[machine] = {
                'status': status,
                'errors_reported': errors_reported,
                'error_freq': error_freq_count,
                'health_score': health_score,
                'date': date,
                'maintenance_date': maintenance_date.strftime('%Y-%m-%d') if maintenance_date else 'N/A',
                'replacement_date': replacement_date.strftime('%Y-%m-%d') if replacement_date else 'N/A',
                'maintenance_required': maintenance_date is not None,
                'replacement_required': replacement_date is not None
            }
            
    return health_data

def fetch_manufacturing_stages(limit=5000, filters=None):
    try:
        df = pd.read_csv(MACHINE_LOGS_CSV)
        logger.info("Loaded machine_logs.csv")
    except Exception as e:
        logger.error(f"Failed to load machine_logs.csv: {e}")
        return {}

    # Apply filters if provided
    df = apply_filters(df, filters)

    # Limit the rows
    df = df.head(limit)

    stage_data = {}
    for _, row in df.iterrows():
        machine = row['MachineName']
        stage = row.get('ManufacturingStage', 'Unknown')
        production = int(row['ProductionAmount'])
        defects = int(row['DefectivesProduced'])
        
        if stage not in stage_data:
            stage_data[stage] = {
                'stage': stage,
                'machines': set(),
                'production': 0,
                'defects': 0
            }
            
        stage_data[stage]['machines'].add(machine)
        stage_data[stage]['production'] += production
        stage_data[stage]['defects'] += defects
        
    # Convert sets to lists for JSON serialization
    for stage in stage_data:
        stage_data[stage]['machines'] = list(stage_data[stage]['machines'])
        stage_data[stage]['defect_rate'] = (stage_data[stage]['defects'] / stage_data[stage]['production'] * 100) if stage_data[stage]['production'] > 0 else 0
        
    return stage_data

# Helper Functions
def apply_filters(df, filters):
    if not filters:
        return df
        
    # Date range filter
    if 'date_from' in filters and filters['date_from']:
        df = df[df['Date'] >= filters['date_from']]
    if 'date_to' in filters and filters['date_to']:
        df = df[df['Date'] <= filters['date_to']]
    
    # Machine name filter
    if 'machine_name' in filters and filters['machine_name']:
        df = df[df['MachineName'] == filters['machine_name']]
    
    # Manufacturing stage filter
    if 'stage' in filters and filters['stage']:
        df = df[df['ManufacturingStage'] == filters['stage']]
    
    # Maintenance status filter
    if 'status' in filters and filters['status']:
        df = df[df['MaintenanceStatus'] == filters['status']]
    
    # Error description filter (for error_logs.csv)
    if 'error_desc' in filters and filters['error_desc'] and 'ErrorDesc' in df.columns:
        df = df[df['ErrorDesc'] == filters['error_desc']]
    
    # Minimum errors filter
    if 'min_errors' in filters and filters['min_errors'] and 'ErrorsReported' in df.columns:
        df = df[df['ErrorsReported'] >= int(filters['min_errors'])]
    
    return df

def convert_to_dataframe(data, data_type):
    """Convert the data dictionary to a pandas DataFrame based on the type of data."""
    if data_type == 'efficiency':
        return pd.DataFrame(data)
    elif data_type == 'uptime':
        df_data = []
        for machine, values in data.items():
            df_data.append({
                'machine_name': machine,
                'uptime': values['uptime'],
                'downtime': values['downtime'],
                'uptime_pct': values['uptime_pct'],
                'date': values.get('date', 'Unknown')
            })
        return pd.DataFrame(df_data)
    elif data_type == 'error_distribution':
        df_data = []
        for error_desc, count in data.items():
            df_data.append({
                'error_desc': error_desc,
                'count': count
            })
        return pd.DataFrame(df_data)
    elif data_type == 'production_trend':
        df_data = []
        for date, values in data.items():
            df_data.append({
                'date': date,
                'production': values['production'],
                'defects': values['defects']
            })
        return pd.DataFrame(df_data).sort_values('date')
    elif data_type == 'maintenance':
        df_data = []
        for machine, values in data.items():
            df_data.append({
                'machine_name': machine,
                'status': values['status'],
                'errors_reported': values['errors_reported'],
                'error_freq': values['error_freq'],
                'health_score': values['health_score'],
                'maintenance_required': values['maintenance_required'],
                'replacement_required': values['replacement_required'],
                'date': values.get('date', 'Unknown')
            })
        return pd.DataFrame(df_data)
    elif data_type == 'manufacturing_stages':
        df_data = []
        for stage, values in data.items():
            df_data.append({
                'stage': stage,
                'production': values['production'],
                'defects': values['defects'],
                'defect_rate': values['defect_rate'],
                'machine_count': len(values['machines'])
            })
        return pd.DataFrame(df_data)
    else:
        return pd.DataFrame()

# Visualization Functions (unchanged from original)
def plot_efficiency_bar(data):
    df = convert_to_dataframe(data, 'efficiency')
    if df.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 8))
    df = df.sort_values('efficiency', ascending=False)
    colors = plt.cm.RdYlGn(df['efficiency']/100)
    bars = ax.bar(df['machine_name'], df['efficiency'], color=colors)
    ax.set_title('Machine Efficiency (%)', fontsize=16)
    ax.set_xlabel('Machine Name', fontsize=12)
    ax.set_ylabel('Efficiency (%)', fontsize=12)
    ax.set_ylim(0, 105)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    return fig

def plot_efficiency_gauge(data):
    df = convert_to_dataframe(data, 'efficiency')
    if df.empty:
        return None
    top_machines = df.sort_values('efficiency', ascending=False).head(6)
    fig, axs = plt.subplots(2, 3, figsize=(15, 10), subplot_kw=dict(polar=True))
    axs = axs.flatten()
    for i, (idx, row) in enumerate(top_machines.iterrows()):
        if i >= 6:
            break
        gauge_min, gauge_max = 0, 100
        efficiency = min(max(row['efficiency'], gauge_min), gauge_max)
        color = 'red' if efficiency < 60 else 'orange' if efficiency < 80 else 'green'
        angles = np.linspace(0, 2*np.pi, 100)
        angles = np.append(angles, angles[0])
        axs[i].plot(angles, [1]*101, color='lightgray', linewidth=15)
        value_angles = np.linspace(0, 2*np.pi * efficiency/100, 100)
        value_angles = np.append(value_angles, 0)
        value_data = [1]*len(value_angles)
        axs[i].plot(value_angles, value_data, color=color, linewidth=15)
        axs[i].spines['polar'].set_visible(False)
        axs[i].set_xticks([])
        axs[i].set_yticks([])
        axs[i].text(0, 0, f"{efficiency:.1f}%", ha='center', va='center', fontsize=20, fontweight='bold')
        axs[i].set_title(row['machine_name'], pad=20, fontsize=14)
    for i in range(len(top_machines), 6):
        axs[i].axis('off')
    plt.suptitle('Machine Efficiency Gauges (Top 6)', fontsize=18, y=0.98)
    plt.tight_layout()
    return fig

def plot_uptime_donut(data):
    df = convert_to_dataframe(data, 'uptime')
    if df.empty:
        return None
    top_machines = df.sort_values('uptime_pct', ascending=False).head(6)
    fig, axs = plt.subplots(2, 3, figsize=(15, 10))
    axs = axs.flatten()
    for i, (idx, row) in enumerate(top_machines.iterrows()):
        if i >= 6:
            break
        uptime = row['uptime']
        downtime = row['downtime']
        if uptime + downtime == 0:
            axs[i].text(0.5, 0.5, "No data", ha='center', va='center', fontsize=14)
            axs[i].axis('off')
            continue
        wedges, texts, autotexts = axs[i].pie(
            [uptime, downtime], 
            labels=['Uptime', 'Downtime'],
            autopct='%1.1f%%',
            colors=['green', 'red'],
            startangle=90,
            wedgeprops={'width': 0.4, 'edgecolor': 'w', 'linewidth': 2}
        )
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_fontweight('bold')
        axs[i].set_title(row['machine_name'], fontsize=12)
        axs[i].text(0, 0, f"Up: {uptime:.1f}h\nDown: {downtime:.1f}h", ha='center', va='center', fontsize=9)
    for i in range(len(top_machines), 6):
        axs[i].axis('off')
    plt.suptitle('Machine Uptime vs Downtime', fontsize=16, y=0.98)
    plt.tight_layout()
    return fig

def plot_uptime_area(data):
    df = convert_to_dataframe(data, 'uptime')
    if df.empty:
        return None
    df = df.sort_values('uptime_pct', ascending=False)
    fig, ax = plt.subplots(figsize=(12, 8))
    machines = df['machine_name']
    uptime = df['uptime']
    downtime = df['downtime']
    ax.fill_between(machines, 0, uptime, label='Uptime', color='green', alpha=0.7)
    ax.fill_between(machines, uptime, uptime + downtime, label='Downtime', color='red', alpha=0.7)
    ax.set_title('Machine Uptime vs Downtime Distribution', fontsize=16)
    ax.set_xlabel('Machine Name', fontsize=12)
    ax.set_ylabel('Hours', fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(loc='upper right', fontsize=10)
    for i, machine in enumerate(machines):
        total = uptime.iloc[i] + downtime.iloc[i]
        up_percent = (uptime.iloc[i] / total * 100) if total > 0 else 0
        down_percent = (downtime.iloc[i] / total * 100) if total > 0 else 0
        ax.text(i, uptime.iloc[i] / 2, f"{up_percent:.1f}%", 
                ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        ax.text(i, uptime.iloc[i] + downtime.iloc[i] / 2, f"{down_percent:.1f}%", 
                ha='center', va='center', fontsize=9, fontweight='bold', color='white')
    plt.tight_layout()
    return fig

def plot_error_pie(data):
    df = convert_to_dataframe(data, 'error_distribution')
    if df.empty:
        return None
    df = df.sort_values('count', ascending=False)
    if len(df) > 7:
        top_errors = df.head(7)
        other_count = df.iloc[7:]['count'].sum()
        df = pd.concat([top_errors, pd.DataFrame([{'error_desc': 'Other Errors', 'count': other_count}])])
    fig, ax = plt.subplots(figsize=(12, 9))
    wedges, texts, autotexts = ax.pie(
        df['count'],
        labels=df['error_desc'],
        autopct='%1.1f%%',
        startangle=90,
        shadow=True,
        explode=[0.05] * len(df),
        colors=plt.cm.tab10(np.linspace(0, 1, len(df)))
    )
    for text in texts:
        text.set_fontsize(11)
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')
    centre_circle = plt.Circle((0, 0), 0.5, fc='white')
    ax.add_patch(centre_circle)
    ax.set_title('Error Type Distribution', fontsize=16)
    ax.axis('equal')
    legend_labels = [f"{row['error_desc']} ({row['count']})" for _, row in df.iterrows()]
    ax.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0.5), fontsize=10)
    plt.tight_layout()
    return fig

def plot_error_heatmap(data):
    if not data:
        return None
    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], errors='coerce')
    df['date_only'] = df['datetime'].dt.date
    error_counts = df.groupby(['machine_name', 'date_only']).size().reset_index(name='error_count')
    pivot_df = error_counts.pivot(index='machine_name', columns='date_only', values='error_count').fillna(0)
    pivot_df['total'] = pivot_df.sum(axis=1)
    pivot_df = pivot_df.sort_values('total', ascending=False)
    pivot_df = pivot_df.drop(columns=['total'])
    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(
        pivot_df, 
        cmap='YlOrRd', 
        annot=True, 
        fmt='.0f',
        linewidths=0.5,
        ax=ax,
        cbar_kws={'label': 'Number of Errors'}
    )
    ax.set_title('Error Frequency by Machine and Date', fontsize=16)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Machine Name', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return fig

def plot_production_line(data):
    df = convert_to_dataframe(data, 'production_trend')
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    fig, ax1 = plt.subplots(figsize=(12, 8))
    color = 'tab:blue'
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Production Amount', color=color, fontsize=12)
    ax1.plot(df['date'], df['production'], color=color, marker='o', linewidth=2, markersize=8, label='Production')
    ax1.tick_params(axis='y', labelcolor=color)
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Defectives Produced', color=color, fontsize=12)
    ax2.plot(df['date'], df['defects'], color=color, marker='s', linewidth=2, markersize=8, label='Defectives')
    ax2.tick_params(axis='y', labelcolor=color)
    df['defect_rate'] = (df['defects'] / df['production'] * 100).round(1)
    for i, row in df.iterrows():
        ax1.annotate(f"{row['defect_rate']}%", 
                    (mdates.date2num(row['date']), row['production']),
                    xytext=(0, 10), textcoords='offset points',
                    ha='center', va='bottom', fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.7))
    ax1.set_title('Production and Defectives Trend Over Time', fontsize=16)
    ax1.grid(True, linestyle='--', alpha=0.7)
    date_format = mdates.DateFormatter('%Y-%m-%d')
    ax1.xaxis.set_major_formatter(date_format)
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(df)//10)))
    plt.xticks(rotation=45)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    plt.tight_layout()
    return fig

def plot_production_stacked(data):
    df = convert_to_dataframe(data, 'production_trend')
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    fig, ax = plt.subplots(figsize=(12, 8))
    df['good_production'] = df['production'] - df['defects']
    bar_width = 0.8
    x = range(len(df))
    good_bars = ax.bar(x, df['good_production'], bar_width, label='Good Production', color='green')
    defect_bars = ax.bar(x, df['defects'], bar_width, bottom=df['good_production'], label='Defectives', color='red')
    ax.set_title('Production Breakdown by Date', fontsize=16)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Units', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(df['date'].dt.strftime('%Y-%m-%d'), rotation=45, ha='right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.legend()
    for i, row in df.iterrows():
        good_pct = row['good_production'] / row['production'] * 100 if row['production'] > 0 else 0
        defect_pct = row['defects'] / row['production'] * 100 if row['production'] > 0 else 0
        if row['good_production'] > 0:
            ax.text(i, row['good_production']/2, f"{good_pct:.1f}%", 
                    ha='center', va='center', fontsize=9, color='white', fontweight='bold')
        if row['defects'] > 0:
            ax.text(i, row['good_production'] + row['defects']/2, f"{defect_pct:.1f}%", 
                    ha='center', va='center', fontsize=9, color='white', fontweight='bold')
    plt.tight_layout()
    return fig

def plot_maintenance_radar(data):
    df = convert_to_dataframe(data, 'maintenance')
    if df.empty:
        return None
    top_machines = df.sort_values('health_score').head(8)
    machines = top_machines['machine_name']
    health_scores = top_machines['health_score']
    N = len(machines)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    health_values = health_scores.tolist()
    health_values += health_values[:1]
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    plt.xticks(angles[:-1], machines, fontsize=10)
    ax.plot(angles, health_values, linewidth=2, linestyle='solid', label='Health Score')
    ax.fill(angles, health_values, alpha=0.25)
    ax.set_ylim(0, 100)
    for i in range(0, 101, 20):
        ax.fill(np.linspace(0, 2*np.pi, 100), 
                np.ones(100) * (i + 20),
                alpha=0.1, 
                color=plt.cm.RdYlGn(i/100))
    for angle, health, machine in zip(angles[:-1], health_values[:-1], machines):
        color = plt.cm.RdYlGn(health/100)
        maintenance = df.loc[df['machine_name'] == machine, 'maintenance_required'].values[0]
        replacement = df.loc[df['machine_name'] == machine, 'replacement_required'].values[0]
        marker = 'o' if not replacement else 'X' if replacement else 's'
        ax.scatter(angle, health, s=200, c=[color], marker=marker, edgecolor='black', linewidth=1.5, zorder=10)
        ax.text(angle, health + 5, f"{health:.0f}", horizontalalignment='center', verticalalignment='bottom',
                fontsize=9, fontweight='bold')
    ax.set_title('Machine Health Scores\n', fontsize=16, pad=20)
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Healthy'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='orange', markersize=10, label='Maintenance Needed'),
        Line2D([0], [0], marker='X', color='w', markerfacecolor='red', markersize=10, label='Replacement Needed')
    ]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.1, 0.1))
    plt.tight_layout()
    return fig

def plot_maintenance_bubble(data):
    df = convert_to_dataframe(data, 'maintenance')
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(12, 8))
    x = df['error_freq']
    y = df['errors_reported']
    size = 100 * (1 + (100 - df['health_score']) / 20)
    colors = ['red' if row['replacement_required'] else 'orange' if row['maintenance_required'] else 'green' for _, row in df.iterrows()]
    scatter = ax.scatter(x, y, s=size, c=colors, alpha=0.6, edgecolors='black')
    for i, (_, row) in enumerate(df.iterrows()):
        ax.annotate(row['machine_name'],
                   (row['error_freq'], row['errors_reported']),
                   xytext=(5, 5), textcoords='offset points',
                   fontsize=9)
    ax.set_title('Machine Maintenance Needs', fontsize=16)
    ax.set_xlabel('Error Frequency', fontsize=12)
    ax.set_ylabel('Errors Reported', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.axhline(y=5, color='orange', linestyle='--', alpha=0.7, label='Maintenance Threshold')
    ax.axhline(y=10, color='red', linestyle='--', alpha=0.7, label='Replacement Threshold')
    ax.axvline(x=5, color='orange', linestyle='--', alpha=0.7)
    ax.axvline(x=10, color='red', linestyle='--', alpha=0.7)
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Healthy'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Maintenance Needed'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='Replacement Needed')
    ]
    ax.legend(handles=legend_elements, loc='upper left')
    ax.text(7.5, 15, "Critical Zone\n(Replace)", color='darkred', fontsize=10, ha='center', fontweight='bold')
    ax.text(7.5, 7.5, "Warning Zone\n(Maintenance)", color='darkorange', fontsize=10, ha='center', fontweight='bold')
    ax.text(2.5, 2.5, "Safe Zone", color='darkgreen', fontsize=10, ha='center', fontweight='bold')
    plt.tight_layout()
    return fig

def plot_stage_treemap(data):
    df = convert_to_dataframe(data, 'manufacturing_stages')
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(12, 8))
    df = df.sort_values('production', ascending=False)
    sizes = df['production']
    labels = [f"{stage}\n{prod:,} units" for stage, prod in zip(df['stage'], df['production'])]
    colors = plt.cm.RdYlGn_r(df['defect_rate'] / df['defect_rate'].max())
    squarify = __import__('squarify')
    squarify.plot(sizes=sizes, label=labels, color=colors, alpha=0.8, edgecolor='white', linewidth=2, ax=ax)
    ax.axis('off')
    ax.set_title('Manufacturing Stages by Production Volume and Defect Rate', fontsize=16)
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    sm = ScalarMappable(cmap=plt.cm.RdYlGn_r, norm=Normalize(vmin=0, vmax=df['defect_rate'].max()))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label('Defect Rate (%)', rotation=270, labelpad=20)
    for i, (_, row) in enumerate(df.iterrows()):
        try:
            x, y = ax.patches[i].get_xy()
            width = ax.patches[i].get_width()
            height = ax.patches[i].get_height()
            ax.text(x + width/2, y + height/2, f"Defect: {row['defect_rate']:.1f}%",
                   ha='center', va='center', fontsize=10, fontweight='bold',
                   color='black')
        except:
            pass
    plt.tight_layout()
    return fig

def plot_error_pareto(data):
    df = convert_to_dataframe(data, 'error_distribution')
    if df.empty:
        return None
    df = df.sort_values('count', ascending=False)
    df['cumulative'] = df['count'].cumsum()
    df['cumulative_percent'] = df['cumulative'] / df['count'].sum() * 100
    fig, ax1 = plt.subplots(figsize=(12, 8))
    ax1.bar(df['error_desc'], df['count'], color='steelblue')
    ax1.set_xlabel('Error Description', fontsize=12)
    ax1.set_ylabel('Error Count', fontsize=12)
    ax1.tick_params(axis='x', rotation=45)
    ax2 = ax1.twinx()
    ax2.plot(df['error_desc'], df['cumulative_percent'], color='red', marker='o', linestyle='-', linewidth=2)
    ax2.set_ylabel('Cumulative Percentage', color='red', fontsize=12)
    ax2.set_ylim(0, 105)
    ax1.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.title('Error Pareto Analysis', fontsize=16)
    ax2.axhline(y=80, color='green', linestyle='--', alpha=0.7)
    ax2.text(0, 81, '80% Threshold', color='green', fontsize=10)
    for i, v in enumerate(df['count']):
        ax1.text(i, v + 0.5, str(v), ha='center', fontsize=9)
    plt.tight_layout()
    return fig

def get_chart_image(fig):
    if fig is None:
        return None
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{img_base64}"

# Main Application Functions (unchanged from original)
class IndustrialDashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Industrial Monitoring Dashboard")
        self.root.geometry("1200x800")
        self.current_figure = None
        self.current_data = None
        self.current_filters = {}
        self.current_vis_type = None
        
        self.create_menu_frame()
        self.create_filter_frame()
        self.create_chart_frame()
        
        self.show_machine_efficiency()
    
    def create_menu_frame(self):
        menu_frame = ttk.LabelFrame(self.root, text="Visualization Options")
        menu_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")
        ttk.Label(menu_frame, text="Select Visualization:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        vis_types = [
            ("Machine Efficiency (Bar Chart)", "efficiency_bar"),
            ("Machine Efficiency (Gauge Chart)", "efficiency_gauge"),
            ("Uptime vs Downtime (Donut Charts)", "uptime_donut"),
            ("Uptime vs Downtime (Area Chart)", "uptime_area"),
            ("Error Distribution (Pie Chart)", "error_pie"),
            ("Error Frequency (Heatmap)", "error_heatmap"),
            ("Production Trend (Line Chart)", "production_line"),
            ("Production Breakdown (Stacked Bar)", "production_stacked"),
            ("Machine Health (Radar Chart)", "maintenance_radar"),
            ("Maintenance Needs (Bubble Chart)", "maintenance_bubble"),
            ("Manufacturing Stages (Treemap)", "stage_treemap"),
            ("Error Analysis (Pareto Chart)", "error_pareto")
        ]
        self.vis_var = tk.StringVar(value="efficiency_bar")
        for i, (text, value) in enumerate(vis_types):
            ttk.Radiobutton(menu_frame, text=text, value=value, variable=self.vis_var).grid(
                row=i+1, column=0, padx=5, pady=2, sticky="w")
        ttk.Button(menu_frame, text="Show Visualization", command=self.update_visualization).grid(
            row=len(vis_types)+1, column=0, padx=5, pady=10, sticky="w")
    
    def create_filter_frame(self):
        filter_frame = ttk.LabelFrame(self.root, text="Filter Options")
        filter_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        ttk.Label(filter_frame, text="Date Range:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(filter_frame, text="From:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.date_from_entry = ttk.Entry(filter_frame, width=12)
        self.date_from_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(filter_frame, text="To:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.date_to_entry = ttk.Entry(filter_frame, width=12)
        self.date_to_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(filter_frame, text="Machine Name:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.machine_entry = ttk.Entry(filter_frame, width=15)
        self.machine_entry.grid(row=3, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(filter_frame, text="Manufacturing Stage:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.stage_entry = ttk.Entry(filter_frame, width=15)
        self.stage_entry.grid(row=4, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(filter_frame, text="Maintenance Status:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.status_var = tk.StringVar()
        status_combobox = ttk.Combobox(filter_frame, textvariable=self.status_var, width=12)
        status_combobox['values'] = ('', 'Operational', 'Maintenance', 'Breakdown')
        status_combobox.grid(row=5, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(filter_frame, text="Error Description:").grid(row=6, column=0, padx=5, pady=5, sticky="w")
        self.error_desc_entry = ttk.Entry(filter_frame, width=15)
        self.error_desc_entry.grid(row=6, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(filter_frame, text="Min. Errors:").grid(row=7, column=0, padx=5, pady=5, sticky="w")
        self.min_errors_entry = ttk.Entry(filter_frame, width=5)
        self.min_errors_entry.grid(row=7, column=1, padx=5, pady=2, sticky="w")
        ttk.Button(filter_frame, text="Apply Filters", command=self.apply_filters).grid(
            row=8, column=0, columnspan=2, padx=5, pady=10, sticky="w")
        ttk.Button(filter_frame, text="Reset Filters", command=self.reset_filters).grid(
            row=9, column=0, columnspan=2, padx=5, pady=5, sticky="w")
    
    def create_chart_frame(self):
        chart_frame = ttk.LabelFrame(self.root, text="Visualization")
        chart_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.chart_container = ttk.Frame(chart_frame)
        self.chart_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def update_visualization(self):
        vis_type = self.vis_var.get()
        self.current_vis_type = vis_type
        for widget in self.chart_container.winfo_children():
            widget.destroy()
        if vis_type == "efficiency_bar":
            self.show_machine_efficiency()
        elif vis_type == "efficiency_gauge":
            self.show_efficiency_gauge()
        elif vis_type == "uptime_donut":
            self.show_uptime_donut()
        elif vis_type == "uptime_area":
            self.show_uptime_area()
        elif vis_type == "error_pie":
            self.show_error_pie()
        elif vis_type == "error_heatmap":
            self.show_error_heatmap()
        elif vis_type == "production_line":
            self.show_production_line()
        elif vis_type == "production_stacked":
            self.show_production_stacked()
        elif vis_type == "maintenance_radar":
            self.show_maintenance_radar()
        elif vis_type == "maintenance_bubble":
            self.show_maintenance_bubble()
        elif vis_type == "stage_treemap":
            self.show_stage_treemap()
        elif vis_type == "error_pareto":
            self.show_error_pareto()
    
    def apply_filters(self):
        filters = {}
        date_from = self.date_from_entry.get().strip()
        date_to = self.date_to_entry.get().strip()
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        machine = self.machine_entry.get().strip()
        if machine:
            filters['machine_name'] = machine
        stage = self.stage_entry.get().strip()
        if stage:
            filters['stage'] = stage
        status = self.status_var.get().strip()
        if status:
            filters['status'] = status
        error_desc = self.error_desc_entry.get().strip()
        if error_desc:
            filters['error_desc'] = error_desc
        min_errors = self.min_errors_entry.get().strip()
        if min_errors and min_errors.isdigit():
            filters['min_errors'] = min_errors
        self.current_filters = filters
        self.update_visualization()
    
    def reset_filters(self):
        self.date_from_entry.delete(0, tk.END)
        self.date_to_entry.delete(0, tk.END)
        self.machine_entry.delete(0, tk.END)
        self.stage_entry.delete(0, tk.END)
        self.status_var.set('')
        self.error_desc_entry.delete(0, tk.END)
        self.min_errors_entry.delete(0, tk.END)
        self.current_filters = {}
        self.update_visualization()
    
    def display_chart(self, figure):
        for widget in self.chart_container.winfo_children():
            widget.destroy()
        if figure:
            canvas = FigureCanvasTkAgg(figure, master=self.chart_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.current_figure = figure
        else:
            ttk.Label(self.chart_container, text="No data available for the selected filters.").pack(padx=20, pady=20)
    
    def show_machine_efficiency(self):
        data = fetch_machine_efficiency(filters=self.current_filters)
        self.current_data = data
        figure = plot_efficiency_bar(data)
        self.display_chart(figure)
    
    def show_efficiency_gauge(self):
        data = fetch_machine_efficiency(filters=self.current_filters)
        self.current_data = data
        figure = plot_efficiency_gauge(data)
        self.display_chart(figure)
    
    def show_uptime_donut(self):
        data = fetch_uptime_downtime(filters=self.current_filters)
        self.current_data = data
        figure = plot_uptime_donut(data)
        self.display_chart(figure)
    
    def show_uptime_area(self):
        data = fetch_uptime_downtime(filters=self.current_filters)
        self.current_data = data
        figure = plot_uptime_area(data)
        self.display_chart(figure)
    
    def show_error_pie(self):
        data = fetch_error_distribution(filters=self.current_filters)
        self.current_data = data
        figure = plot_error_pie(data)
        self.display_chart(figure)
    
    def show_error_heatmap(self):
        data = fetch_error_logs(filters=self.current_filters)
        self.current_data = data
        figure = plot_error_heatmap(data)
        self.display_chart(figure)
    
    def show_production_line(self):
        data = fetch_production_trend(filters=self.current_filters)
        self.current_data = data
        figure = plot_production_line(data)
        self.display_chart(figure)
    
    def show_production_stacked(self):
        data = fetch_production_trend(filters=self.current_filters)
        self.current_data = data
        figure = plot_production_stacked(data)
        self.display_chart(figure)
    
    def show_maintenance_radar(self):
        data = fetch_maintenance_recommendation(filters=self.current_filters)
        self.current_data = data
        figure = plot_maintenance_radar(data)
        self.display_chart(figure)
    
    def show_maintenance_bubble(self):
        data = fetch_maintenance_recommendation(filters=self.current_filters)
        self.current_data = data
        figure = plot_maintenance_bubble(data)
        self.display_chart(figure)
    
    def show_stage_treemap(self):
        data = fetch_manufacturing_stages(filters=self.current_filters)
        self.current_data = data
        figure = plot_stage_treemap(data)
        self.display_chart(figure)
    
    def show_error_pareto(self):
        data = fetch_error_distribution(filters=self.current_filters)
        self.current_data = data
        figure = plot_error_pareto(data)
        self.display_chart(figure)

def main():
    root = tk.Tk()
    app = IndustrialDashboardApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()