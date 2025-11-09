#!/usr/bin/env python3
"""
Prometheus Metrics Exporter for Meshtastic Bridge
Provides metrics endpoint for monitoring
"""

import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and exposes Prometheus metrics"""

    def __init__(self):
        """Initialize metrics collector"""
        self.lock = Lock()

        # Counter metrics
        self.messages_received_total = {'radio1': 0, 'radio2': 0}
        self.messages_sent_total = {'radio1': 0, 'radio2': 0}
        self.messages_errors_total = {'radio1': 0, 'radio2': 0}
        self.messages_forwarded_total = 0
        self.messages_dropped_total = 0
        self.messages_filtered_total = 0

        # Gauge metrics
        self.connected_radios = 0
        self.active_nodes = 0
        self.tracked_messages = 0

        # Histogram/timing metrics
        self.message_processing_times = []
        self.max_processing_time = 0
        self.min_processing_time = float('inf')

        # Uptime
        self.start_time = time.time()

        # Node statistics
        self.node_message_counts: Dict[str, int] = {}

    def increment_received(self, radio: str, count: int = 1):
        """Increment received message counter"""
        with self.lock:
            if radio in self.messages_received_total:
                self.messages_received_total[radio] += count

    def increment_sent(self, radio: str, count: int = 1):
        """Increment sent message counter"""
        with self.lock:
            if radio in self.messages_sent_total:
                self.messages_sent_total[radio] += count

    def increment_errors(self, radio: str, count: int = 1):
        """Increment error counter"""
        with self.lock:
            if radio in self.messages_errors_total:
                self.messages_errors_total[radio] += count

    def increment_forwarded(self, count: int = 1):
        """Increment forwarded message counter"""
        with self.lock:
            self.messages_forwarded_total += count

    def increment_dropped(self, count: int = 1):
        """Increment dropped message counter"""
        with self.lock:
            self.messages_dropped_total += count

    def increment_filtered(self, count: int = 1):
        """Increment filtered message counter"""
        with self.lock:
            self.messages_filtered_total += count

    def set_connected_radios(self, count: int):
        """Set number of connected radios"""
        with self.lock:
            self.connected_radios = count

    def set_active_nodes(self, count: int):
        """Set number of active nodes"""
        with self.lock:
            self.active_nodes = count

    def set_tracked_messages(self, count: int):
        """Set number of tracked messages"""
        with self.lock:
            self.tracked_messages = count

    def record_processing_time(self, duration_ms: float):
        """Record message processing time"""
        with self.lock:
            self.message_processing_times.append(duration_ms)

            # Keep only last 1000 measurements
            if len(self.message_processing_times) > 1000:
                self.message_processing_times.pop(0)

            self.max_processing_time = max(self.max_processing_time, duration_ms)
            if duration_ms > 0:
                self.min_processing_time = min(self.min_processing_time, duration_ms)

    def increment_node_messages(self, node_id: str, count: int = 1):
        """Increment message count for a specific node"""
        with self.lock:
            if node_id not in self.node_message_counts:
                self.node_message_counts[node_id] = 0
            self.node_message_counts[node_id] += count

    def get_uptime_seconds(self) -> float:
        """Get uptime in seconds"""
        return time.time() - self.start_time

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format

        Returns:
            Metrics in Prometheus text format
        """
        with self.lock:
            lines = []

            # Add header
            lines.append('# HELP meshtastic_bridge_info Bridge information')
            lines.append('# TYPE meshtastic_bridge_info gauge')
            lines.append('meshtastic_bridge_info{version="2.0"} 1')
            lines.append('')

            # Uptime
            lines.append('# HELP meshtastic_bridge_uptime_seconds Bridge uptime in seconds')
            lines.append('# TYPE meshtastic_bridge_uptime_seconds gauge')
            lines.append(f'meshtastic_bridge_uptime_seconds {self.get_uptime_seconds():.2f}')
            lines.append('')

            # Messages received
            lines.append('# HELP meshtastic_messages_received_total Total messages received per radio')
            lines.append('# TYPE meshtastic_messages_received_total counter')
            for radio, count in self.messages_received_total.items():
                lines.append(f'meshtastic_messages_received_total{{radio="{radio}"}} {count}')
            lines.append('')

            # Messages sent
            lines.append('# HELP meshtastic_messages_sent_total Total messages sent per radio')
            lines.append('# TYPE meshtastic_messages_sent_total counter')
            for radio, count in self.messages_sent_total.items():
                lines.append(f'meshtastic_messages_sent_total{{radio="{radio}"}} {count}')
            lines.append('')

            # Errors
            lines.append('# HELP meshtastic_messages_errors_total Total message errors per radio')
            lines.append('# TYPE meshtastic_messages_errors_total counter')
            for radio, count in self.messages_errors_total.items():
                lines.append(f'meshtastic_messages_errors_total{{radio="{radio}"}} {count}')
            lines.append('')

            # Forwarded
            lines.append('# HELP meshtastic_messages_forwarded_total Total messages forwarded')
            lines.append('# TYPE meshtastic_messages_forwarded_total counter')
            lines.append(f'meshtastic_messages_forwarded_total {self.messages_forwarded_total}')
            lines.append('')

            # Dropped
            lines.append('# HELP meshtastic_messages_dropped_total Total messages dropped')
            lines.append('# TYPE meshtastic_messages_dropped_total counter')
            lines.append(f'meshtastic_messages_dropped_total {self.messages_dropped_total}')
            lines.append('')

            # Filtered
            lines.append('# HELP meshtastic_messages_filtered_total Total messages filtered')
            lines.append('# TYPE meshtastic_messages_filtered_total counter')
            lines.append(f'meshtastic_messages_filtered_total {self.messages_filtered_total}')
            lines.append('')

            # Connected radios
            lines.append('# HELP meshtastic_connected_radios Number of connected radios')
            lines.append('# TYPE meshtastic_connected_radios gauge')
            lines.append(f'meshtastic_connected_radios {self.connected_radios}')
            lines.append('')

            # Active nodes
            lines.append('# HELP meshtastic_active_nodes Number of active nodes')
            lines.append('# TYPE meshtastic_active_nodes gauge')
            lines.append(f'meshtastic_active_nodes {self.active_nodes}')
            lines.append('')

            # Tracked messages
            lines.append('# HELP meshtastic_tracked_messages Number of currently tracked messages')
            lines.append('# TYPE meshtastic_tracked_messages gauge')
            lines.append(f'meshtastic_tracked_messages {self.tracked_messages}')
            lines.append('')

            # Processing time statistics
            if self.message_processing_times:
                avg_time = sum(self.message_processing_times) / len(self.message_processing_times)

                lines.append('# HELP meshtastic_message_processing_time_ms Message processing time statistics')
                lines.append('# TYPE meshtastic_message_processing_time_ms gauge')
                lines.append(f'meshtastic_message_processing_time_ms{{stat="avg"}} {avg_time:.2f}')
                lines.append(f'meshtastic_message_processing_time_ms{{stat="max"}} {self.max_processing_time:.2f}')
                lines.append(f'meshtastic_message_processing_time_ms{{stat="min"}} {self.min_processing_time:.2f}')
                lines.append('')

            # Per-node message counts
            if self.node_message_counts:
                lines.append('# HELP meshtastic_node_messages_total Total messages per node')
                lines.append('# TYPE meshtastic_node_messages_total counter')
                for node_id, count in self.node_message_counts.items():
                    # Escape node ID for prometheus label
                    safe_node_id = node_id.replace('"', '\\"')
                    lines.append(f'meshtastic_node_messages_total{{node_id="{safe_node_id}"}} {count}')
                lines.append('')

            return '\n'.join(lines)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoint"""

    metrics_collector: Optional[MetricsCollector] = None

    def do_GET(self):
        """Handle GET request"""
        if self.path == '/metrics' and self.metrics_collector:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()

            metrics = self.metrics_collector.export_prometheus()
            self.wfile.write(metrics.encode('utf-8'))

        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Override to suppress request logging"""
        pass  # Suppress default logging


