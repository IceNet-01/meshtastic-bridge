#!/usr/bin/env python3
"""
Enhanced Meshtastic Bridge - Version 2.0
Bridges messages between multiple Meshtastic radios with advanced features
"""

import time
import logging
from datetime import datetime
from threading import Thread, Lock
from pathlib import Path
import sys

import meshtastic
import meshtastic.serial_interface
from pubsub import pub

from device_manager import DeviceManager
from config import BridgeConfig
from message_filter import MessageFilter
from database import DatabaseManager
from metrics import MetricsCollector, MetricsServer
from mqtt_bridge import MQTTBridge
from web_interface import WebInterface, create_web_files
from bridge import MessageTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedMeshtasticBridge:
    """Enhanced bridge with configuration, filtering, database, metrics, MQTT, and web UI"""

    def __init__(self, config_path: str = None):
        """
        Initialize enhanced bridge

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = BridgeConfig(config_path)

        # Validate configuration
        warnings = self.config.validate()
        if warnings:
            logger.warning("Configuration warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")

        # Bridge settings
        bridge_config = self.config.get('bridge', {})
        self.auto_detect = bridge_config.get('auto_detect', True)
        self.ports = bridge_config.get('ports', [])

        # Radio interfaces
        self.interfaces = []
        self.radio_names = []

        # Message tracker
        tracker_config = bridge_config.get('message_tracking', {})
        self.tracker = MessageTracker(
            max_age_minutes=tracker_config.get('max_age_minutes', 10),
            max_messages=tracker_config.get('max_messages', 1000)
        )

        # Message filter
        filter_config = self.config.get('filtering', {})
        self.message_filter = MessageFilter(filter_config) if filter_config.get('enabled') else None

        # Database
        db_config = self.config.get('database', {})
        self.database = None
        if db_config.get('enabled'):
            self.database = DatabaseManager(
                db_path=db_config.get('path', './meshtastic_bridge.db'),
                retention_days=db_config.get('retention_days', 30)
            )
            self.database.log_event('startup', 'Enhanced bridge starting')

        # Metrics
        metrics_config = self.config.get('metrics', {})
        self.metrics = None
        self.metrics_server = None
        if metrics_config.get('enabled'):
            self.metrics = MetricsCollector()
            self.metrics_server = MetricsServer(
                self.metrics,
                host='0.0.0.0',
                port=metrics_config.get('port', 9090)
            )

        # MQTT
        mqtt_config = self.config.get('mqtt', {})
        self.mqtt = None
        if mqtt_config.get('enabled'):
            self.mqtt = MQTTBridge(mqtt_config, self._mqtt_message_callback)

        # Web interface
        web_config = self.config.get('web', {})
        self.web = None
        if web_config.get('enabled'):
            # Create web files if they don't exist
            if not Path('web/templates/index.html').exists():
                create_web_files()

            # For web interface compatibility
            self.port1 = None
            self.port2 = None
            self.interface1 = None
            self.interface2 = None
            self.radio_settings = {}
            self.running = False
            self.stats = {}

            self.web = WebInterface(self, web_config)

        # Background tasks
        self.cleanup_thread = None
        self.stats_thread = None

        self.lock = Lock()

    def connect(self):
        """Connect to all configured radios"""
        # Determine which ports to use
        ports_to_use = []

        if self.auto_detect:
            logger.info("Auto-detecting Meshtastic radios...")
            num_radios = len(self.ports) if self.ports else 2
            devices = DeviceManager.auto_detect_radios(required_count=num_radios)

            if len(devices) < num_radios:
                raise RuntimeError(f"Auto-detection found only {len(devices)} radio(s), need {num_radios}")

            ports_to_use = [dev[0] for dev in devices]
        else:
            if not self.ports:
                raise RuntimeError("auto_detect is False but no ports specified in configuration")
            ports_to_use = self.ports

        # Connect to each radio
        for idx, port in enumerate(ports_to_use):
            radio_name = f"radio{idx + 1}"
            logger.info(f"Connecting to {radio_name} on {port}...")

            try:
                interface = meshtastic.serial_interface.SerialInterface(port)
                time.sleep(2)  # Wait for connection to stabilize

                self.interfaces.append(interface)
                self.radio_names.append(radio_name)

                # Check settings
                settings = DeviceManager.check_radio_settings(interface, port)
                self.radio_settings[radio_name] = settings

                logger.info(f"{radio_name} connected successfully")

                if settings.get('recommendations'):
                    for rec in settings['recommendations']:
                        logger.warning(f"{radio_name}: {rec}")

            except Exception as e:
                logger.error(f"Failed to connect to {radio_name}: {e}")
                self._cleanup_connections()
                raise

        # Set up for backward compatibility with 2-radio mode
        if len(self.interfaces) >= 2:
            self.interface1 = self.interfaces[0]
            self.interface2 = self.interfaces[1]
            self.port1 = ports_to_use[0]
            self.port2 = ports_to_use[1]

        # Initialize stats
        self.stats = {name: {'received': 0, 'sent': 0, 'errors': 0} for name in self.radio_names}

        # Subscribe to message events
        pub.subscribe(self._on_receive, "meshtastic.receive")

        # Start metrics server
        if self.metrics_server:
            self.metrics_server.start()
            self.metrics.set_connected_radios(len(self.interfaces))

        # Connect to MQTT
        if self.mqtt:
            self.mqtt.connect()

        # Start web interface
        if self.web:
            self.web.start()

        # Start background tasks
        self._start_background_tasks()

        self.running = True
        logger.info(f"Enhanced bridge is now running with {len(self.interfaces)} radios")

    def _on_receive(self, packet, interface):
        """Handle messages received on any radio"""
        try:
            # Determine which radio received this
            source_idx = None
            for idx, iface in enumerate(self.interfaces):
                if interface == iface:
                    source_idx = idx
                    break

            if source_idx is None:
                return

            source_radio = self.radio_names[source_idx]
            self._handle_message(packet, source_radio, source_idx)

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def _handle_message(self, packet, source_radio: str, source_idx: int):
        """Process and forward a message"""
        start_time = time.time()

        try:
            # Extract message details
            if 'decoded' not in packet:
                return

            decoded = packet['decoded']

            # Only handle text messages
            if decoded.get('portnum') != 'TEXT_MESSAGE_APP':
                return

            msg_id = packet.get('id', 0)
            from_node = packet.get('fromId', 'unknown')
            to_node = packet.get('toId', 'unknown')

            # Get the text payload
            payload = decoded.get('payload', b'')
            if isinstance(payload, bytes):
                text = payload.decode('utf-8', errors='ignore')
            else:
                text = str(payload)

            # Get channel info
            channel = packet.get('channel', 0)

            # Check if we've already seen this message
            if self.tracker.has_seen(msg_id):
                logger.debug(f"Already seen message {msg_id}, skipping")
                return

            # Apply message filter
            message_dict = {
                'id': msg_id,
                'from': from_node,
                'to': to_node,
                'text': text,
                'channel': channel
            }

            if self.message_filter and not self.message_filter.should_forward(message_dict):
                logger.info(f"Message from {from_node} filtered out")
                if self.metrics:
                    self.metrics.increment_filtered()
                return

            # Add to tracker
            timestamp = datetime.now()
            entry = self.tracker.add_message(msg_id, from_node, to_node, text, channel)

            # Update stats
            with self.lock:
                self.stats[source_radio]['received'] += 1

            if self.metrics:
                self.metrics.increment_received(source_radio)
                self.metrics.increment_node_messages(from_node)

            logger.info(f"[{source_radio}] Received from {from_node}: {text}")

            # Save to database
            if self.database:
                self.database.add_message(msg_id, from_node, to_node, text, channel, timestamp, False, source_radio, None)

            # Publish to MQTT
            if self.mqtt:
                entry['timestamp'] = timestamp
                self.mqtt.publish_message(entry, 'incoming')

            # Broadcast to web clients
            if self.web:
                entry['timestamp'] = timestamp
                self.web.broadcast_message(entry)

            # Forward to other radios
            forwarded = False
            for idx, interface in enumerate(self.interfaces):
                if idx == source_idx:
                    continue  # Don't send back to source

                target_radio = self.radio_names[idx]

                try:
                    interface.sendText(text, channelIndex=channel)
                    self.tracker.mark_forwarded(msg_id)
                    forwarded = True

                    with self.lock:
                        self.stats[target_radio]['sent'] += 1

                    if self.metrics:
                        self.metrics.increment_sent(target_radio)
                        self.metrics.increment_forwarded()

                    if self.database:
                        self.database.mark_forwarded(msg_id)

                    logger.info(f"[{source_radio} -> {target_radio}] Forwarded message")

                except Exception as e:
                    logger.error(f"Failed to forward to {target_radio}: {e}")
                    with self.lock:
                        self.stats[target_radio]['errors'] += 1

                    if self.metrics:
                        self.metrics.increment_errors(target_radio)
                        self.metrics.increment_dropped()

            # Record processing time
            if self.metrics:
                processing_time = (time.time() - start_time) * 1000
                self.metrics.record_processing_time(processing_time)

        except Exception as e:
            logger.error(f"Error in _handle_message: {e}")

    def _mqtt_message_callback(self, text: str, radio: str, channel: int):
        """Handle messages from MQTT for sending"""
        try:
            # Find the radio interface
            if radio in self.radio_names:
                idx = self.radio_names.index(radio)
                self.interfaces[idx].sendText(text, channelIndex=channel)
                logger.info(f"Sent message from MQTT via {radio}: {text}")
            else:
                logger.warning(f"Unknown radio '{radio}' specified in MQTT message")

        except Exception as e:
            logger.error(f"Error sending MQTT message: {e}")

    def send_message(self, text: str, radio: str = 'radio1', channel: int = 0) -> bool:
        """Send a message through specified radio"""
        try:
            if radio not in self.radio_names:
                logger.error(f"Unknown radio: {radio}")
                return False

            idx = self.radio_names.index(radio)
            self.interfaces[idx].sendText(text, channelIndex=channel)
            logger.info(f"Sent message via {radio}: {text}")

            # Publish to MQTT
            if self.mqtt:
                message = {
                    'id': f'sent_{int(time.time())}',
                    'from': 'bridge',
                    'to': 'broadcast',
                    'text': text,
                    'channel': channel,
                    'timestamp': datetime.now(),
                    'forwarded': False
                }
                self.mqtt.publish_message(message, 'outgoing')

            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def get_stats(self) -> dict:
        """Get bridge statistics"""
        with self.lock:
            stats = self.stats.copy()
            stats['tracker'] = self.tracker.get_stats()

            if self.message_filter:
                stats['filter'] = self.message_filter.get_stats()

            if self.mqtt:
                stats['mqtt'] = self.mqtt.get_stats()

            return stats

    def get_recent_messages(self, count: int = 50):
        """Get recent messages"""
        if self.database:
            messages = self.database.get_messages(limit=count)
            return messages
        else:
            return self.tracker.get_recent_messages(count)

    def get_node_info(self, radio: str = 'radio1'):
        """Get node information from a radio"""
        try:
            if radio not in self.radio_names:
                return None

            idx = self.radio_names.index(radio)
            interface = self.interfaces[idx]

            if hasattr(interface, 'myInfo'):
                return interface.myInfo
            return None

        except Exception as e:
            logger.error(f"Failed to get node info: {e}")
            return None

    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        # Database cleanup task
        if self.database:
            self.cleanup_thread = Thread(target=self._cleanup_task, daemon=True)
            self.cleanup_thread.start()

        # Statistics recording task
        if self.database or self.mqtt:
            self.stats_thread = Thread(target=self._stats_task, daemon=True)
            self.stats_thread.start()

    def _cleanup_task(self):
        """Periodic database cleanup"""
        while self.running:
            try:
                time.sleep(3600)  # Run every hour
                if self.database:
                    self.database.cleanup_old_messages()
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    def _stats_task(self):
        """Periodic statistics recording"""
        while self.running:
            try:
                time.sleep(300)  # Run every 5 minutes

                stats = self.get_stats()

                # Record to database
                if self.database:
                    for radio_name, radio_stats in stats.items():
                        if isinstance(radio_stats, dict) and 'received' in radio_stats:
                            self.database.record_statistics(
                                radio_name,
                                radio_stats['received'],
                                radio_stats['sent'],
                                radio_stats['errors']
                            )

                # Publish to MQTT
                if self.mqtt:
                    self.mqtt.publish_statistics(stats)

                # Update metrics
                if self.metrics:
                    self.metrics.set_tracked_messages(stats.get('tracker', {}).get('currently_tracked', 0))

                # Broadcast to web
                if self.web:
                    self.web.broadcast_statistics(stats)

            except Exception as e:
                logger.error(f"Error in stats task: {e}")

    def _cleanup_connections(self):
        """Clean up all radio connections"""
        for interface in self.interfaces:
            try:
                interface.close()
            except Exception as e:
                logger.error(f"Error closing interface: {e}")

    def close(self):
        """Close all connections and cleanup"""
        self.running = False
        logger.info("Closing enhanced bridge...")

        # Log shutdown event
        if self.database:
            self.database.log_event('shutdown', 'Enhanced bridge shutting down')

        # Close radios
        self._cleanup_connections()

        # Stop metrics server
        if self.metrics_server:
            self.metrics_server.stop()

        # Disconnect MQTT
        if self.mqtt:
            self.mqtt.disconnect()

        # Stop web interface
        if self.web:
            self.web.stop()

        # Close database
        if self.database:
            self.database.close()

        logger.info("Enhanced bridge closed")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Enhanced Meshtastic Bridge v2.0')
    parser.add_argument('-c', '--config', help='Path to configuration file')
    parser.add_argument('--create-config', help='Create example configuration file')
    args = parser.parse_args()

    # Create example config if requested
    if args.create_config:
        config = BridgeConfig()
        config.create_example_config(args.create_config)
        print(f"Created example configuration: {args.create_config}")
        return

    try:
        # Create enhanced bridge
        bridge = EnhancedMeshtasticBridge(config_path=args.config)

        # Connect
        bridge.connect()
        print("Enhanced bridge is running. Press Ctrl+C to stop.")

        # Show where services are running
        if bridge.metrics_server:
            print(f"  Metrics: http://localhost:{bridge.config.get('metrics.port', 9090)}/metrics")
        if bridge.web:
            print(f"  Web UI: http://localhost:{bridge.config.get('web.port', 8080)}")

        while bridge.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping bridge...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'bridge' in locals():
            bridge.close()


if __name__ == "__main__":
    main()
