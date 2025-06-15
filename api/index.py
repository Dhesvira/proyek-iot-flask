from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
import datetime
import json
import csv
import os
from datetime import timezone, timedelta

# ================= FIX 1: Path Absolut untuk Folder Templates =================
# Ini adalah perbaikan utama untuk error 404 NOT FOUND.
# Kita membuat path yang pasti ke folder 'templates' agar Vercel tidak bingung.
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)
# ============================================================================

# ================= FIX 2: Path Penyimpanan CSV untuk Vercel =================
    # Vercel hanya mengizinkan penulisan file di folder sementara '/tmp'.
# Jika tidak diubah, logging ke CSV akan gagal.
CSV_FILE = '/tmp/sensor_log.csv'
# ============================================================================

CSV_HEADERS = [
    'server_timestamp', 
    'deviceId', 
    'temperature_celsius', 
    'humidity_percent', 
    'motion_detected', 
    'device_timestamp'
]

# Variabel ini akan di-reset setiap kali serverless function dipanggil ulang.
# Untuk data yang benar-benar persisten, diperlukan database eksternal (misal: Vercel KV).
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
        content_type = request.headers.get('Content-Type')
        if (content_type == 'application/json'):
            data_diterima = request.json
            wib = timezone(timedelta(hours=7))
            timestamp_server = datetime.datetime.now(wib).isoformat()
            
            device_id = data_diterima.get("deviceId", "unknown_device")
            current_device_data = latest_data_store.get(device_id, {"history": []})
            current_data_point = data_diterima.copy()
            current_data_point['server_timestamp'] = timestamp_server
            current_device_data["latest"] = current_data_point
            latest_data_store[device_id] = current_device_data

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
        else:
            return jsonify({"status": "error", "pesan": "Content-Type harus application/json"}), 400
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

@app.route('/reset_log')
def reset_log():
    try:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
    except Exception as e:
        print(f"Terjadi error saat mereset log: {e}")
    return redirect(url_for('history_page'))

@app.route('/delete_log_file')
def delete_log_file():
    try:
        if os.path.exists(CSV_FILE):
            os.remove(CSV_FILE)
    except Exception as e:
        print(f"Terjadi error saat menghapus file log: {e}")
    return redirect(url_for('history_page'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)