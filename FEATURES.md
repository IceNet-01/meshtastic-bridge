## Meshtastic Bridge - Feature Documentation

This document provides detailed information about all features available in Meshtastic Bridge v2.0.

## Table of Contents

1. [Configuration Management](#configuration-management)
2. [Message Filtering](#message-filtering)
3. [Database Persistence](#database-persistence)
4. [Metrics Export](#metrics-export)
5. [MQTT Integration](#mqtt-integration)
6. [Web Interface](#web-interface)
7. [Advanced Usage](#advanced-usage)

---

## Configuration Management

### Overview

The bridge supports flexible configuration through YAML or JSON files, making it easy to customize behavior without changing code.

### Configuration File Locations

The bridge looks for configuration files in the following locations (in order):

1. `./meshtastic-bridge.yaml`
2. `./meshtastic-bridge.yml`
3. `./meshtastic-bridge.json`
4. `~/.meshtastic-bridge.yaml`
5. `~/.config/meshtastic-bridge.yaml`
6. `/etc/meshtastic-bridge/config.yaml`

### Creating a Configuration File

```bash
# Create an example configuration
python config.py

# Or use the enhanced bridge
python bridge_enhanced.py --create-config meshtastic-bridge.yaml
```

### Configuration Sections

**Bridge Settings:**
- `auto_detect`: Automatically find connected radios
- `ports`: Manual port specification
- `message_tracking`: Deduplication settings

**Filtering:**
- `enabled`: Enable/disable filtering
- `whitelist_nodes`: Only forward these nodes
- `blacklist_nodes`: Never forward these nodes
- `content_filters`: Keyword and regex filters

**Database:**
- `enabled`: Enable message persistence
- `path`: Database file location
- `retention_days`: Message retention period

**Metrics:**
- `enabled`: Enable Prometheus metrics
- `port`: Metrics endpoint port

**MQTT:**
- `enabled`: Enable MQTT bridge
- `broker`: MQTT broker address
- `topic_prefix`: Topic prefix for messages

**Web:**
- `enabled`: Enable web dashboard
- `port`: Web server port

---

## Message Filtering

### Overview

Message filtering allows you to control which messages are forwarded based on sender, content, or channel.

### Filter Types

**1. Node-Based Filtering**

```yaml
filtering:
  enabled: true
  whitelist_nodes:
    - "!abc123456"  # Only forward from these nodes
  blacklist_nodes:
    - "!bad123456"  # Never forward from these nodes
```

**2. Content-Based Filtering**

```yaml
filtering:
  content_filters:
    keywords:
      - spam
      - advertisement
    regex_patterns:
      - '\b\d{3}-\d{3}-\d{4}\b'  # Block phone numbers
```

**3. Channel-Based Filtering**

```yaml
filtering:
  allowed_channels: [0, 1]  # Only these channels
  blocked_channels: [5]      # Never these channels
```

**4. Custom Rules**

```yaml
filtering:
  custom_rules:
    - name: "Emergency Priority"
      type: keyword
      pattern: "EMERGENCY"
      action: allow
      priority: 100
```

### Filter Statistics

View filter statistics:
- Via web interface at `/api/statistics`
- In application logs
- Through Prometheus metrics

---

## Database Persistence

### Overview

SQLite database stores all messages, nodes, and statistics for historical analysis and search.

### Features

- **Message Storage**: All messages with metadata
- **Node Tracking**: First/last seen, message counts
- **Statistics**: Historical performance data
- **Event Logging**: System events and errors
- **Search**: Full-text message search
- **Retention**: Automatic cleanup of old messages

### Database Schema

**messages**: Message history
**nodes**: Node registry
**statistics**: Performance metrics
**settings**: Configuration storage
**events**: System event log

### Querying the Database

```bash
# Access database directly
sqlite3 meshtastic_bridge.db

# Example queries
SELECT * FROM messages ORDER BY timestamp DESC LIMIT 10;
SELECT node_id, message_count FROM nodes ORDER BY message_count DESC;
SELECT * FROM events WHERE event_type = 'error';
```

### API Access

```bash
# Get messages via API
curl http://localhost:8080/api/messages?count=50

# Search messages
curl http://localhost:8080/api/messages?search=hello
```

---

## Metrics Export

### Overview

Prometheus-compatible metrics endpoint for monitoring and alerting.

### Available Metrics

**Counters:**
- `meshtastic_messages_received_total{radio="radioN"}`
- `meshtastic_messages_sent_total{radio="radioN"}`
- `meshtastic_messages_errors_total{radio="radioN"}`
- `meshtastic_messages_forwarded_total`
- `meshtastic_messages_dropped_total`
- `meshtastic_messages_filtered_total`
- `meshtastic_node_messages_total{node_id="!abc123456"}`

**Gauges:**
- `meshtastic_bridge_uptime_seconds`
- `meshtastic_connected_radios`
- `meshtastic_active_nodes`
- `meshtastic_tracked_messages`
- `meshtastic_message_processing_time_ms{stat="avg|max|min"}`

### Accessing Metrics

```bash
# View metrics
curl http://localhost:9090/metrics

# Health check
curl http://localhost:9090/health
```

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'meshtastic-bridge'
    static_configs:
      - targets: ['localhost:9090']
```

### Grafana Dashboard

Import the provided Grafana dashboard template:
1. Open Grafana
2. Import Dashboard
3. Upload `grafana-dashboard.json` (coming soon)

---

## MQTT Integration

### Overview

Publish messages to MQTT broker and receive commands via MQTT topics.

### Topic Structure

**Published Topics:**
- `meshtastic/bridge/messages/incoming/{node_id}` - Full message JSON
- `meshtastic/bridge/text/incoming/{node_id}` - Text only
- `meshtastic/bridge/channel/{channel}/incoming` - Channel-based
- `meshtastic/bridge/bridge/status` - Bridge status
- `meshtastic/bridge/bridge/statistics` - Statistics

**Subscribed Topics:**
- `meshtastic/bridge/command/send` - Send messages

### Configuration

```yaml
mqtt:
  enabled: true
  broker: localhost
  port: 1883
  username: myuser
  password: mypass
  topic_prefix: meshtastic/bridge
```

### Sending Messages via MQTT

```bash
# Simple text message
mosquitto_pub -t meshtastic/bridge/command/send -m "Hello World"

# JSON with options
mosquitto_pub -t meshtastic/bridge/command/send -m '{
  "text": "Hello",
  "radio": "radio1",
  "channel": 0
}'
```

### Home Assistant Integration

Enable Home Assistant auto-discovery:

```yaml
mqtt:
  homeassistant_discovery: true
```

This creates sensors for each node automatically.

---

## Web Interface

### Overview

Real-time web dashboard for monitoring and controlling the bridge.

### Features

- **Real-time Updates**: WebSocket-based live data
- **Message Log**: View incoming and forwarded messages
- **Statistics Dashboard**: Visual statistics display
- **Send Messages**: Send messages through any radio
- **Node Information**: Connected node details
- **Responsive Design**: Works on mobile and desktop

### Accessing the Dashboard

```
http://localhost:8080
```

### API Endpoints

**GET /api/status**: Bridge status
**GET /api/statistics**: Current statistics
**GET /api/messages**: Recent messages
**GET /api/nodes**: Node information
**POST /api/send**: Send a message

### API Examples

```bash
# Get status
curl http://localhost:8080/api/status

# Get recent messages
curl http://localhost:8080/api/messages?count=20

# Send a message
curl -X POST http://localhost:8080/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from API",
    "radio": "radio1",
    "channel": 0
  }'
```

### WebSocket Events

**Client -> Server:**
- `connect`: Initial connection
- `request_status`: Request status update

**Server -> Client:**
- `connected`: Connection confirmed
- `new_message`: New message received
- `statistics_update`: Statistics updated
- `status_update`: Status changed

---

## Advanced Usage

### Multiple Radios (>2)

Configure multiple radios:

```yaml
bridge:
  auto_detect: false
  ports:
    - /dev/ttyUSB0
    - /dev/ttyUSB1
    - /dev/ttyUSB2
```

Messages received on any radio are forwarded to all others.

### Custom Message Processing

Create custom rules for complex filtering:

```yaml
filtering:
  custom_rules:
    - name: "Allow Emergency"
      type: regex
      pattern: "^(EMERGENCY|URGENT|HELP)"
      action: allow
      priority: 100
    - name: "Block Spam Keywords"
      type: keyword
      pattern: "spam"
      action: block
      priority: 50
```

### Integration Examples

**1. Node-RED Integration**

Use MQTT nodes to integrate with Node-RED flows.

**2. Discord/Telegram Bots**

Monitor MQTT topics and forward to messaging platforms.

**3. Custom Scripts**

Use the REST API to build custom monitoring or automation.

**4. Alerting**

Use Prometheus metrics with Alertmanager for notifications.

### Performance Tuning

**Message Tracking:**
```yaml
bridge:
  message_tracking:
    max_age_minutes: 5   # Reduce for less memory
    max_messages: 500    # Reduce for less memory
```

**Database:**
```yaml
database:
  retention_days: 7      # Keep less history
```

**Logging:**
```yaml
logging:
  level: WARNING         # Reduce logging verbosity
```

### Troubleshooting

**Enable Debug Logging:**
```yaml
logging:
  level: DEBUG
```

**Check Metrics:**
```bash
curl http://localhost:9090/metrics | grep error
```

**View Database:**
```bash
sqlite3 meshtastic_bridge.db "SELECT * FROM events WHERE event_type='error';"
```

**MQTT Debugging:**
```bash
# Subscribe to all bridge topics
mosquitto_sub -t "meshtastic/bridge/#" -v
```

---

## Best Practices

1. **Always enable database** for message history
2. **Use filtering** to reduce unnecessary traffic
3. **Monitor metrics** to track performance
4. **Regular backups** of database file
5. **Secure web interface** if exposed to internet
6. **Use MQTT authentication** for production
7. **Configure log rotation** for long-running deployments

---

## Support and Contributing

- **Issues**: Report bugs on GitHub
- **Feature Requests**: Submit via GitHub issues
- **Documentation**: Help improve docs via pull requests
- **Testing**: Test on different hardware configurations

---

For more information, see:
- [README.md](README.md) - Getting started
- [ROADMAP.md](ROADMAP.md) - Future development
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide
