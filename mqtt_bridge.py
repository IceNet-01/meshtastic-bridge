#!/usr/bin/env python3
"""
MQTT Bridge for Meshtastic Bridge
Publishes messages to MQTT and subscribes to topics for sending
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Callable
from threading import Thread

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

logger = logging.getLogger(__name__)


class MQTTBridge:
    """MQTT integration for Meshtastic Bridge"""

    def __init__(self, config: Dict[str, Any], message_callback: Optional[Callable] = None):
        """
        Initialize MQTT bridge

        Args:
            config: MQTT configuration dictionary
            message_callback: Callback function for messages from MQTT (text, radio, channel)
        """
        if not MQTT_AVAILABLE:
            raise ImportError("paho-mqtt not installed. Install with: pip install paho-mqtt")

        self.config = config
        self.message_callback = message_callback

        # MQTT settings
        self.broker = config.get('broker', 'localhost')
        self.port = config.get('port', 1883)
        self.username = config.get('username')
        self.password = config.get('password')
        self.topic_prefix = config.get('topic_prefix', 'meshtastic/bridge')
        self.publish_incoming = config.get('publish_incoming', True)
        self.publish_outgoing = config.get('publish_outgoing', True)
        self.qos = config.get('qos', 1)
        self.retain = config.get('retain', False)

        # Client ID
        self.client_id = config.get('client_id', 'meshtastic-bridge')

        # Create MQTT client
        self.client = mqtt.Client(client_id=self.client_id)

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # Set authentication if provided
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        # Connection state
        self.connected = False
        self.running = False

        # Statistics
        self.stats = {
            'published': 0,
            'received': 0,
            'errors': 0
        }

    def connect(self):
        """Connect to MQTT broker"""
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, keepalive=60)

            # Start network loop in background
            self.client.loop_start()
            self.running = True

            # Wait for connection
            timeout = 10
            start = time.time()
            while not self.connected and (time.time() - start) < timeout:
                time.sleep(0.1)

            if not self.connected:
                raise TimeoutError("Connection timeout")

            logger.info("Connected to MQTT broker")

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    def _on_connect(self, client, userdata, flags, rc):
        """Called when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connection successful")

            # Subscribe to command topics
            command_topic = f"{self.topic_prefix}/command/#"
            self.client.subscribe(command_topic, qos=self.qos)
            logger.info(f"Subscribed to {command_topic}")

            # Publish online status
            status_topic = f"{self.topic_prefix}/status"
            self.client.publish(status_topic, "online", qos=1, retain=True)

        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Called when disconnected from MQTT broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (code {rc})")
        else:
            logger.info("MQTT disconnected")

    def _on_message(self, client, userdata, message):
        """Called when a message is received from MQTT"""
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')

            logger.debug(f"MQTT message received on {topic}: {payload}")
            self.stats['received'] += 1

            # Handle command messages
            if topic.startswith(f"{self.topic_prefix}/command/"):
                self._handle_command(topic, payload)

        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
            self.stats['errors'] += 1

    def _handle_command(self, topic: str, payload: str):
        """Handle command messages from MQTT"""
        try:
            # Extract command from topic
            parts = topic.split('/')
            if len(parts) < 3:
                return

            command = parts[2]  # command type (e.g., 'send')

            if command == 'send' and self.message_callback:
                # Parse send command
                try:
                    data = json.loads(payload)
                    text = data.get('text', payload)
                    radio = data.get('radio', 'radio1')
                    channel = data.get('channel', 0)

                    # Call the message callback
                    self.message_callback(text, radio, channel)
                    logger.info(f"Sent message from MQTT: {text}")

                except json.JSONDecodeError:
                    # If not JSON, treat as plain text
                    self.message_callback(payload, 'radio1', 0)
                    logger.info(f"Sent message from MQTT: {payload}")

        except Exception as e:
            logger.error(f"Error handling MQTT command: {e}")
            self.stats['errors'] += 1

    def publish_message(self, message: Dict[str, Any], direction: str = 'incoming'):
        """
        Publish a Meshtastic message to MQTT

        Args:
            message: Message dictionary
            direction: 'incoming' or 'outgoing'
        """
        if not self.connected:
            logger.warning("Not connected to MQTT broker")
            return

        try:
            # Check if we should publish this direction
            if direction == 'incoming' and not self.publish_incoming:
                return
            if direction == 'outgoing' and not self.publish_outgoing:
                return

            # Build topic
            from_node = message.get('from', 'unknown')
            channel = message.get('channel', 0)

            # Publish to multiple topics for flexibility

            # 1. Full message data (JSON)
            data_topic = f"{self.topic_prefix}/messages/{direction}/{from_node}"
            payload = json.dumps({
                'id': message.get('id'),
                'from': from_node,
                'to': message.get('to'),
                'text': message.get('text'),
                'channel': channel,
                'timestamp': message.get('timestamp').isoformat() if message.get('timestamp') else None,
                'forwarded': message.get('forwarded', False)
            })
            self.client.publish(data_topic, payload, qos=self.qos, retain=self.retain)

            # 2. Text content only
            text_topic = f"{self.topic_prefix}/text/{direction}/{from_node}"
            text = message.get('text', '')
            self.client.publish(text_topic, text, qos=self.qos, retain=False)

            # 3. Channel-based topic
            channel_topic = f"{self.topic_prefix}/channel/{channel}/{direction}"
            self.client.publish(channel_topic, payload, qos=self.qos, retain=False)

            # 4. Home Assistant discovery (if configured)
            if self.config.get('homeassistant_discovery', False):
                self._publish_homeassistant_discovery(from_node)

            self.stats['published'] += 1
            logger.debug(f"Published message to MQTT: {data_topic}")

        except Exception as e:
            logger.error(f"Failed to publish to MQTT: {e}")
            self.stats['errors'] += 1

    def _publish_homeassistant_discovery(self, node_id: str):
        """Publish Home Assistant MQTT discovery message"""
        try:
            # Create sensor for this node
            discovery_topic = f"homeassistant/sensor/meshtastic_{node_id}/config"

            config = {
                "name": f"Meshtastic {node_id}",
                "state_topic": f"{self.topic_prefix}/text/incoming/{node_id}",
                "icon": "mdi:radio-tower",
                "unique_id": f"meshtastic_bridge_{node_id}",
                "device": {
                    "identifiers": [f"meshtastic_bridge_{node_id}"],
                    "name": f"Meshtastic Node {node_id}",
                    "manufacturer": "Meshtastic",
                    "model": "Radio Node"
                }
            }

            self.client.publish(discovery_topic, json.dumps(config), qos=1, retain=True)

        except Exception as e:
            logger.error(f"Failed to publish Home Assistant discovery: {e}")

    def publish_status(self, status: Dict[str, Any]):
        """Publish bridge status to MQTT"""
        if not self.connected:
            return

        try:
            status_topic = f"{self.topic_prefix}/bridge/status"
            payload = json.dumps(status)
            self.client.publish(status_topic, payload, qos=1, retain=True)

        except Exception as e:
            logger.error(f"Failed to publish status: {e}")

    def publish_statistics(self, stats: Dict[str, Any]):
        """Publish statistics to MQTT"""
        if not self.connected:
            return

        try:
            stats_topic = f"{self.topic_prefix}/bridge/statistics"
            payload = json.dumps(stats)
            self.client.publish(stats_topic, payload, qos=1, retain=False)

        except Exception as e:
            logger.error(f"Failed to publish statistics: {e}")

    def get_stats(self) -> Dict[str, int]:
        """Get MQTT bridge statistics"""
        return self.stats.copy()

    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            # Publish offline status
            if self.connected:
                status_topic = f"{self.topic_prefix}/status"
                self.client.publish(status_topic, "offline", qos=1, retain=True)

            self.running = False
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")

        except Exception as e:
            logger.error(f"Error disconnecting from MQTT: {e}")


def main():
    """Test MQTT bridge"""
    logging.basicConfig(level=logging.DEBUG)

    # Test configuration
    config = {
        'broker': 'localhost',
        'port': 1883,
        'username': None,
        'password': None,
        'topic_prefix': 'meshtastic/bridge',
        'publish_incoming': True,
        'publish_outgoing': True
    }

    def message_callback(text: str, radio: str, channel: int):
        """Handle messages from MQTT"""
        print(f"Message from MQTT: {text} (radio: {radio}, channel: {channel})")

    print("Starting MQTT bridge test...")

    try:
        # Create bridge
        bridge = MQTTBridge(config, message_callback)

        # Connect
        print("Connecting to MQTT broker...")
        bridge.connect()

        # Publish a test message
        print("\nPublishing test message...")
        from datetime import datetime
        test_message = {
            'id': 'test123',
            'from': '!abc123456',
            'to': 'broadcast',
            'text': 'Test message from MQTT bridge',
            'channel': 0,
            'timestamp': datetime.now(),
            'forwarded': False
        }
        bridge.publish_message(test_message, 'incoming')

        # Publish status
        print("Publishing status...")
        bridge.publish_status({'connected': True, 'radios': 2})

        # Keep running for a bit
        print("\nBridge running. Publish to 'meshtastic/bridge/command/send' to send a message.")
        print("Press Ctrl+C to stop...")

        time.sleep(30)

    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'bridge' in locals():
            bridge.disconnect()


if __name__ == "__main__":
    main()
