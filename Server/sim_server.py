from flask import Flask, request, jsonify
from datetime import datetime
import threading

app = Flask(__name__)

# Store received data
received_data = []
data_lock = threading.Lock()

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    
    # Add timestamp and print to console
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_with_timestamp = {
        'timestamp': timestamp,
        'board_id': data.get('board_id'),
        'mac': data.get('mac'),
        'rssi': data.get('rssi')
    }
    
    with data_lock:
        received_data.append(data_with_timestamp)
    
    print(f"\nReceived data at {timestamp}:")
    print(f"Board ID: {data['board_id']}")
    print(f"MAC Address: {data['mac']}")
    print(f"RSSI: {data['rssi']}\n")
    
    return "OK", 200

@app.route('/data', methods=['GET'])
def get_data():
    with data_lock:
        return jsonify(received_data)

if __name__ == '__main__':
    print("Starting Bluetooth scanner server...")
    print("Listening for data from Wroom32 board...")
    app.run(host='0.0.0.0', port=5000)