#!/usr/bin/env python3
"""
Web Interface for Meshtastic Bridge
Provides REST API and real-time web dashboard
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from threading import Thread

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

logger = logging.getLogger(__name__)


class WebInterface:
    """Web interface for monitoring and controlling the bridge"""

    def __init__(self, bridge, config: Dict[str, Any]):
        """
        Initialize web interface

        Args:
            bridge: MeshtasticBridge instance
            config: Web configuration dictionary
        """
        self.bridge = bridge
        self.config = config

        # Flask app
        self.app = Flask(__name__,
                        static_folder='web/static',
                        template_folder='web/templates')
        self.app.config['SECRET_KEY'] = config.get('secret_key', 'meshtastic-bridge-secret')

        # Enable CORS
        CORS(self.app)

        # SocketIO for real-time updates
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # Setup routes
        self._setup_routes()
        self._setup_socketio()

        # Server settings
        self.host = config.get('host', '0.0.0.0')
        self.port = config.get('port', 8080)
        self.debug = config.get('debug', False)

        # Server thread
        self.server_thread: Optional[Thread] = None
        self.running = False

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            """Serve main dashboard"""
            return render_template('index.html')

        @self.app.route('/api/status')
        def api_status():
            """Get bridge status"""
            try:
                return jsonify({
                    'status': 'running' if self.bridge.running else 'stopped',
                    'radios': {
                        'radio1': {
                            'connected': self.bridge.interface1 is not None,
                            'port': self.bridge.port1
                        },
                        'radio2': {
                            'connected': self.bridge.interface2 is not None,
                            'port': self.bridge.port2
                        }
                    },
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/statistics')
        def api_statistics():
            """Get bridge statistics"""
            try:
                stats = self.bridge.get_stats()
                return jsonify(stats)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/messages')
        def api_messages():
            """Get recent messages"""
            try:
                count = request.args.get('count', 50, type=int)
                messages = self.bridge.get_recent_messages(count)

                # Convert datetime objects to ISO format
                for msg in messages:
                    if 'timestamp' in msg and hasattr(msg['timestamp'], 'isoformat'):
                        msg['timestamp'] = msg['timestamp'].isoformat()

                return jsonify(messages)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/send', methods=['POST'])
        def api_send():
            """Send a message"""
            try:
                data = request.get_json()

                if not data or 'text' not in data:
                    return jsonify({'error': 'Missing text field'}), 400

                text = data['text']
                radio = data.get('radio', 'radio1')
                channel = data.get('channel', 0)

                success = self.bridge.send_message(text, radio, channel)

                if success:
                    return jsonify({'success': True, 'message': 'Message sent'})
                else:
                    return jsonify({'error': 'Failed to send message'}), 500

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/nodes')
        def api_nodes():
            """Get node information"""
            try:
                nodes = []

                # Get node info from both radios
                for radio_name in ['radio1', 'radio2']:
                    info = self.bridge.get_node_info(radio_name)
                    if info:
                        nodes.append({
                            'radio': radio_name,
                            'info': str(info)
                        })

                return jsonify(nodes)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/settings', methods=['GET', 'POST'])
        def api_settings():
            """Get or update settings"""
            try:
                if request.method == 'GET':
                    return jsonify(self.bridge.radio_settings)
                else:
                    # Update settings (if needed)
                    return jsonify({'message': 'Settings update not implemented'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/health')
        def health():
            """Health check endpoint"""
            return jsonify({'status': 'healthy'})

    def _setup_socketio(self):
        """Setup SocketIO event handlers"""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            logger.info("Web client connected")
            emit('connected', {'status': 'ok'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            logger.info("Web client disconnected")

        @self.socketio.on('request_status')
        def handle_request_status():
            """Handle status request"""
            try:
                status = {
                    'running': self.bridge.running,
                    'radios_connected': 2 if (self.bridge.interface1 and self.bridge.interface2) else 0
                }
                emit('status_update', status)
            except Exception as e:
                logger.error(f"Error handling status request: {e}")

    def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a new message to all connected clients"""
        try:
            # Convert datetime to ISO format
            if 'timestamp' in message and hasattr(message['timestamp'], 'isoformat'):
                message = message.copy()
                message['timestamp'] = message['timestamp'].isoformat()

            self.socketio.emit('new_message', message)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")

    def broadcast_statistics(self, stats: Dict[str, Any]):
        """Broadcast statistics update to all connected clients"""
        try:
            self.socketio.emit('statistics_update', stats)
        except Exception as e:
            logger.error(f"Error broadcasting statistics: {e}")

    def start(self):
        """Start the web server"""
        try:
            self.running = True

            # Start server in background thread
            self.server_thread = Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            logger.info(f"Web interface started on http://{self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start web interface: {e}")
            raise

    def _run_server(self):
        """Run the Flask server"""
        try:
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=self.debug,
                use_reloader=False,
                log_output=not self.debug
            )
        except Exception as e:
            if self.running:
                logger.error(f"Web server error: {e}")

    def stop(self):
        """Stop the web server"""
        self.running = False
        # SocketIO will handle cleanup
        logger.info("Web interface stopped")


