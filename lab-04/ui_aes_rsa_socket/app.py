import os
import json
import socket
import threading
import time
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Cryptography imports
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

app = Flask(__name__)
app.config['SECRET_KEY'] = 'aes_rsa_socket_secret_key_12345!'
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
# AES-RSA TCP SOCKET SERVER
# ==========================================

aes_rsa_server_socket = None
aes_rsa_server_thread = None
aes_rsa_server_running = False
clients_aes_rsa = {}
clients_aes_rsa_lock = threading.Lock()

def run_aes_rsa_server():
    global aes_rsa_server_socket, aes_rsa_server_running, clients_aes_rsa
    log_server_event("Generating server RSA keypair (2048-bit)...")
    server_key = RSA.generate(2048)
    server_pub_pem = server_key.publickey().export_key(format='PEM').decode('utf-8')
    
    log_server_event("Server RSA Keys generated successfully.")
    
    aes_rsa_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    aes_rsa_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        aes_rsa_server_socket.bind(('127.0.0.1', 12345))
        aes_rsa_server_socket.listen(5)
        log_server_event("Socket server listening on port 12345...")
    except Exception as e:
        log_server_event(f"Error binding to port 12345: {str(e)}")
        aes_rsa_server_running = False
        return

    while aes_rsa_server_running:
        try:
            aes_rsa_server_socket.settimeout(1.0)
            client_socket, client_address = aes_rsa_server_socket.accept()
            threading.Thread(
                target=handle_aes_rsa_client,
                args=(client_socket, client_address, server_key),
                daemon=True
            ).start()
        except socket.timeout:
            continue
        except Exception as e:
            if aes_rsa_server_running:
                log_server_event(f"Server exception: {str(e)}")
            break

    # Close all connected sockets
    with clients_aes_rsa_lock:
        for sock in list(clients_aes_rsa.keys()):
            try:
                sock.close()
            except:
                pass
        clients_aes_rsa.clear()
    
    try:
        aes_rsa_server_socket.close()
    except:
        pass
    log_server_event("Server socket closed.")

def handle_aes_rsa_client(client_socket, client_address, server_key):
    global clients_aes_rsa
    client_name = "Unknown"
    log_server_event(f"New TCP connection from {client_address[0]}:{client_address[1]}")
    
    try:
        # Step 1: Send server public key (PEM)
        server_pub_pem = server_key.publickey().export_key(format='PEM')
        client_socket.send(server_pub_pem)
        log_server_event("Handshake: Sent Server RSA Public Key (PEM)")
        
        # Step 2: Receive client name & public key
        client_data_raw = client_socket.recv(4096)
        if not client_data_raw:
            client_socket.close()
            return
            
        try:
            client_data = json.loads(client_data_raw.decode('utf-8'))
            client_name = client_data.get("name", "Unknown")
            client_pub_pem = client_data.get("public_key")
        except Exception:
            client_name = f"Client_{client_address[1]}"
            client_pub_pem = client_data_raw.decode('utf-8')
            
        log_server_event(f"Handshake: Received Public Key and Client Name: '{client_name}'")
        client_received_key = RSA.import_key(client_pub_pem)
        
        # Step 3: Generate AES key (16 bytes / 128 bits)
        aes_key = get_random_bytes(16)
        log_server_event(f"Handshake: Generated Session AES Key for {client_name}: {aes_key.hex()}")
        
        # Step 4: Encrypt AES key using Client's Public Key (PKCS1_OAEP)
        cipher_rsa = PKCS1_OAEP.new(client_received_key)
        encrypted_aes_key = cipher_rsa.encrypt(aes_key)
        
        # Send encrypted AES key
        client_socket.send(encrypted_aes_key)
        log_server_event(f"Handshake: Sent Encrypted AES key to {client_name}")
        
        with clients_aes_rsa_lock:
            clients_aes_rsa[client_socket] = {"name": client_name, "aes_key": aes_key}
            
        update_active_clients_list()
        log_server_event(f"Handshake with '{client_name}' completed. SECURE CHANNEL ACTIVE.")
        
        # Step 5: Recv loop
        while True:
            encrypted_payload = client_socket.recv(2048)
            if not encrypted_payload:
                break
                
            decrypted_message = decrypt_aes(aes_key, encrypted_payload)
            log_server_event(f"Received from {client_name} - Ciphertext(hex): {encrypted_payload.hex()}")
            log_server_event(f"Received from {client_name} - Decrypted: '{decrypted_message}'")
            
            if decrypted_message == "exit":
                break
                
            recipient = None
            msg_content = decrypted_message
            if ":" in decrypted_message:
                parts = decrypted_message.split(":", 1)
                recipient = parts[0].strip()
                msg_content = parts[1].strip()
                
            # Relay messages
            with clients_aes_rsa_lock:
                for target_sock, info in clients_aes_rsa.items():
                    is_target = False
                    if recipient and recipient != "all":
                        if info["name"].lower() == recipient.lower() and target_sock != client_socket:
                            is_target = True
                    else:
                        if target_sock != client_socket:
                            is_target = True
                            
                    if is_target:
                        relay_str = f"{client_name}: {msg_content}"
                        encrypted_relay = encrypt_aes(info["aes_key"], relay_str)
                        target_sock.send(encrypted_relay)
                        log_server_event(f"Relaying message to {info['name']}. Re-encrypting with their AES key.")
                        
    except Exception as e:
        log_server_event(f"Exception handling client {client_name}: {str(e)}")
    finally:
        with clients_aes_rsa_lock:
            if client_socket in clients_aes_rsa:
                del clients_aes_rsa[client_socket]
        try:
            client_socket.close()
        except:
            pass
        log_server_event(f"Connection with client '{client_name}' closed.")
        update_active_clients_list()

