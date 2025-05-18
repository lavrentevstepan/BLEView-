#!/usr/bin/python3

import socket
import random
import time
import threading

SERVER_HOST = 'localhost'
SERVER_PORT = 8080
DEVICE_ID = '26881b2db72a'
INTERVAL = 5

threads = {}
stop_events = {}

def simulate_device(deviceid, stop_event):
    while not stop_event.is_set():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect((SERVER_HOST, SERVER_PORT))
                    print(f"Device {deviceid} connected to server at {SERVER_HOST}:{SERVER_PORT}")
                    
                    while not stop_event.is_set():
                        try:
                            value = random.randint(30, 99)
                            message = f"{deviceid},{DEVICE_ID},{value}\n"
                            
                            s.sendall(message.encode())
                            print(f"Device {deviceid} sent: {message.strip()}")
                            
                            time.sleep(INTERVAL)
                            
                        except ConnectionResetError:
                            print(f"Device {deviceid}: Connection reset by server. Reconnecting...")
                            break
                        except BrokenPipeError:
                            print(f"Device {deviceid}: Connection broken. Reconnecting...")
                            break
                        except Exception as e:
                            print(f"Device {deviceid}: Error during communication: {e}")
                            break
                            
                except ConnectionRefusedError:
                    print(f"Device {deviceid}: Server at {SERVER_HOST}:{SERVER_PORT} not available. Retrying in 5 seconds...")
                    time.sleep(5)
                except Exception as e:
                    print(f"Device {deviceid}: Connection error: {e}. Retrying in 5 seconds...")
                    time.sleep(5)
                    
        except Exception as e:
            print(f"Device {deviceid}: Unexpected error: {e}. Restarting simulator...")
            time.sleep(5)

if __name__ == "__main__":
    print(f"Starting device simulator with ID {DEVICE_ID}")
    print(f"Will send data every {INTERVAL} seconds to {SERVER_HOST}:{SERVER_PORT}")
    
    num_devices = 4
    for i in range(num_devices):
        stop_events[i+1] = threading.Event()
        thread = threading.Thread(target=simulate_device, args=(i+1, stop_events[i+1]))
        thread.daemon = True
        threads[i+1] = thread
        thread.start()
        time.sleep(0.2)
    
    print("\nCommands:")
    print("Enter device number (1-4) to stop that device")
    print("Enter 'q' to quit all devices")
    
    try:
        while True:
            cmd = input("\nEnter command (1-4 or q): ").strip().lower()
            if cmd == 'q':
                print("Stopping all devices...")
                for event in stop_events.values():
                    event.set()
                break
            elif cmd.isdigit():
                device_num = int(cmd)
                if device_num in threads:
                    print(f"Stopping device {device_num}...")
                    stop_events[device_num].set()
                    threads[device_num].join(timeout=1)
                    del threads[device_num]
                    del stop_events[device_num]
                    print(f"Device {device_num} stopped")
                else:
                    print(f"Device {device_num} not found or already stopped")
            else:
                print("Invalid command. Enter a number (1-4) or 'q'")
                
            if threads:
                print(f"Running devices: {sorted(threads.keys())}")
            else:
                print("No devices running")
                break
                
    except KeyboardInterrupt:
        print("\nStopping all devices...")
        for event in stop_events.values():
            event.set()
    finally:
        print("Device simulator stopped")