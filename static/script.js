const socket = io();
const body = document.body;
const toggleBtn = document.getElementById('toggle-theme-btn');
let currentChat = 'general';
let usersList = [];

// Función para cambiar entre modo claro y oscuro
function toggleDarkMode() {
    body.classList.toggle('dark-mode');
    const isDarkMode = body.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDarkMode);

    if (isDarkMode) {
        toggleBtn.innerHTML = '<i class="fas fa-sun"></i> Modo Claro';
    } else {
        toggleBtn.innerHTML = '<i class="fas fa-moon"></i> Modo Oscuro';
    }
}

// Cargar el tema guardado al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded. My IP:", myIP);
    
    // Cargar tema guardado
    const savedDarkMode = localStorage.getItem('darkMode') === 'true';
    if (savedDarkMode) {
        body.classList.add('dark-mode');
        toggleBtn.innerHTML = '<i class="fas fa-sun"></i> Modo Claro';
    }
    
    // Configurar manejadores de eventos
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleDarkMode);
    }
    
    const sendButton = document.getElementById('send-button');
    const messageInput = document.getElementById('mensaje');
    
    if (sendButton) {
        sendButton.addEventListener('click', enviar);
    }
    
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                enviar();
            }
        });
    }
});

// Cambiar entre chat general y privado
function selectChat(target) {
    currentChat = target;
    
    // Actualizar UI para mostrar chat activo
    document.querySelectorAll('.user-item').forEach(item => {
        item.classList.remove('active');
    });
    
    const selectedItem = target === 'general' 
        ? document.querySelector('.user-item')
        : document.querySelector(`.user-item[data-ip="${target}"]`);
        
    if (selectedItem) {
        selectedItem.classList.add('active');
    }
    
    // Actualizar estado del chat
    const statusEl = document.getElementById('chat-status');
    if (statusEl) {
        if (target === 'general') {
            statusEl.textContent = "Chat General";
        } else {
            const userName = usersList.find(user => user.ip === target)?.username || target;
            statusEl.textContent = `Chat con ${userName}`;
            
            // Unirse a la sala privada
            socket.emit('join_private', { room: `${myIP}_${target}` });
        }
    }
    
    // Limpiar mensajes
    const mensajesEl = document.getElementById('mensajes');
    if (mensajesEl) {
        mensajesEl.innerHTML = '';
    }
}

// Función unificada para mostrar mensajes en la UI
function displayMessage(messageText, isFromMe = false, isPrivate = false) {
    const mensajesEl = document.getElementById('mensajes');
    if (!mensajesEl) return;
    
    const item = document.createElement('li');
    item.textContent = messageText;
    
    if (isFromMe) {
        item.classList.add('self');
    }
    
    if (isPrivate) {
        item.classList.add('private-message');
    }
    
    item.style.animation = 'fadeIn 0.3s ease';
    mensajesEl.appendChild(item);
    scrollToBottom();
}

// Recibir mensajes generales
socket.on('message', function(msg) {
    console.log("Received message:", msg);
    if (currentChat === 'general') {
        // El servidor ya incluye la IP en el mensaje, así que verificamos si contiene nuestra IP
        const isFromMe = msg.includes(`(${myIP})`);
        displayMessage(msg, isFromMe, false);
    }
});

// Recibir mensajes privados
socket.on('private_message', function(data) {
    console.log("Received private message:", data);
    const { message, from, to } = data;
    const otherUser = from === myIP ? to : from;
    
    // Si estamos en la conversación correcta, mostrar el mensaje
    if (currentChat === otherUser) {
        const isFromMe = from === myIP;
        displayMessage(message, isFromMe, true);
    }
});

// Recibir lista de usuarios - Adaptado al formato del servidor
socket.on('users_list', function(users) {
    console.log("Received users list:", users);
    
    // Convertir el formato del servidor (array de arrays) al formato esperado
    usersList = users.map(user => ({
        ip: user[0],
        username: user[1]
    }));
    
    const usersListEl = document.getElementById('users-list');
    if (usersListEl) {
        usersListEl.innerHTML = '';
        
        // Agregar elemento de chat general
        const generalChatItem = document.createElement('div');
        generalChatItem.classList.add('user-item');
        if (currentChat === 'general') {
            generalChatItem.classList.add('active');
        }
        generalChatItem.innerHTML = '<i class="fas fa-users"></i> Chat General';
        generalChatItem.onclick = () => selectChat('general');
        usersListEl.appendChild(generalChatItem);
        
        // Agregar usuarios (excluyendo el usuario actual)
        usersList.forEach(user => {
            if (user.ip !== myIP) {
                const userItem = document.createElement('div');
                userItem.classList.add('user-item');
                userItem.setAttribute('data-ip', user.ip);
                userItem.innerHTML = `<i class="fas fa-user"></i> ${user.username}`;
                userItem.onclick = () => selectChat(user.ip);
                usersListEl.appendChild(userItem);
            }
        });
    }
});

// Debug connection status
socket.on('connect', function() {
    console.log('Connected to server!');
});

socket.on('connect_error', function(err) {
    console.error('Connection error:', err);
});

socket.on('disconnect', function() {
    console.log('Disconnected from server');
});

function enviar() {
    const input = document.getElementById('mensaje');
    if (!input) return;
    
    const mensaje = input.value.trim();
    
    if (mensaje) {
        console.log("Sending message:", mensaje, "to", currentChat);
        
        if (currentChat === 'general') {
            // Mensaje público
            socket.send(mensaje);
        } else {
            // Mensaje privado
            socket.send({
                message: mensaje,
                receiver: currentChat
            });
        }
        
        // Limpiar input
        input.value = '';
        input.focus();
    }
}

function scrollToBottom() {
    const mensajesContainer = document.querySelector('.messages-container');
    if (mensajesContainer) {
        mensajesContainer.scrollTop = mensajesContainer.scrollHeight;
    }
}