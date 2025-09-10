from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from datetime import datetime
import sqlite3
import uuid
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'NOTENEMOSCLAVEPORQUENOMEDIOLACABEZAPARAIMAGINARMEUNACLAVE'
socketio = SocketIO(app, cors_allowed_origins="*")

#IPS_PERMITIDAS = ['192.168.1.2', '192.168.1.3', '127.0.0.1']
DB_PATH = 'chat_messages.db'

# Inicializar la base de datos
def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                receiver TEXT,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_private BOOLEAN NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                ip TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

# Obtener todos los mensajes públicos
def get_public_messages():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT sender, content, timestamp FROM messages WHERE is_private = 0')
    messages = cursor.fetchall()
    conn.close()
    return messages

# Obtener mensajes privados entre dos usuarios
def get_private_messages(user1, user2):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sender, content, timestamp FROM messages 
        WHERE is_private = 1 AND 
        ((sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?))
    ''', (user1, user2, user2, user1))
    messages = cursor.fetchall()
    conn.close()
    return messages

# Guardar un mensaje en la base de datos
def save_message(sender, content, receiver=None, is_private=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO messages (sender, receiver, content, timestamp, is_private) 
        VALUES (?, ?, ?, ?, ?)
    ''', (sender, receiver, content, timestamp, is_private))
    conn.commit()
    conn.close()

# Obtener todos los usuarios activos
def get_active_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT ip, username FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

@app.route('/')
def index():
    ip_cliente = request.headers.get('X-Forwarded-For', request.remote_addr)
    print(f"[INTENTO DE ACCESO] IP detectada: {ip_cliente}")

    #if ip_cliente not in IPS_PERMITIDAS:
     #   print(f"[RECHAZADO] IP no permitida: {ip_cliente}")
      #  return f"<h1>Acceso denegado para {ip_cliente}</h1>", 403

    print(f"[ACEPTADO] IP permitida: {ip_cliente}")
    # Generar un ID de sesión único si no existe
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    return render_template('chat.html', ip=ip_cliente)

@socketio.on('connect')
def handle_connect():
    ip_cliente = request.remote_addr
    user_id = session.get('user_id', str(uuid.uuid4()))
    
    # Registrar o actualizar usuario
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT OR REPLACE INTO users (ip, username, last_seen) 
        VALUES (?, ?, ?)
    ''', (ip_cliente, f"Usuario ({ip_cliente})", timestamp))
    conn.commit()
    conn.close()
    
    # Enviar historial de mensajes públicos
    public_messages = get_public_messages()
    for msg in public_messages:
        sender, content, timestamp = msg
        emit('message', f"({sender}) dice: {content} - [{timestamp}]")
    
    # Enviar lista de usuarios activos
    active_users = get_active_users()
    emit('users_list', active_users)

@socketio.on('message')
def handle_message(data):
    ip_cliente = request.remote_addr
    
    if isinstance(data, str):  # Mensaje público tradicional para mantener compatibilidad
        message_content = data
        is_private = False
        receiver = None
    else:  # Formato nuevo para mensajes privados
        message_content = data.get('message', '')
        receiver = data.get('receiver', None)
        is_private = receiver is not None
    
    # Guardar mensaje en la base de datos
    save_message(ip_cliente, message_content, receiver, is_private)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"({ip_cliente}) dice: {message_content} - [{timestamp}]"
    
    if is_private:
        # Enviar solo al remitente y destinatario
        emit('private_message', {
            'message': formatted_message,
            'from': ip_cliente,
            'to': receiver
        }, room=receiver)
        emit('private_message', {
            'message': formatted_message,
            'from': ip_cliente,
            'to': receiver
        }, room=request.sid)
    else:
        # Broadcast a todos
        send(formatted_message, broadcast=True)

@socketio.on('join_private')
def on_join_private(data):
    room = data['room']
    join_room(room)
    
    # Cargar mensajes anteriores entre estos usuarios
    current_user = request.remote_addr
    other_user = room.replace(current_user, '').replace('_', '')
    
    private_messages = get_private_messages(current_user, other_user)
    for msg in private_messages:
        sender, content, timestamp = msg
        emit('private_message', {
            'message': f"({sender}) dice: {content} - [{timestamp}]",
            'from': sender,
            'to': current_user if sender != current_user else other_user
        })

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug='true')