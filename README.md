# Meshtastic Bridge

A powerful bridge/repeater application for Meshtastic radios that forwards messages between different channel configurations (e.g., LongFast and LongModerate).

## 🎉 Version 2.0 Released!

The enhanced bridge now includes professional-grade features for monitoring, filtering, and integration:

✅ **Configuration Files** - YAML/JSON support for easy customization
✅ **Message Filtering** - Filter by sender, content (keywords/regex), or channel
✅ **SQLite Database** - Persistent message storage and search
✅ **Prometheus Metrics** - Monitor performance with Grafana
✅ **MQTT Integration** - Publish to MQTT, Home Assistant support
✅ **Web Dashboard** - Real-time web interface with API
✅ **Multiple Radios** - Support for >2 radios simultaneously

See [FEATURES.md](FEATURES.md) for detailed documentation | [ROADMAP.md](ROADMAP.md) for future plans

## Features

### Core Features (v1.0)
- **Auto-Detection**: Automatically finds and connects to your Meshtastic radios
- **Settings Verification**: Checks radio configuration and provides recommendations
- **Auto-Start at Boot**: Optional systemd service for hands-free operation
- **Dual Radio Bridge**: Connects two Meshtastic radios and forwards messages between them
- **Message Deduplication**: Intelligent tracking prevents message loops and spam
- **Message Logging**: All messages are tracked with timestamps and forwarding status
- **Terminal GUI**: Beautiful Textual-based interface showing:
  - Real-time statistics (messages received/sent/errors)
  - Node connection status
  - Live message log with forwarding status
  - Message sending capability
- **Bidirectional Communication**: Messages flow both ways between radios
- **Channel Support**: Works with different channel configurations

### Enhanced Features (v2.0)
- **Configuration Management**: YAML/JSON config files for all settings
- **Message Filtering**:
  - Whitelist/blacklist by node ID
  - Content filtering with keywords and regex patterns
  - Channel-based filtering
  - Custom filter rules with priorities
- **Database Persistence**:
  - SQLite storage for message history
  - Full-text message search
  - Node registry and statistics
  - Automatic cleanup of old messages
- **Metrics & Monitoring**:
  - Prometheus metrics endpoint
  - Message throughput, error rates, processing times
  - Ready for Grafana dashboards
- **MQTT Bridge**:
  - Publish messages to MQTT broker
  - Subscribe to commands for sending
  - Home Assistant auto-discovery
  - Flexible topic mapping
- **Web Interface**:
  - Real-time dashboard with live updates
  - REST API for integration
  - Send messages via web UI
  - Statistics visualization
- **Multiple Radio Support**: Connect and bridge >2 radios simultaneously

## Requirements

- Python 3.8+
- Two or more Meshtastic-compatible radios
- USB serial connections

## Installation

### Quick Install

Run the installation script to set everything up automatically:

```bash
cd /home/mesh/meshtastic-bridge
./install.sh
```

This will:
1. Add your user to the `dialout` group for serial port access
2. Install system dependencies (python3-venv, python3-pip)
3. Set up the Python virtual environment
4. Install all required packages
5. Make scripts executable
6. Optionally install the systemd service for auto-start at boot
7. Optionally create a desktop shortcut

### Manual Installation

If you prefer to install manually:

```bash
cd /home/mesh/meshtastic-bridge

# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and log back in for this to take effect

# Install system dependencies
sudo apt install python3-venv python3-pip

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Make scripts executable
chmod +x *.py *.sh
```

Dependencies:
- Core: meshtastic, pyserial, pubsub
- UI: textual, rich
- Configuration: pyyaml
- MQTT: paho-mqtt
- Web: flask, flask-cors, flask-socketio
- Utilities: python-dateutil

See [requirements.txt](requirements.txt) for complete list.

## Usage

### Version 2.0 Enhanced Bridge (Recommended)

The enhanced bridge includes all v2.0 features (web UI, MQTT, metrics, filtering, database):

```bash
# First, create a configuration file
python bridge_enhanced.py --create-config meshtastic-bridge.yaml

# Edit the configuration to enable desired features
nano meshtastic-bridge.yaml

# Run the enhanced bridge
source venv/bin/activate
python bridge_enhanced.py -c meshtastic-bridge.yaml
```