def run_aes_rsa_client_thread(client_name):
    client_id = f"client_{client_name}"
    log_client_event(client_name, "Attempting to connect to TCP server...")
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect(('127.0.0.1', 12345))
        log_client_event(client_name, "Connected to Server.")
        
        # Step 1: Generate Client RSA keys
        log_client_event(client_name, "Generating Client RSA key pair...")
        client_key = RSA.generate(2048)
        client_pub_pem = client_key.publickey().export_key(format='PEM').decode('utf-8')
        log_client_event(client_name, "Client RSA keys generated successfully.")
        
        # Step 2: Receive server public key
        server_pub_pem_raw = client_socket.recv(2048)
        server_pub_pem = server_pub_pem_raw.decode('utf-8')
        log_client_event(client_name, "Received Server Public Key.")
        
        # Step 3: Send client public key & name (JSON format)
        payload = {
            "name": client_name,
            "public_key": client_pub_pem
        }
        client_socket.send(json.dumps(payload).encode('utf-8'))
        log_client_event(client_name, "Sent Name and Public Key to Server.")
        
        # Step 4: Receive Encrypted AES key
        encrypted_aes_key = client_socket.recv(2048)
        log_client_event(client_name, f"Received Encrypted AES Key (hex): {encrypted_aes_key.hex()}")
        
        cipher_rsa = PKCS1_OAEP.new(client_key)
        aes_key = cipher_rsa.decrypt(encrypted_aes_key)
        log_client_event(client_name, f"Decrypted AES session key: {aes_key.hex()}")
        
        with active_web_clients_lock:
            active_web_clients[client_id] = {
                "socket": client_socket,
                "aes_key": aes_key,
                "name": client_name
            }
        
        update_active_clients_list()
        
        socketio.emit('client_info_update', {
            "client": client_name,
            "aes_key": aes_key.hex(),
            "rsa_public_key_pem": client_pub_pem,
            "rsa_server_public_key_pem": server_pub_pem
        })
        
        # Msg loop
        while True:
            encrypted_payload = client_socket.recv(2048)
            if not encrypted_payload:
                break
                
            decrypted_message = decrypt_aes(aes_key, encrypted_payload)
            log_client_event(client_name, f"Received encrypted message (hex): {encrypted_payload.hex()}")
            
            sender = "Server"
            msg = decrypted_message
            if ":" in decrypted_message:
                parts = decrypted_message.split(":", 1)
                sender = parts[0]
                msg = parts[1]
                
            socketio.emit('client_message', {
                "client": client_name,
                "sender": sender,
                "message": msg,
                "raw_hex": encrypted_payload.hex(),
                "iv_hex": encrypted_payload[:16].hex()
            })
            
    except Exception as e:
        log_client_event(client_name, f"Error: {str(e)}")
    finally:
        try:
            client_socket.close()
        except:
            pass
        with active_web_clients_lock:
            if client_id in active_web_clients:
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
    global aes_rsa_server_running
    with active_web_clients_lock:
        aes_clients = [info["name"] for cid, info in active_web_clients.items()]
    emit('status_update', {
        "aes_rsa_server": aes_rsa_server_running,
        "aes_rsa_clients": aes_clients
    })

@socketio.on('start_server')
def handle_start_server(data=None):
    global aes_rsa_server_running, aes_rsa_server_thread
    if aes_rsa_server_running:
        log_server_event("Server is already running.")
        return
    aes_rsa_server_running = True
    aes_rsa_server_thread = threading.Thread(target=run_aes_rsa_server, daemon=True)
    aes_rsa_server_thread.start()
    log_server_event("Starting server socket thread...")

@socketio.on('stop_server')
def handle_stop_server(data=None):
    global aes_rsa_server_running, aes_rsa_server_socket
    if not aes_rsa_server_running:
        return
    aes_rsa_server_running = False
    if aes_rsa_server_socket:
        try:
            aes_rsa_server_socket.close()
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
        
    if not aes_rsa_server_running:
        emit('error_msg', {"message": "AES-RSA Server is not running!"})
        return
    threading.Thread(target=run_aes_rsa_client_thread, args=(client_name,), daemon=True).start()

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
        sock = client_info["socket"]
        aes_key = client_info["aes_key"]
        
        payload_str = f"{recipient}:{msg}"
        encrypted_payload = encrypt_aes(aes_key, payload_str)
        
        try:
            sock.send(encrypted_payload)
            log_client_event(sender, f"Plaintext payload sent: '{payload_str}'")
            log_client_event(sender, f"Encrypted TCP packet sent: {encrypted_payload.hex()}")
        except Exception as e:
            log_client_event(sender, f"Error sending package: {str(e)}")
            
if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)
