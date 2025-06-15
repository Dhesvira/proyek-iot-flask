from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
import datetime
import json
import csv
import os
from datetime import timezone, timedelta
from pathlib import Path # <-- Tambahkan import ini

# ================= PERBAIKAN FINAL UNTUK PATH TEMPLATES =================
# Menggunakan pathlib untuk path yang lebih andal di lingkungan serverless
BASE_DIR = Path(__file__).resolve().parent.parent
app = Flask(__name__, template_folder=BASE_DIR / 'templates')
# ========================================================================

# Path untuk file CSV di Vercel
CSV_FILE = '/tmp/sensor_log.csv'
CSV_HEADERS = [
    'server_timestamp', 
    'deviceId', 
    'temperature_celsius', 
    'humidity_percent', 
    'motion_detected', 
    'device_timestamp'
]

latest_data_store = {} 

def log_to_csv(data):
    """Fungsi untuk menyimpan data ke dalam file CSV di /tmp."""
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        
        if not file_exists:
            writer.writeheader()
            
        writer.writerow(data)

@app.route('/data', methods=['POST'])
def handle_data():
    global latest_data_store
    try:
        data_diterima = request.json
        wib = timezone(timedelta(hours=7))
        timestamp_server = datetime.datetime.now(wib).isoformat()
        
        device_id = data_diterima.get("deviceId", "unknown_device")
        current_data_point = data_diterima.copy()
        current_data_point['server_timestamp'] = timestamp_server
        latest_data_store[device_id] = {"latest": current_data_point}

        log_data = {
            'server_timestamp': timestamp_server,
            'deviceId': device_id,
            'temperature_celsius': data_diterima.get('temperature_celsius'),
            'humidity_percent': data_diterima.get('humidity_percent'),
            'motion_detected': data_diterima.get('motion_detected'),
            'device_timestamp': data_diterima.get('timestamp')
        }
        log_to_csv(log_data)

        return jsonify({"status": "sukses", "pesan": "Data diterima dan dicatat"}), 200
    except Exception as e:
        return jsonify({"status": "error", "pesan": str(e)}), 500

@app.route('/api/latest_data', methods=['GET'])
def get_latest_data():
    global latest_data_store
    return jsonify(latest_data_store)

@app.route('/')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/history')
def history_page():
    history_data = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            history_data = list(reader)
    return render_template('history.html', history_data=reversed(history_data))

@app.route('/download_csv')
def download_csv():
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True, download_name='sensor_log.csv')
    else:
        return "File log tidak ditemukan.", 404

# Rute untuk reset dan hapus log tetap sama
@app.route('/reset_log')
def reset_log():
    try:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
    except Exception:
        pass # Abaikan error jika file tidak ada
    return redirect(url_for('history_page'))

@app.route('/delete_log_file')
def delete_log_file():
    try:
        if os.path.exists(CSV_FILE):
            os.remove(CSV_FILE)
    except Exception:
        pass # Abaikan error jika file tidak ada
    return redirect(url_for('history_page'))