**Access the services:**
- 🌐 **Web Dashboard**: http://localhost:8080
- 📊 **Prometheus Metrics**: http://localhost:9090/metrics
- 🔌 **REST API**: http://localhost:8080/api/status

**Example configuration:**
```yaml
bridge:
  auto_detect: true

database:
  enabled: true
  path: ./meshtastic_bridge.db

metrics:
  enabled: true
  port: 9090

web:
  enabled: true
  port: 8080

mqtt:
  enabled: false  # Enable if you have an MQTT broker

filtering:
  enabled: false  # Enable to filter messages
```

See [config.example.yaml](config.example.yaml) for all options.

### Version 1.0 Basic Bridge

For simple bridging without advanced features:

**Easy Way: Auto-Detection**

```bash
cd /home/mesh/meshtastic-bridge
./run.sh
```

The script will:
- Auto-detect connected radios
- Ask if you want GUI or headless mode
- Start the bridge automatically

**Run directly with auto-detection:**

With GUI:
```bash
source venv/bin/activate
python gui.py
```

Without GUI (headless):
```bash
source venv/bin/activate
python bridge.py
```

### Manual Port Selection

If you want to specify exact ports:

**With GUI:**
```bash
source venv/bin/activate
python gui.py /dev/ttyUSB0 /dev/ttyUSB1
```

**Without GUI:**
```bash
source venv/bin/activate
python bridge.py /dev/ttyUSB0 /dev/ttyUSB1
```

### Finding Your Radio Ports (if needed)

```bash
# List all USB serial devices
ls -l /dev/ttyUSB* /dev/ttyACM*

# Or use the built-in detector
./list-devices.sh

# Or use dmesg to see recently connected devices
dmesg | grep tty
```

Common port names:
- `/dev/ttyUSB0`, `/dev/ttyUSB1` (most common on Linux)
- `/dev/ttyACM0`, `/dev/ttyACM1` (some devices)

### GUI Controls

- **Arrow Keys / Tab**: Navigate between elements
- **Enter**: Send message (when in input field)
- **Send (Radio 1)**: Send message via first radio
- **Send (Radio 2)**: Send message via second radio
- **q or Ctrl+C**: Quit application
- **r**: Refresh display

### Running Headless (No GUI)

```bash
source venv/bin/activate
python bridge.py /dev/ttyUSB0 /dev/ttyUSB1
```

## Auto-Start at Boot (systemd Service)

The bridge can be configured to start automatically at boot using systemd.

### Installation

Run the installation script and answer "yes" when asked about the systemd service:

```bash
./install.sh
```

Or install manually:

```bash
sudo cp meshtastic-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable meshtastic-bridge
sudo systemctl start meshtastic-bridge
```

### Service Management

```bash
# Start the service
sudo systemctl start meshtastic-bridge

# Stop the service
sudo systemctl stop meshtastic-bridge

# Restart the service
sudo systemctl restart meshtastic-bridge

# Check service status
sudo systemctl status meshtastic-bridge

# View live logs
sudo journalctl -u meshtastic-bridge -f

# Disable auto-start at boot
sudo systemctl disable meshtastic-bridge

# Enable auto-start at boot
sudo systemctl enable meshtastic-bridge
```

### Notes

- The service runs in headless mode (no GUI)
- Auto-detection is enabled by default
- Logs are available via `journalctl`
- The service will automatically restart if it crashes
- Radios should be connected before the system boots for best results

## How It Works

1. **Connection**: The bridge connects to both radios via USB serial
2. **Message Reception**: When a message arrives on either radio, it's received and logged
3. **Deduplication**: The message ID is checked against recent messages to prevent loops
4. **Forwarding**: If it's a new message, it's forwarded to the other radio
5. **Tracking**: All messages are logged with timestamps and forwarding status

### Message Tracking

- Messages are tracked for 10 minutes by default
- Up to 1000 messages are kept in memory
- Each message includes:
  - Message ID (for deduplication)
  - Source node
  - Destination node
  - Message text
  - Channel
  - Timestamp
  - Forwarding status

## Configuration

### Version 2.0 Configuration Files

Create and customize a configuration file:

