import os
import json
import socket
import threading
import hashlib
import time
import queue
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Cryptography imports
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives import serialization

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dh_aes_socket_secret_key_12345!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Helper for AES CBC encryption
def encrypt_aes(key, message_str):
    cipher = AES.new(key, AES.MODE_CBC)
    ciphertext = cipher.encrypt(pad(message_str.encode('utf-8'), AES.block_size))
    return cipher.iv + ciphertext

# Helper for AES CBC decryption
def decrypt_aes(key, encrypted_bytes):
    try:
        if len(encrypted_bytes) < AES.block_size:
            return "[Decryption Error: Payload too short]"
        iv = encrypted_bytes[:AES.block_size]
        ciphertext = encrypted_bytes[AES.block_size:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        return f"[Decryption Error: {str(e)}]"

# Helper to receive newline-separated JSON messages over TCP robustly
def receive_json_messages(sock):
    buffer = ""
    while True:
        try:
            data = sock.recv(8192)
            if not data:
                break
            buffer += data.decode('utf-8')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if line:
                    yield json.loads(line)
        except Exception:
            break

# Global state
active_web_clients = {}
active_web_clients_lock = threading.Lock()

# Logging helpers
def log_server_event(message):
    timestamp = time.strftime('%H:%M:%S')
    socketio.emit('server_log', {
        "message": f"[{timestamp}] {message}"
    })
    print(f"[SERVER] {message}")

def log_client_event(client_name, message):
    timestamp = time.strftime('%H:%M:%S')
    socketio.emit('client_log', {
        "client": client_name,
        "message": f"[{timestamp}] {message}"
    })
    print(f"[CLIENT - {client_name}] {message}")

def update_active_clients_list():
    with active_web_clients_lock:
        names = [info["name"] for cid, info in active_web_clients.items()]
    socketio.emit('active_clients', {
        "clients": names
    })

# ==========================================
# E2EE DIFFIE-HELLMAN-AES TCP SOCKET SERVER
# ==========================================

dh_aes_server_socket = None
dh_aes_server_thread = None
dh_aes_server_running = False
dh_parameters = None
clients_dh_aes = {}
clients_dh_aes_lock = threading.Lock()

def run_dh_aes_server():
    global dh_aes_server_socket, dh_aes_server_running, clients_dh_aes, dh_parameters
    log_server_event("Generating Diffie-Hellman parameters (1024-bit)...")
    dh_parameters = dh.generate_parameters(generator=2, key_size=1024)
    log_server_event("DH parameters generated successfully.")
    
    dh_aes_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    dh_aes_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        dh_aes_server_socket.bind(('127.0.0.1', 12346))
        dh_aes_server_socket.listen(5)
        log_server_event("Socket server listening on port 12346...")
    except Exception as e:
        log_server_event(f"Error binding to port 12346: {str(e)}")
        dh_aes_server_running = False
        return

    while dh_aes_server_running:
        try:
            dh_aes_server_socket.settimeout(1.0)
            client_socket, client_address = dh_aes_server_socket.accept()
            threading.Thread(
                target=handle_dh_aes_client,
                args=(client_socket, client_address),
                daemon=True
            ).start()
        except socket.timeout:
            continue
        except Exception as e:
            if dh_aes_server_running:
                log_server_event(f"Server exception: {str(e)}")
            break

    # Close client sockets
    with clients_dh_aes_lock:
        for sock in list(clients_dh_aes.keys()):
            try:
                sock.close()
            except:
                pass
        clients_dh_aes.clear()
        
    try:
        dh_aes_server_socket.close()
    except:
        pass
    log_server_event("Server socket closed.")

def send_to_client_by_name(recipient_name, payload):
    with clients_dh_aes_lock:
        for sock, info in clients_dh_aes.items():
            if info["name"] == recipient_name:
                try:
                    sock.send((json.dumps(payload) + '\n').encode('utf-8'))
                    return True
                except:
                    pass
    return False

def broadcast_client_list():
    with clients_dh_aes_lock:
        names = [info["name"] for info in clients_dh_aes.values()]
        sockets = list(clients_dh_aes.keys())
        
    payload = {
        "type": "client_list",
        "clients": names
    }
    
    for sock in sockets:
        try:
            sock.send((json.dumps(payload) + '\n').encode('utf-8'))
        except:
            pass
            
    # Also update web UI client list
    update_active_clients_list()

def handle_dh_aes_client(client_socket, client_address):
    global clients_dh_aes
    client_name = "Unknown"
    log_server_event(f"New TCP connection from {client_address[0]}:{client_address[1]}")
    
    try:
        msg_gen = receive_json_messages(client_socket)
        
        # Step 1: Send DH parameters to client
        parameters_pem = dh_parameters.parameter_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.ParameterFormat.PKCS3
        ).decode('utf-8')
        
        client_socket.send((json.dumps({
            "type": "parameters",
            "parameters": parameters_pem
        }) + '\n').encode('utf-8'))
        
        # Step 2: Wait for client registration
        try:
            reg_payload = next(msg_gen)
        except StopIteration:
            client_socket.close()
            return
            
        if reg_payload.get("type") == "register":
            client_name = reg_payload.get("name")
            
        with clients_dh_aes_lock:
            clients_dh_aes[client_socket] = {"name": client_name}
            
        log_server_event(f"Registered TCP client: '{client_name}'")
        
        # Broadcast updated client list to everyone
        broadcast_client_list()
        
        # Recv loop (acts as a blind relay)
        for payload in msg_gen:
            msg_type = payload.get("type")
            recipient = payload.get("recipient")
            
            if msg_type == "dh_exchange":
                # Relaying public DH exchange data
                log_server_event(f"Blindly relaying DH Public Key from '{client_name}' to '{recipient}'...")
                send_to_client_by_name(recipient, payload)
                
            elif msg_type == "message":
                # Relaying E2EE encrypted message
                ciphertext = payload.get("ciphertext")
                log_server_event(f"Relaying E2EE message from '{client_name}' to '{recipient}':")
                log_server_event(f"  Ciphertext (hex): {ciphertext[:40]}... (Server cannot decrypt)")
                send_to_client_by_name(recipient, payload)
                
    except Exception as e:
        log_server_event(f"Exception handling client {client_name}: {str(e)}")
    finally:
        with clients_dh_aes_lock:
            if client_socket in clients_dh_aes:
                del clients_dh_aes[client_socket]
        try:
            client_socket.close()
        except:
            pass
        log_server_event(f"Connection with client '{client_name}' closed.")
        broadcast_client_list()

