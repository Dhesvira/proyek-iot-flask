from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
import datetime
import json
import csv
import os
from datetime import timezone, timedelta

app = Flask(__name__)

# --- PENGATURAN DATABASE CSV ---
CSV_FILE = 'sensor_log.csv'
CSV_HEADERS = [
    'server_timestamp', 
    'deviceId', 
    'temperature_celsius', 
    'humidity_percent', 
    'motion_detected', 
    'device_timestamp'
]
# --------------------------------

# Variabel untuk menyimpan data terakhir per deviceId (real-time)
latest_data_store = {} 

def log_to_csv(data):
    """Fungsi untuk menyimpan data ke dalam file CSV."""
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        
        # Tulis header hanya jika file baru dibuat
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
            
            print(f"[{timestamp_server}] Data diterima ke /data:")
            print(json.dumps(data_diterima, indent=2))
            
            # --- Simpan data ke latest_data_store untuk tampilan real-time ---
            device_id = data_diterima.get("deviceId", "unknown_device")
            current_device_data = latest_data_store.get(device_id, {"history": []})
            current_data_point = data_diterima.copy()
            current_data_point['server_timestamp'] = timestamp_server
            current_device_data["latest"] = current_data_point
            latest_data_store[device_id] = current_device_data

            # --- LOGGING KE CSV ---
            log_data = {
                'server_timestamp': timestamp_server,
                'deviceId': device_id,
                'temperature_celsius': data_diterima.get('temperature_celsius'),
                'humidity_percent': data_diterima.get('humidity_percent'),
                'motion_detected': data_diterima.get('motion_detected'),
                'device_timestamp': data_diterima.get('timestamp')
            }
            log_to_csv(log_data)
            # ----------------------

            return jsonify({"status": "sukses", "pesan": "Data diterima dan dicatat"}), 200
        else:
            return jsonify({"status": "error", "pesan": "Content-Type harus application/json"}), 400
    except Exception as e:
        print(f"Error memproses request API di /data: {e}")
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
    # Balik urutan agar data terbaru ada di atas
    return render_template('history.html', history_data=reversed(history_data))

@app.route('/download_csv')
def download_csv():
    # Pastikan file ada sebelum mencoba mengirimnya
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    else:
        # Jika file tidak ada, kembalikan ke halaman history dengan pesan error (opsional)
        # Atau cukup kembalikan halaman kosong atau pesan error sederhana
        return "File log tidak ditemukan.", 404

# --- RUTE BARU UNTUK MERESET LOG ---
@app.route('/reset_log')
def reset_log():
    """Menghapus semua data dari file CSV, tetapi tetap mempertahankan file dan headernya."""
    try:
        # Buka file dalam mode 'w' untuk mengosongkan isinya
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            # Tulis kembali header
            writer.writeheader()
        print(f"Log data di {CSV_FILE} telah direset.")
    except Exception as e:
        print(f"Terjadi error saat mereset log: {e}")
    # Arahkan pengguna kembali ke halaman history
    return redirect(url_for('history_page'))

# --- RUTE BARU UNTUK MENGHAPUS FILE LOG ---
@app.route('/delete_log_file')
def delete_log_file():
    """Menghapus file log CSV secara permanen."""
    try:
        if os.path.exists(CSV_FILE):
            os.remove(CSV_FILE)
            print(f"File log {CSV_FILE} telah berhasil dihapus.")
        else:
            print(f"File log {CSV_FILE} tidak ditemukan, tidak ada yang dihapus.")
    except Exception as e:
        print(f"Terjadi error saat menghapus file log: {e}")
    # Arahkan pengguna kembali ke halaman history
    return redirect(url_for('history_page'))


if __name__ == '__main__':
    print("Menjalankan Flask API server di http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

