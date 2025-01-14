from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

@socketio.on('connect')
def on_connect():
    print('Client connected')

@socketio.on('message')
def on_message(data):
    print('Message received:', data)
    socketio.send('Echo: ' + data)

@socketio.on('disconnect')
def on_disconnect():
    print('Client disconnected')

if __name__ == "__main__":
    socketio.run(
        app,
        certfile=str("certs/localhost+2.pem"),
        keyfile=str("certs/localhost+2-key.pem"),
        host="0.0.0.0",
        port=8000,
        allow_unsafe_werkzeug=True,
    )