class MetricsServer:
    """HTTP server for exposing metrics"""

    def __init__(self, collector: MetricsCollector, host: str = '0.0.0.0', port: int = 9090):
        """
        Initialize metrics server

        Args:
            collector: MetricsCollector instance
            host: Host to bind to
            port: Port to listen on
        """
        self.collector = collector
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[Thread] = None
        self.running = False

    def start(self):
        """Start the metrics server"""
        try:
            # Set the collector for the handler
            MetricsHandler.metrics_collector = self.collector

            # Create HTTP server
            self.server = HTTPServer((self.host, self.port), MetricsHandler)
            self.running = True

            # Start server in background thread
            self.thread = Thread(target=self._run_server, daemon=True)
            self.thread.start()

            logger.info(f"Metrics server started on http://{self.host}:{self.port}/metrics")

        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise

    def _run_server(self):
        """Run the HTTP server"""
        while self.running:
            try:
                self.server.handle_request()
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    logger.error(f"Error handling metrics request: {e}")

    def stop(self):
        """Stop the metrics server"""
        self.running = False

        if self.server:
            try:
                self.server.shutdown()
                logger.info("Metrics server stopped")
            except Exception as e:
                logger.error(f"Error stopping metrics server: {e}")


def main():
    """Test metrics server"""
    logging.basicConfig(level=logging.INFO)

    print("Starting metrics server test...")

    # Create collector
    collector = MetricsCollector()

    # Add some test data
    collector.increment_received('radio1', 100)
    collector.increment_received('radio2', 75)
    collector.increment_sent('radio1', 75)
    collector.increment_sent('radio2', 100)
    collector.increment_errors('radio1', 5)
    collector.increment_forwarded(150)
    collector.set_connected_radios(2)
    collector.set_active_nodes(10)
    collector.set_tracked_messages(25)
    collector.record_processing_time(12.5)
    collector.record_processing_time(15.3)
    collector.record_processing_time(8.7)
    collector.increment_node_messages('!abc123456', 45)
    collector.increment_node_messages('!def789012', 30)

    # Start server
    server = MetricsServer(collector, port=9090)
    server.start()

    print("\nMetrics server running at http://localhost:9090/metrics")
    print("Health check at http://localhost:9090/health")
    print("\nSample metrics:")
    print(collector.export_prometheus())
    print("\nPress Ctrl+C to stop...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.stop()


if __name__ == "__main__":
    main()
