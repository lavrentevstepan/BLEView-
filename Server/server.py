#!/usr/bin/python3

from flask import Flask, render_template
from flask_socketio import SocketIO
import random
from threading import Thread
import time
import socket
import numpy as np
from scipy.optimize import least_squares

app = Flask(__name__)
socketio = SocketIO(app)

devices = {}

def update_devices():
    while True:
        time.sleep(1)
        socketio.emit("update_devices", devices)

def update_device_list(device_name, x, y):
    if device_name in devices:
        devices[device_name]["x"] = x
        devices[device_name]["y"] = y
        print(f"Updated {device_name} coordinates to ({x}, {y})")
    else:
        devices[device_name] = {"x": x, "y": y}
        print(f"Added new device {device_name} with coordinates ({x}, {y})")

@app.route("/")
def index():
    return render_template("map.html")

# ============ TRIANGULATION ==================

def get_receiver_coords(receiver_id, n, m):
    if receiver_id == 1:
        return (0, 0)
    elif receiver_id == 2:
        return (n, 0)
    elif receiver_id == 3:
        return (n, m)
    elif receiver_id == 4:
        return (0, m)
    else:
        raise ValueError("Invalid receiver ID")


def rssi_to_distance(rssi, rssi_at_1m=-50, path_loss_exponent=2):
    # d = 10^((RSSI_at_1m - RSSI) / (10 * n))
    return 10 ** ((rssi_at_1m - rssi) / (10 * path_loss_exponent))

def triangulation_error(point, receivers, distances):
    x, y = point
    error = []
    for (rx, ry), d in zip(receivers, distances):
        error.append(np.sqrt((x - rx)**2 + (y - ry)**2) - d)
    return error

def locate_device(receivers_data, n, m):
    receivers = []
    distances = []
    for receiver_id, mac, rssi in receivers_data:
        coords = get_receiver_coords(receiver_id, n, m)
        distance = rssi_to_distance(rssi)
        receivers.append(coords)
        distances.append(distance)

    if len(receivers) > 3:
        combined = list(zip(receivers, distances))
        combined.sort(key=lambda x: x[1])
        receivers, distances = zip(*combined[:3])

    initial_guess = np.mean(receivers, axis=0)

    result = least_squares(
        triangulation_error,
        initial_guess,
        args=(receivers, distances),
        method='lm'
    )

    x, y = result.x
    x = max(0, min(n, x))
    y = max(0, min(m, y))

    return x, y

# ++++++++++++++++++++++++++++++++++++++++++++++++++++

devices_rssi_data = {}

def coordinate_calculation(n=100, m=100):
    print("\n[+] Checking for devices to triangulate...")
    for item in devices_rssi_data:
        print(item)
    for device_mac, rssi_measurements in devices_rssi_data.items():
        if len(rssi_measurements) >= 3:
            print(f"\n[+] Performing triangulation for device: {device_mac} with data:")
            receivers_data = []
            for gateway_id, rssi in rssi_measurements:
                print(f"    Gateway ID: {gateway_id}, RSSI: {rssi}")
                receivers_data.append([gateway_id, device_mac, rssi])

            try:
                x, y = locate_device(receivers_data, n, m)
                print(f"[+] Calculated coordinates for {device_mac}: ({x:.2f}, {y:.2f})")
                update_device_list(device_mac, x, y)
                print(devices)
            except Exception as e:
                print(f"[!] Error during triangulation for {device_mac}: {e}")
        else:
            print(f"[!] Not enough data for triangulation for device: {device_mac}. Current data points: {len(rssi_measurements)}")

def rssi_process(input_line):
    try:
        gateway_id_str, device_mac, rssi_str = input_line.split(",")
        gateway_id = int(gateway_id_str)
        rssi = -int(rssi_str)

        if device_mac not in devices_rssi_data:
            devices_rssi_data[device_mac] = []
        else:
            devices_rssi_data[device_mac] = [
                data for data in devices_rssi_data[device_mac] if data[0] != gateway_id
            ]
        devices_rssi_data[device_mac].append((gateway_id, rssi))

    except ValueError as e:
        print(f"[!] Error parsing RSSI data: {e}. Expected format: gateway_id,device_mac,rssi")
    except Exception as e:
        print(f"[!] Unexpected error processing RSSI data: {e}")

def triangulation_handle():
    cycle_counter = 0
    while True:
        time.sleep(1)

        coordinate_calculation()
        print(f"================== [{cycle_counter}] ==================")

        cycle_counter = (cycle_counter + 1) % 20
        if cycle_counter == 9:
            print("[!] Clearing devices_rssi_data")
            devices_rssi_data.clear()

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
                        if line.strip():
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
    Thread(target=triangulation_handle, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000)