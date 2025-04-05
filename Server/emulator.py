#!/usr/bin/python3

import socket
import random
import time
import threading

SERVER_HOST = 'localhost'
SERVER_PORT = 8080
DEVICE_ID = '48872d9cfb38'
INTERVAL = 5

def simulate_device(deviceid):
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect((SERVER_HOST, SERVER_PORT))
                    print(f"Connected to server at {SERVER_HOST}:{SERVER_PORT}")
                    
                    while True:
                        try:
                            value = random.randint(30, 99)
                            message = f"{deviceid},{DEVICE_ID},{value}\n"
                            
                            s.sendall(message.encode())
                            print(f"Sent: {message.strip()}")
                            
                            time.sleep(INTERVAL)
                            
                        except ConnectionResetError:
                            print("Connection reset by server. Reconnecting...")
                            break
                        except BrokenPipeError:
                            print("Connection broken. Reconnecting...")
                            break
                        except Exception as e:
                            print(f"Error during communication: {e}")
                            break
                            
                except ConnectionRefusedError:
                    print(f"Server at {SERVER_HOST}:{SERVER_PORT} not available. Retrying in 5 seconds...")
                    time.sleep(5)
                except Exception as e:
                    print(f"Connection error: {e}. Retrying in 5 seconds...")
                    time.sleep(5)
                    
        except Exception as e:
            print(f"Unexpected error: {e}. Restarting simulator...")
            time.sleep(5)

if __name__ == "__main__":
    print(f"Starting device simulator with ID {DEVICE_ID}")
    print(f"Will send data every {INTERVAL} seconds to {SERVER_HOST}:{SERVER_PORT}")
    
    num_devices = 4
    for i in range(num_devices):
        thread = threading.Thread(target=simulate_device, args=(i+1,))
        thread.daemon = True
        thread.start()
        time.sleep(0.2)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping device simulator...")