```bash
# Create example configuration
python bridge_enhanced.py --create-config meshtastic-bridge.yaml

# Edit the configuration
nano meshtastic-bridge.yaml
```

See [config.example.yaml](config.example.yaml) for all available options and [FEATURES.md](FEATURES.md) for detailed configuration documentation.

### Version 1.0 Code-Based Configuration

For the basic bridge, modify settings in `bridge.py`:

```python
# In MessageTracker.__init__()
max_age_minutes=10  # How long to track messages
max_messages=1000   # Maximum messages in memory
```

## Troubleshooting

### Permission Denied on Serial Ports

If you get "Permission denied" errors:

```bash
# Add your user to the dialout group
sudo usermod -a -G dialout $USER

# Then log out and log back in
```

### Radio Not Found

- Check that both radios are connected via USB
- Verify the port names with `ls -l /dev/ttyUSB*`
- Try unplugging and replugging the radios
- Check `dmesg` output for USB device detection

### Connection Hangs

- Make sure the radios are powered on
- Verify they're not in bootloader mode
- Try different USB ports
- Check USB cable quality

### Messages Not Forwarding

- Check that both radios are on the same mesh network
- Verify channel settings match on both radios
- Check the message log for errors
- Ensure radios have good signal to the mesh

## Architecture

### Version 1.0 Architecture
```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Radio 1   │◄────────┤   Bridge    │────────►│   Radio 2   │
│  (LongFast) │         │  + Tracker  │         │(LongModerate)│
└─────────────┘         └─────────────┘         └─────────────┘
                               │
                               │
                        ┌──────▼──────┐
                        │  Terminal   │
                        │     GUI     │
                        └─────────────┘
```

### Version 2.0 Enhanced Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Radio 1   │◄───►│             │◄───►│   Radio 2   │
└─────────────┘     │   Enhanced  │     └─────────────┘
                    │    Bridge   │
┌─────────────┐     │             │     ┌─────────────┐
│   Radio N   │◄───►│   + Core    │◄───►│   Radio N+1 │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
    │   Message   │ │  Database  │ │   Config   │
    │   Filter    │ │   SQLite   │ │   Manager  │
    └─────────────┘ └────────────┘ └────────────┘
           │               │               │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
    │    MQTT     │ │    Web     │ │ Prometheus │
    │   Bridge    │ │ Dashboard  │ │  Metrics   │
    └─────────────┘ └────────────┘ └────────────┘
           │               │               │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
    │    Home     │ │  Browser   │ │  Grafana   │
    │  Assistant  │ │   Users    │ │ Monitoring │
    └─────────────┘ └────────────┘ └────────────┘
```

## Files

**Core Application:**
- `bridge.py`: Original bridge logic (v1.0)
- `bridge_enhanced.py`: Enhanced bridge with v2.0 features
- `gui.py`: Textual-based terminal GUI
- `device_manager.py`: Auto-detection and settings verification

**v2.0 Feature Modules:**
- `config.py`: Configuration file management (YAML/JSON)
- `message_filter.py`: Message filtering system
- `database.py`: SQLite database manager
- `metrics.py`: Prometheus metrics exporter
- `mqtt_bridge.py`: MQTT integration
- `web_interface.py`: Web dashboard and API

**Configuration & Scripts:**
- `config.example.yaml`: Example configuration file
- `run.sh`: Interactive launcher script
- `install.sh`: Installation and setup script
- `list-devices.sh`: USB device detection utility
- `meshtastic-bridge.service`: systemd service file

**Documentation:**
- `README.md`: Full documentation (this file)
- `FEATURES.md`: Detailed feature documentation
- `ROADMAP.md`: Development roadmap
- `QUICKSTART.md`: Quick start guide

**Dependencies:**
- `requirements.txt`: Python dependencies

---

## Documentation

- **[FEATURES.md](FEATURES.md)** - Comprehensive feature documentation with usage examples
- **[ROADMAP.md](ROADMAP.md)** - Development roadmap and future plans
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide
- **[config.example.yaml](config.example.yaml)** - Example configuration file

## License

MIT License - Feel free to use and modify as needed.

## Contributing

This is a personal project, but feel free to fork and enhance it!
