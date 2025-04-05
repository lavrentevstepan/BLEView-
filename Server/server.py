#!/usr/bin/python3

from flask import Flask, render_template
from flask_socketio import SocketIO
import random
from threading import Thread

import socket
import time


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

def rssi_process(input_line):
    try:
        gateway_id, device_mac, rssi = input_line.split(",")
        if len(data_for_triangulation) == 0:
            data_for_triangulation.append([int(gateway_id),device_mac,-int(rssi)])

        exist_flag = 1

        for device in data_for_triangulation:
            if device[0] == int(gateway_id) and device[1] == device_mac:
                device[2] = -int(rssi)
                exist_flag = 0
        if(exist_flag):
            data_for_triangulation.append([int(gateway_id),device_mac,-int(rssi)])
        
        print(f"=== data_for_triangulation[{len(data_for_triangulation)}] ===".upper())
        for device in data_for_triangulation:
            print(device)


    except Exception:
        print(Exception)


def coordinate_calculation():
    pass




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
                        if len(line) != 0:
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
    # run_server()
    Thread(target=run_server, daemon=True).start()
    Thread(target=update_devices, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000)