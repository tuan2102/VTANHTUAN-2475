// Connect to the socket server
const socket = io();

// UI active state
let activeClients = [];

// Auto-sync status on connect
socket.on('connect', () => {
    console.log("WebSocket connected.");
    socket.emit('get_status');
});

// Start Server Event
function startServer() {
    socket.emit('start_server');
}

// Stop Server Event
function stopServer() {
    socket.emit('stop_server');
}

// Clear Server Console
function clearConsole() {
    const consoleEl = document.getElementById("console");
    if (consoleEl) {
        consoleEl.innerHTML = `[${new Date().toLocaleTimeString()}] Console cleared.`;
    }
}

// Modal handling
function showAddClientModal() {
    document.getElementById('input-client-name').value = '';
    document.getElementById('add-client-modal').classList.add('active');
    document.getElementById('input-client-name').focus();
}

function hideAddClientModal() {
    document.getElementById('add-client-modal').classList.remove('active');
}

// Connect Client
function submitAddClient() {
    const name = document.getElementById('input-client-name').value.trim();
    
    if (!name) {
        showToast("Client name cannot be blank!");
        return;
    }
    
    if (!/^[a-zA-Z0-9_\-]{2,12}$/.test(name)) {
        showToast("Name must be 2-12 characters and only contain letters, numbers, or underscores.");
        return;
    }
    
    socket.emit('add_client', { name: name });
    hideAddClientModal();
}

// Disconnect Client
function removeClient(name) {
    socket.emit('remove_client', { name: name });
}