def create_web_files():
    """Create HTML and JavaScript files for the web interface"""
    import os

    # Create directories
    os.makedirs('web/templates', exist_ok=True)
    os.makedirs('web/static/css', exist_ok=True)
    os.makedirs('web/static/js', exist_ok=True)

    # Create index.html
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meshtastic Bridge - Dashboard</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔗 Meshtastic Bridge</h1>
            <div class="status-indicator" id="status">
                <span class="status-dot"></span>
                <span>Connecting...</span>
            </div>
        </header>

        <div class="dashboard">
            <!-- Statistics -->
            <section class="card">
                <h2>📊 Statistics</h2>
                <div class="stats-grid" id="statistics">
                    <div class="stat">
                        <div class="stat-value">0</div>
                        <div class="stat-label">Radio 1 Received</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">0</div>
                        <div class="stat-label">Radio 1 Sent</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">0</div>
                        <div class="stat-label">Radio 2 Received</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">0</div>
                        <div class="stat-label">Radio 2 Sent</div>
                    </div>
                </div>
            </section>

            <!-- Messages -->
            <section class="card messages-card">
                <h2>💬 Messages</h2>
                <div class="messages-container" id="messages">
                    <p class="empty-message">No messages yet...</p>
                </div>
            </section>

            <!-- Send Message -->
            <section class="card">
                <h2>📤 Send Message</h2>
                <div class="send-form">
                    <input type="text" id="messageInput" placeholder="Type your message here..." />
                    <select id="radioSelect">
                        <option value="radio1">Radio 1</option>
                        <option value="radio2">Radio 2</option>
                    </select>
                    <button id="sendButton">Send</button>
                </div>
            </section>
        </div>
    </div>

    <script src="/static/js/app.js"></script>
</body>
</html>'''

    # Create CSS
    css_content = '''* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
}

header {
    background: white;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

h1 {
    color: #333;
    font-size: 28px;
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
}

.status-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #fbbf24;
    animation: pulse 2s infinite;
}

.status-indicator.connected .status-dot {
    background: #10b981;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.dashboard {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
}

.card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

h2 {
    color: #333;
    margin-bottom: 15px;
    font-size: 20px;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
}

.stat {
    text-align: center;
    padding: 15px;
    background: #f3f4f6;
    border-radius: 8px;
}

.stat-value {
    font-size: 32px;
    font-weight: bold;
    color: #667eea;
}

.stat-label {
    font-size: 14px;
    color: #6b7280;
    margin-top: 5px;
}

.messages-card {
    grid-column: 1;
}

.messages-container {
    max-height: 400px;
    overflow-y: auto;
    padding: 10px;
    background: #f9fafb;
    border-radius: 8px;
}

.message {
    padding: 10px;
    margin-bottom: 10px;
    background: white;
    border-radius: 6px;
    border-left: 4px solid #667eea;
}

.message-header {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 5px;
}

.message-text {
    color: #333;
}

.message.forwarded {
    border-left-color: #10b981;
}

.empty-message {
    text-align: center;
    color: #9ca3af;
    padding: 20px;
}

.send-form {
    display: flex;
    gap: 10px;
}

#messageInput {
    flex: 1;
    padding: 12px;
    border: 2px solid #e5e7eb;
    border-radius: 6px;
    font-size: 14px;
}

#messageInput:focus {
    outline: none;
    border-color: #667eea;
}

#radioSelect {
    padding: 12px;
    border: 2px solid #e5e7eb;
    border-radius: 6px;
    background: white;
    cursor: pointer;
}

#sendButton {
    padding: 12px 24px;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
    transition: background 0.3s;
}

#sendButton:hover {
    background: #5568d3;
}

@media (min-width: 768px) {
    .dashboard {
        grid-template-columns: 1fr 1fr;
    }

    .messages-card {
        grid-column: 1 / -1;
    }
}'''

    # Create JavaScript
    js_content = '''// Initialize Socket.IO
const socket = io();

// DOM elements
const statusEl = document.getElementById('status');
const messagesEl = document.getElementById('messages');
const statisticsEl = document.getElementById('statistics');
const messageInput = document.getElementById('messageInput');
const radioSelect = document.getElementById('radioSelect');
const sendButton = document.getElementById('sendButton');