# ==========================================
# E2EE CLIENT THREAD SIMULATION
# ==========================================

def run_dh_aes_client_thread(client_name):
    client_id = f"client_{client_name}"
    log_client_event(client_name, "Attempting to connect to TCP server...")
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect(('127.0.0.1', 12346))
        log_client_event(client_name, "Connected to Server.")
        
        msg_gen = receive_json_messages(client_socket)
        
        # Step 1: Receive DH parameters & server public key
        try:
            payload = next(msg_gen)
        except StopIteration:
            client_socket.close()
            return
            
        log_client_event(client_name, "Received DH parameters from Server.")
        loaded_parameters = serialization.load_pem_parameters(payload["parameters"].encode('utf-8'))
        
        # Step 2: Register Client name to server
        client_socket.send((json.dumps({
            "type": "register",
            "name": client_name
        }) + '\n').encode('utf-8'))
        log_client_event(client_name, "Sent registration name to Server.")
        
        # Step 3: Generate Client DH Key pair
        log_client_event(client_name, "Generating DH key pair...")
        client_private_key = loaded_parameters.generate_private_key()
        client_public_key = client_private_key.public_key()
        
        client_pub_pem = client_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        log_client_event(client_name, "DH key pair generated.")
        
        msg_queue = queue.Queue()
        e2ee_keys = {}  # recipient_name -> derived_aes_key
        sent_dh_to = set()  # set of names we sent public key to
        
        with active_web_clients_lock:
            active_web_clients[client_id] = {
                "socket": client_socket,
                "msg_queue": msg_queue,
                "name": client_name
            }
            
        update_active_clients_list()
        
        # E2EE Sender Loop Thread
        def sender_loop():
            while True:
                try:
                    msg_item = msg_queue.get()
                    if msg_item == "STOP":
                        break
                    recipient = msg_item["recipient"]
                    message = msg_item["message"]
                    
                    aes_key = e2ee_keys.get(recipient)
                    if aes_key:
                        # Encrypt message end-to-end
                        encrypted_bytes = encrypt_aes(aes_key, message)
                        
                        client_socket.send((json.dumps({
                            "type": "message",
                            "sender": client_name,
                            "recipient": recipient,
                            "ciphertext": encrypted_bytes.hex(),
                            "iv": encrypted_bytes[:16].hex()
                        }) + '\n').encode('utf-8'))
                        log_client_event(client_name, f"E2EE message encrypted and sent to {recipient}.")
                    else:
                        log_client_event(client_name, f"Error: No derived E2EE key for '{recipient}' yet!")
                except Exception as e:
                    log_client_event(client_name, f"Sender thread error: {str(e)}")
                    break

        threading.Thread(target=sender_loop, daemon=True).start()
        
        # E2EE Receiver Loop
        for payload in msg_gen:
            payload_type = payload.get("type")
            
            if payload_type == "client_list":
                other_clients = payload.get("clients", [])
                for other in other_clients:
                    if other != client_name and other not in e2ee_keys and other not in sent_dh_to:
                        # Initiate DH exchange with this client
                        log_client_event(client_name, f"Initiating E2EE DH key exchange with '{other}'...")
                        client_socket.send((json.dumps({
                            "type": "dh_exchange",
                            "sender": client_name,
                            "recipient": other,
                            "public_key": client_pub_pem
                        }) + '\n').encode('utf-8'))
                        sent_dh_to.add(other)
                        
            elif payload_type == "dh_exchange":
                sender = payload.get("sender")
                sender_pub_pem = payload.get("public_key")
                
                # Load sender's DH public key
                loaded_sender_pub_key = serialization.load_pem_public_key(sender_pub_pem.encode('utf-8'))
                
                # Derive shared secret E2EE
                shared_secret = client_private_key.exchange(loaded_sender_pub_key)
                aes_key = hashlib.sha256(shared_secret).digest()[:16]
                e2ee_keys[sender] = aes_key
                
                log_client_event(client_name, f"Derived E2EE AES key with '{sender}': {aes_key.hex()}")
                
                # If we haven't sent our DH public key to them, respond now
                if sender not in sent_dh_to:
                    log_client_event(client_name, f"Responding to E2EE DH exchange from '{sender}'...")
                    client_socket.send((json.dumps({
                        "type": "dh_exchange",
                        "sender": client_name,
                        "recipient": sender,
                        "public_key": client_pub_pem
                    }) + '\n').encode('utf-8'))
                    sent_dh_to.add(sender)
                    
                # Update UI elements
                socketio.emit('client_info_update', {
                    "client": client_name,
                    "aes_key": aes_key.hex(),
                    "dh_shared_secret": shared_secret.hex()
                })
                
            elif payload_type == "message":
                sender = payload.get("sender")
                ciphertext_hex = payload.get("ciphertext")
                iv_hex = payload.get("iv")
                
                ciphertext_bytes = bytes.fromhex(ciphertext_hex)
                aes_key = e2ee_keys.get(sender)
                
                if aes_key:
                    # Decrypt message locally on the client
                    decrypted_message = decrypt_aes(aes_key, ciphertext_bytes)
                    log_client_event(client_name, f"Decrypted E2EE message from '{sender}': '{decrypted_message}'")
                    
                    socketio.emit('client_message', {
                        "client": client_name,
                        "sender": sender,
                        "message": decrypted_message,
                        "raw_hex": ciphertext_hex,
                        "iv_hex": iv_hex
                    })
                else:
                    log_client_event(client_name, f"Error: Cannot decrypt message from '{sender}' - no key!")
                    
    except Exception as e:
        log_client_event(client_name, f"Receiver thread error: {str(e)}")
    finally:
        try:
            client_socket.close()
        except:
            pass
        with active_web_clients_lock:
            if client_id in active_web_clients:
                # Stop the sender loop thread
                active_web_clients[client_id]["msg_queue"].put("STOP")
                del active_web_clients[client_id]
        log_client_event(client_name, "Socket connection closed.")
        update_active_clients_list()