// Create Card HTML
function createClientCardHTML(clientName) {
    const cardId = `card-${clientName}`;
    return `
        <div class="client-card glass-card" id="${cardId}">
            <div class="client-card-header">
                <div class="client-title">
                    <span class="client-dot"></span>
                    <span>${clientName}</span>
                </div>
                <button class="btn-card-close" onclick="removeClient('${clientName}')" title="Disconnect TCP Client">
                    <i class="fa-solid fa-square-xmark"></i>
                </button>
            </div>
            <div class="client-card-body">
                <!-- Cryptographic Handshake Terminal -->
                <div class="client-handshake-wrapper" id="handshake-${clientName}">[00:00:00] Initializing TCP connection...</div>
                
                <!-- Chat Feed -->
                <div class="client-chat-feed" id="feed-${clientName}">
                    <div class="chat-bubble system">TCP Handshake beginning...</div>
                </div>
                
                <!-- Input and Crypto details -->
                <div class="client-input-area">
                    <div class="client-key-drawer" id="key-drawer-${clientName}">
                        <div><span class="key-title">AES Session Key:</span><span class="key-value" id="key-aes-${clientName}">negotiating...</span></div>
                        <div><span class="key-title">DH Shared Secret:</span><span class="key-value" id="key-dh-${clientName}">negotiating...</span></div>
                    </div>
                    <div class="input-row">
                        <select class="recipient-select" id="recipient-${clientName}">
                            <option value="all">Everyone</option>
                        </select>
                        <input type="text" class="client-text-input" id="input-${clientName}" placeholder="Type message..." onkeydown="handleInputKeydown(event, '${clientName}')">
                        <button class="btn btn-primary" onclick="sendMessage('${clientName}')" style="padding: 0.5rem 0.8rem; border-radius: 8px;">
                            <i class="fa-solid fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Send Message
function sendMessage(sender) {
    const inputEl = document.getElementById(`input-${sender}`);
    const recipientEl = document.getElementById(`recipient-${sender}`);
    
    if (!inputEl) return;
    
    const message = inputEl.value.trim();
    const recipient = recipientEl ? recipientEl.value : 'all';
    
    if (!message) return;
    
    appendChatBubble(sender, sender, message, { local: true, recipient: recipient });
    
    socket.emit('send_message', {
        sender: sender,
        recipient: recipient,
        message: message
    });
    
    inputEl.value = '';
    inputEl.focus();
}

function handleInputKeydown(event, sender) {
    if (event.key === 'Enter') {
        sendMessage(sender);
    }
}

// Sync Dropdowns
function updateRecipientDropdowns(clientList) {
    clientList.forEach(clientName => {
        const selectEl = document.getElementById(`recipient-${clientName}`);
        if (selectEl) {
            const currentVal = selectEl.value;
            selectEl.innerHTML = '<option value="all">Everyone (Broadcast)</option>';
            
            clientList.forEach(otherClient => {
                if (otherClient !== clientName) {
                    selectEl.innerHTML += `<option value="${otherClient}">${otherClient}</option>`;
                }
            });
            
            if ([...selectEl.options].some(opt => opt.value === currentVal)) {
                selectEl.value = currentVal;
            } else {
                selectEl.value = 'all';
            }
        }
    });
}

// Append Chat bubble
function appendChatBubble(clientName, sender, message, options = {}) {
    const feedEl = document.getElementById(`feed-${clientName}`);
    if (!feedEl) return;
    
    let bubbleHtml = '';
    if (options.local) {
        const targetStr = options.recipient === 'all' ? 'Everyone' : options.recipient;
        bubbleHtml = `
            <div class="chat-bubble sent">
                <span class="sender-name">To: ${targetStr}</span>
                <div>${escapeHTML(message)}</div>
                <div class="crypto-details">
                    <div>Encrypted & Transmitted via Sockets</div>
                </div>
            </div>
        `;
    } else {
        const payloadHex = options.raw_hex || '---';
        const ivHex = options.iv_hex || '---';
        bubbleHtml = `
            <div class="chat-bubble received">
                <span class="sender-name">${escapeHTML(sender)}</span>
                <div>${escapeHTML(message)}</div>
                <div class="crypto-details">
                    <div><span class="key-title">IV:</span> <span class="crypto-val">${ivHex}</span></div>
                    <div><span class="key-title">Payload (Hex):</span> <span class="crypto-val">${payloadHex.substring(32)}</span></div>
                </div>
            </div>
        `;
    }
    
    feedEl.innerHTML += bubbleHtml;
    feedEl.scrollTop = feedEl.scrollHeight;
}

// Render Toast
function showToast(message) {
    const toast = document.getElementById('toast-notification');
    const toastMsg = document.getElementById('toast-message');
    
    toastMsg.innerText = message;
    toast.className = 'toast-visible';
    
    setTimeout(() => {
        toast.className = 'toast-hidden';
    }, 4000);
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

// ==========================================
// SOCKET.IO EVENT LISTENER TRIGGERS
// ==========================================

socket.on('status_update', (data) => {
    const statusEl = document.getElementById('server-status');
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    
    if (data.dh_aes_server) {
        statusEl.className = 'status-indicator active';
        statusEl.querySelector('.status-label').innerText = 'ONLINE';
        btnStart.disabled = true;
        btnStop.disabled = false;
    } else {
        statusEl.className = 'status-indicator inactive';
        statusEl.querySelector('.status-label').innerText = 'OFFLINE';
        btnStart.disabled = false;
        btnStop.disabled = true;
        
        // Auto-start server if offline
        console.log("Auto-starting server...");
        startServer();
        return;
    }
    
    const clientList = data.dh_aes_clients || [];
    activeClients = clientList;
    
    const workspaceEl = document.getElementById('workspace');
    const badgeListEl = document.getElementById('client-list');
    
    workspaceEl.innerHTML = '';
    badgeListEl.innerHTML = '';
    
    if (clientList.length === 0) {
        badgeListEl.innerHTML = '<p class="empty-list-msg">No clients connected. Set up a client to start chatting.</p>';
        
        // Auto-connect default clients Client1 and Client2
        console.log("Auto-connecting default clients: Client1 and Client2...");
        setTimeout(() => {
            socket.emit('add_client', { name: 'Client1' });
            setTimeout(() => {
                socket.emit('add_client', { name: 'Client2' });
            }, 300);
        }, 500);
    } else {
        clientList.forEach(name => {
            badgeListEl.innerHTML += `
                <div class="client-badge">
                    <i class="fa-solid fa-circle-user text-accent"></i>
                    <span>${name}</span>
                    <button class="client-badge-remove" onclick="removeClient('${name}')">&times;</button>
                </div>
            `;
            workspaceEl.innerHTML += createClientCardHTML(name);
        });
    }
    
    updateRecipientDropdowns(clientList);
});

socket.on('server_log', (data) => {
    const consoleEl = document.getElementById('console');
    if (consoleEl) {
        const currentContent = consoleEl.innerHTML;
        const lines = currentContent.split('\n');
        if (lines.length > 100) {
            consoleEl.innerHTML = lines.slice(lines.length - 80).join('\n') + '\n' + data.message;
        } else {
            consoleEl.innerHTML += '\n' + data.message;
        }
        consoleEl.scrollTop = consoleEl.scrollHeight;
    }
    
    if (data.message.includes("listening on port") || data.message.includes("closed")) {
        socket.emit('get_status');
    }
});

socket.on('client_log', (data) => {
    const handshakeEl = document.getElementById(`handshake-${data.client}`);
    if (handshakeEl) {
        handshakeEl.innerHTML += '\n' + data.message;
        handshakeEl.scrollTop = handshakeEl.scrollHeight;
    }
});

socket.on('client_info_update', (data) => {
    const aesVal = document.getElementById(`key-aes-${data.client}`);
    if (aesVal) aesVal.innerText = data.aes_key;
    
    const dhVal = document.getElementById(`key-dh-${data.client}`);
    if (dhVal) dhVal.innerText = data.dh_shared_secret.substring(0, 32) + '...';
    
    const feedEl = document.getElementById(`feed-${data.client}`);
    if (feedEl) {
        feedEl.innerHTML = '<div class="chat-bubble system">Secured TCP socket channel established.</div>';
    }
});

socket.on('active_clients', (data) => {
    const clientList = data.clients;
    activeClients = clientList;
    
    const badgeListEl = document.getElementById('client-list');
    const workspaceEl = document.getElementById('workspace');
    
    const existingCards = workspaceEl.querySelectorAll('.client-card');
    existingCards.forEach(card => {
        const clientName = card.id.replace('card-', '');
        if (!clientList.includes(clientName)) {
            card.remove();
        }
    });
    
    clientList.forEach(name => {
        const cardId = `card-${name}`;
        if (!document.getElementById(cardId)) {
            workspaceEl.innerHTML += createClientCardHTML(name);
        }
    });
    
    badgeListEl.innerHTML = '';
    if (clientList.length === 0) {
        badgeListEl.innerHTML = '<p class="empty-list-msg">No clients connected. Set up a client to start chatting.</p>';
    } else {
        clientList.forEach(name => {
            badgeListEl.innerHTML += `
                <div class="client-badge">
                    <i class="fa-solid fa-circle-user text-accent"></i>
                    <span>${name}</span>
                    <button class="client-badge-remove" onclick="removeClient('${name}')">&times;</button>
                </div>
            `;
        });
    }
    
    updateRecipientDropdowns(clientList);
});

socket.on('client_message', (data) => {
    appendChatBubble(data.client, data.sender, data.message, {
        raw_hex: data.raw_hex,
        iv_hex: data.iv_hex
    });
});

socket.on('error_msg', (data) => {
    showToast(data.message);
});

window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideAddClientModal();
    }
});
