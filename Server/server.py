#!/usr/bin/python3

from flask import Flask, render_template
from flask_socketio import SocketIO
import random
from threading import Thread
import time
import socket

app = Flask(__name__)
socketio = SocketIO(app)

devices = {
    "device1": {"x": 50, "y": 50},
    # "device2": {"x": 30, "y": 70},
}

def update_devices():
    while True:
        time.sleep(1)
        for device_id in devices:
            devices[device_id]["x"] = random.randint(0, 100)
            devices[device_id]["y"] = random.randint(0, 100)
        socketio.emit("update_devices", devices)

@app.route("/")
def index():
    return render_template("map.html")

data_for_triangulation = []

def coordinate_calculation():
    if len(data_for_triangulation) >= 3:
        print("\n[+] Performing triangulation with data:")
        for data in data_for_triangulation:
            print(data)
        # TODO: Implement triangulation algorithm here
    else:
        print(f"\n[!] Not enough data for triangulation. Current data points: {len(data_for_triangulation)}")

def rssi_process(input_line):
    try:
        gateway_id, device_mac, rssi = input_line.split(",")
        gateway_id = int(gateway_id)
        rssi = -int(rssi)

        found = False
        for i, device_data in enumerate(data_for_triangulation):
            if device_data[0] == gateway_id and device_data[1] == device_mac:
                data_for_triangulation[i][2] = rssi
                found = True
                break
        if not found:
            data_for_triangulation.append([gateway_id, device_mac, rssi])

        print(f"=== data_for_triangulation[{len(data_for_triangulation)}] ===".upper())
        for device in data_for_triangulation:
            print(device)

        coordinate_calculation()

    except Exception as e:
        print(f"[!] Error processing RSSI data: {e}")

def clear_triangulation_data():
    while True:
        time.sleep(10)
        print("[!] Clearing data_for_triangulation")
        data_for_triangulation.clear()

HOST = '0.0.0.0'
PORT = 8080

def handle_client(conn, addr):
    print(f"\n[+] Connected by {addr}")
    try:
        with conn:
            while True:
                try:
                    data = conn.recv(1024)
                    if not data:
                        print(f"[-] Connection closed by {addr}")
                        break
                    for line in data.decode().splitlines():
                        if line.strip():  # Проверяем, что строка не пустая после удаления пробельных символов
                            print(f"handle_client: [FROM {addr}] {line}")
                            rssi_process(line)
                except ConnectionResetError:
                    print(f"[!] Connection reset by {addr}")
                    break
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[!] Error in connection with {addr}: {e}")
                    break
    except Exception as e:
        print(f"[!] Connection handling error: {e}")
    finally:
        print(f"[~] Disconnected from {addr}")

def run_server():
    while True:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen(5)

            print(f"\n[+] Server listening on {HOST}:{PORT}")

            while True:
                try:
                    conn, addr = server.accept()
                    client_thread = Thread(target=handle_client, args=(conn, addr), daemon=True)
                    client_thread.start()
                except KeyboardInterrupt:
                    print("\n[!] Server shutdown requested")
                    server.close()
                    return
                except Exception as e:
                    print(f"[!] Accept error: {e}")
                    continue

        except Exception as e:
            print(f"[!] Server error: {e}")
            time.sleep(5)
            continue

if __name__ == "__main__":
    Thread(target=run_server, daemon=True).start()
    Thread(target=update_devices, daemon=True).start()
    Thread(target=clear_triangulation_data, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000)