# ==========================================
# WEB APP ROUTES & SOCKETIO ENDPOINTS
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('get_status')
def handle_get_status():
    global dh_aes_server_running
    with active_web_clients_lock:
        dh_clients = [info["name"] for cid, info in active_web_clients.items()]
    emit('status_update', {
        "dh_aes_server": dh_aes_server_running,
        "dh_aes_clients": dh_clients
    })

@socketio.on('start_server')
def handle_start_server(data=None):
    global dh_aes_server_running, dh_aes_server_thread
    if dh_aes_server_running:
        log_server_event("Server is already running.")
        return
    dh_aes_server_running = True
    dh_aes_server_thread = threading.Thread(target=run_dh_aes_server, daemon=True)
    dh_aes_server_thread.start()
    log_server_event("Starting server socket thread...")

@socketio.on('stop_server')
def handle_stop_server(data=None):
    global dh_aes_server_running, dh_aes_server_socket
    if not dh_aes_server_running:
        return
    dh_aes_server_running = False
    if dh_aes_server_socket:
        try:
            dh_aes_server_socket.close()
        except:
            pass
    log_server_event("Signaled server to stop...")

@socketio.on('add_client')
def handle_add_client(data):
    client_name = data.get("name", "").strip()
    if not client_name:
        return
        
    client_id = f"client_{client_name}"
    with active_web_clients_lock:
        is_connected = client_id in active_web_clients
        
    if is_connected:
        emit('error_msg', {"message": f"Client '{client_name}' is already connected."})
        return
        
    if not dh_aes_server_running:
        emit('error_msg', {"message": "DH-AES Server is not running!"})
        return
    threading.Thread(target=run_dh_aes_client_thread, args=(client_name,), daemon=True).start()

@socketio.on('remove_client')
def handle_remove_client(data):
    client_name = data.get("name")
    client_id = f"client_{client_name}"
    with active_web_clients_lock:
        client_info = active_web_clients.get(client_id)
        
    if client_info:
        try:
            client_info["socket"].close()
        except:
            pass
        log_client_event(client_name, "Requested disconnection.")

@socketio.on('send_message')
def handle_send_message(data):
    sender = data.get("sender")
    recipient = data.get("recipient", "all")
    msg = data.get("message")
    
    client_id = f"client_{sender}"
    with active_web_clients_lock:
        client_info = active_web_clients.get(client_id)
        
    if client_info:
        client_info["msg_queue"].put({
            "recipient": recipient,
            "message": msg
        })

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