// Connection status
socket.on('connect', () => {
    console.log('Connected to server');
    updateStatus('connected');
    loadMessages();
    loadStatistics();
    startAutoRefresh();
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateStatus('disconnected');
});

// Real-time message updates
socket.on('new_message', (message) => {
    addMessage(message);
});

// Statistics updates
socket.on('statistics_update', (stats) => {
    updateStatistics(stats);
});

// Update status indicator
function updateStatus(status) {
    if (status === 'connected') {
        statusEl.className = 'status-indicator connected';
        statusEl.querySelector('span:last-child').textContent = 'Connected';
    } else {
        statusEl.className = 'status-indicator';
        statusEl.querySelector('span:last-child').textContent = 'Disconnected';
    }
}

// Load messages from API
async function loadMessages() {
    try {
        const response = await fetch('/api/messages?count=30');
        const messages = await response.json();

        messagesEl.innerHTML = '';
        if (messages.length === 0) {
            messagesEl.innerHTML = '<p class="empty-message">No messages yet...</p>';
        } else {
            messages.reverse().forEach(msg => addMessage(msg));
        }
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

// Add a message to the display
function addMessage(message) {
    // Remove empty message if present
    const emptyMsg = messagesEl.querySelector('.empty-message');
    if (emptyMsg) {
        emptyMsg.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = message.forwarded ? 'message forwarded' : 'message';

    const timestamp = new Date(message.timestamp).toLocaleTimeString();
    const fromNode = message.from.substring(message.from.length - 8);

    messageDiv.innerHTML = `
        <div class="message-header">
            <span>From: ${fromNode}</span>
            <span>${timestamp}</span>
        </div>
        <div class="message-text">${escapeHtml(message.text)}</div>
    `;

    messagesEl.appendChild(messageDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    // Keep only last 50 messages
    while (messagesEl.children.length > 50) {
        messagesEl.removeChild(messagesEl.firstChild);
    }
}

// Load and update statistics
async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        const stats = await response.json();
        updateStatistics(stats);
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

function updateStatistics(stats) {
    if (!stats.radio1 || !stats.radio2) return;

    statisticsEl.innerHTML = `
        <div class="stat">
            <div class="stat-value">${stats.radio1.received}</div>
            <div class="stat-label">Radio 1 Received</div>
        </div>
        <div class="stat">
            <div class="stat-value">${stats.radio1.sent}</div>
            <div class="stat-label">Radio 1 Sent</div>
        </div>
        <div class="stat">
            <div class="stat-value">${stats.radio2.received}</div>
            <div class="stat-label">Radio 2 Received</div>
        </div>
        <div class="stat">
            <div class="stat-value">${stats.radio2.sent}</div>
            <div class="stat-label">Radio 2 Sent</div>
        </div>
    `;
}

// Send message
sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    const radio = radioSelect.value;

    try {
        const response = await fetch('/api/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text, radio, channel: 0 })
        });

        if (response.ok) {
            messageInput.value = '';
            console.log('Message sent successfully');
        } else {
            const error = await response.json();
            console.error('Error sending message:', error);
            alert('Failed to send message: ' + (error.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Failed to send message');
    }
}

// Auto-refresh statistics
function startAutoRefresh() {
    setInterval(loadStatistics, 5000); // Refresh every 5 seconds
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}'''

    # Write files
    with open('web/templates/index.html', 'w') as f:
        f.write(html_content)

    with open('web/static/css/style.css', 'w') as f:
        f.write(css_content)

    with open('web/static/js/app.js', 'w') as f:
        f.write(js_content)

    logger.info("Web interface files created")


def main():
    """Test web interface"""
    import time

    logging.basicConfig(level=logging.INFO)

    # Create web files
    print("Creating web interface files...")
    create_web_files()

    # Mock bridge for testing
    class MockBridge:
        def __init__(self):
            self.running = True
            self.interface1 = True
            self.interface2 = True
            self.port1 = '/dev/ttyUSB0'
            self.port2 = '/dev/ttyUSB1'
            self.radio_settings = {}

        def get_stats(self):
            return {
                'radio1': {'received': 10, 'sent': 8, 'errors': 0},
                'radio2': {'received': 8, 'sent': 10, 'errors': 0}
            }

        def get_recent_messages(self, count):
            return []

        def send_message(self, text, radio, channel):
            print(f"Mock send: {text} via {radio} on channel {channel}")
            return True

        def get_node_info(self, radio):
            return None

    # Create web interface
    bridge = MockBridge()
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': True
    }

    web = WebInterface(bridge, config)

    print("\nStarting web interface...")
    web.start()

    print(f"\nWeb dashboard available at http://localhost:8080")
    print("Press Ctrl+C to stop...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        web.stop()


if __name__ == "__main__":
    main()
