#!/usr/bin/python3

import socket
import time

HOST = '0.0.0.0'
PORT = 8080

def run_server():
    while True:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            print(f"\nStarting server on {HOST}:{PORT}")
            server.bind((HOST, PORT))
            server.listen(1)
            print(f"Server listening on {HOST}:{PORT}")

            while True:
                try:
                    conn, addr = server.accept()
                    print(f"\nConnected by {addr}")
                    
                    try:
                        with conn:
                            while True:
                                try:
                                    data = conn.recv(1024)
                                    if not data:
                                        print(f"Connection closed by {addr}")
                                        break
                                    for line in data.decode().splitlines():
                                        if len(line) != 0:
                                            print(f"[FROM GATEWAY] {line}")
                                except ConnectionResetError:
                                    print(f"Connection reset by {addr}")
                                    break
                                except socket.timeout:
                                    continue
                                except Exception as e:
                                    print(f"Error in connection with {addr}: {e}")
                                    break
                    except Exception as e:
                        print(f"Connection handling error: {e}")
                    
                    print(f"Disconnected from {addr}. Waiting for new connection...")
                
                except KeyboardInterrupt:
                    print("\nServer shutdown requested")
                    server.close()
                    return
                except Exception as e:
                    print(f"Accept error: {e}")
                    server.close()
                    time.sleep(1)
                    break

        except Exception as e:
            print(f"Server error: {e}")
            time.sleep(5)
            continue

if __name__ == "__main__":
    run_server()