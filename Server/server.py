#!/usr/bin/python3

from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Thread
import time
import socket
import numpy as np
from scipy.optimize import least_squares
import sys
import datetime
import os

# ================== Logger =======================

def setup_logging(log_file='program_log.txt'):
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file_handle = open(log_file, 'a+', encoding='utf-8')
    
    startup_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file_handle.write(f"\n\n=== SERVER STARTED [{startup_time}] ===\n")
    
    return log_file_handle

log_file = 'logs/server_logs.txt'
try:
    log_handle = setup_logging(log_file)
except Exception as e:
    print(f"[ERROR] - Logger: {e}")
    log_handle = None

def log_message(message, print_to_console=True):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    if print_to_console:
        print(message)
    
    if log_handle:
        try:
            log_handle.write(log_entry + "\n")
            log_handle.flush()
        except Exception as e:
            print(f"[ERROR] - Logger: {e}")


# =================================================


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
        log_message(f"Updated {device_name} coordinates to ({x}, {y})")
    else:
        devices[device_name] = {"x": x, "y": y}
        log_message(f"Added new device {device_name} with coordinates ({x}, {y})")

@app.route("/")
def index():
    gateways = {
        1: {"x": 0, "y": 0},
        2: {"x": 100, "y": 0},
        3: {"x": 0, "y": 100},
        4: {"x": 100, "y": 100},
    }
    return render_template("map.html", gateways=gateways)

# ============ TRIANGULATION ==================

def rssi_to_distance(rssi, rssi_at_1m=-60, path_loss_exponent=3):
    # d = 10^((RSSI_at_1m - RSSI) / (10 * n))
    return 10 ** ((rssi_at_1m - rssi) / (10 * path_loss_exponent))

def weighted_triangulation_error(point, receivers, distances):
    x, y = point
    error = []
    for (rx, ry), d in zip(receivers, distances):
        calculated_distance = np.sqrt((x - rx)**2 + (y - ry)**2)
        weight = 1 / (d + 0.001)
        error.append((calculated_distance - d) * weight)
    return error

def get_receiver_coords(receiver_id, n, m):
    gateways = {
        1: (0, 0),
        2: (n, 0),
        3: (0, m),
        4: (n, m),
    }
    return gateways.get(receiver_id)

def locate_device(receivers_data, n, m):
    receivers = []
    distances = []
    for receiver_id, mac, rssi in receivers_data:
        coords = get_receiver_coords(receiver_id, n, m)
        distance = rssi_to_distance(rssi)
        receivers.append(coords)
        distances.append(distance)

        log_message(f"[DEBUG]: MAC {mac}; ID {receiver_id}; DIST {distance}; RSSI {rssi}")

    if len(receivers) > 3:
        combined = list(zip(receivers, distances))
        combined.sort(key=lambda x: x[1])
        receivers, distances = zip(*combined[:3])

    if not receivers:
        return None, None

    initial_guess = np.mean(receivers, axis=0)

    result = least_squares(
        weighted_triangulation_error,
        initial_guess,
        args=(receivers, distances),
        method='lm'
    )

    estimated_x, estimated_y = result.x

    min_rx = min(r[0] for r in receivers)
    max_rx = max(r[0] for r in receivers)
    min_ry = min(r[1] for r in receivers)
    max_ry = max(r[1] for r in receivers)

    range_x = max_rx - min_rx
    range_y = max_ry - min_ry

    # Normalize 
    if range_x > 0:
        normalized_x = (estimated_x - min_rx) / range_x * n
    else:
        normalized_x = n / 2

    if range_y > 0:
        normalized_y = (estimated_y - min_ry) / range_y * m
    else:
        normalized_y = m / 2

    normalized_x = max(0, min(n, normalized_x))
    normalized_y = max(0, min(m, normalized_y))

    return normalized_x, normalized_y

# ++++++++++++++++++++++++++++++++++++++++++++++++++++

devices_rssi_data = {}

def coordinate_calculation(n=100, m=100):
    log_message("\n[+] Checking for devices to triangulate...")
    for device_mac, rssi_measurements in devices_rssi_data.items():
        log_message(f"GATEWAY[{rssi_measurements[0][0]}]\tMAC: {device_mac}\tRSSI: {rssi_measurements[0][1]}\tDIS: {round(rssi_to_distance(rssi_measurements[0][1]),2)}")
    for device_mac, rssi_measurements in devices_rssi_data.items():
        if len(rssi_measurements) >= 3:
            log_message(f"\n[+] Performing triangulation for device: {device_mac} with data:")
            receivers_data = []
            for gateway_id, rssi in rssi_measurements:
                log_message(f"    Gateway ID: {gateway_id}, RSSI: {rssi}")
                receivers_data.append([gateway_id, device_mac, rssi])

            try:
                x, y = locate_device(receivers_data, n, m)
                log_message(f"[+] Calculated coordinates for {device_mac}: ({x:.2f}, {y:.2f})")
                update_device_list(device_mac, x, y)
                log_message(devices)
            except Exception as e:
                log_message(f"[!] Error during triangulation for {device_mac}: {e}")
        else:
            log_message(f"[!] Not enough data for triangulation for device: {device_mac}. Current data points: {len(rssi_measurements)}")

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
        log_message(f"[!] Error parsing RSSI data: {e}. Expected format: gateway_id,device_mac,rssi")
    except Exception as e:
        log_message(f"[!] Unexpected error processing RSSI data: {e}")

def triangulation_handle():
    cycle_counter = 0
    while True:
        time.sleep(1)

        coordinate_calculation()
        log_message(f"--------- [{cycle_counter}] ---------")

        cycle_counter = (cycle_counter + 1) % 20
        if cycle_counter == 9:
            log_message("[!] Clearing devices_rssi_data")
            devices_rssi_data.clear()

HOST = '0.0.0.0'
PORT = 8080

def handle_client(conn, addr):
    log_message(f"\n[+] Connected by {addr}")
    try:
        with conn:
            while True:
                try:
                    data = conn.recv(1024)
                    if not data:
                        log_message(f"[-] Connection closed by {addr}")
                        break
                    for line in data.decode().splitlines():
                        if line.strip():
                            log_message(f"handle_client: [FROM {addr}] {line}")
                            rssi_process(line)
                except ConnectionResetError:
                    log_message(f"[!] Connection reset by {addr}")
                    break
                except socket.timeout:
                    continue
                except Exception as e:
                    log_message(f"[!] Error in connection with {addr}: {e}")
                    break
    except Exception as e:
        log_message(f"[!] Connection handling error: {e}")
    finally:
        log_message(f"[~] Disconnected from {addr}")

def run_server():
    while True:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen(5)

            log_message(f"\n[+] Server listening on {HOST}:{PORT}")

            while True:
                try:
                    conn, addr = server.accept()
                    client_thread = Thread(target=handle_client, args=(conn, addr), daemon=True)
                    client_thread.start()
                except KeyboardInterrupt:
                    log_message("\n[!] Server shutdown requested")
                    server.close()
                    return
                except Exception as e:
                    log_message(f"[!] Accept error: {e}")
                    continue

        except Exception as e:
            log_message(f"[!] Server error: {e}")
            time.sleep(5)
            continue

if __name__ == "__main__":
    Thread(target=run_server, daemon=True).start()
    Thread(target=update_devices, daemon=True).start()
    Thread(target=triangulation_handle, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000)

    if log_handle:
        log_handle.close()