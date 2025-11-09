# Meshtastic Bridge - Headless Server Fork

> **🚀 Production-Ready Headless Server Edition**
> This fork has been optimized for headless server deployments with auto-start on boot and auto-restart on crash.
>
> **📖 For headless server deployment, see:**
> - **[README-HEADLESS.md](README-HEADLESS.md)** - Complete headless server documentation
> - **[QUICKSTART-HEADLESS.md](QUICKSTART-HEADLESS.md)** - 5-minute quick start guide
> - **Installation**: Run `./install-headless.sh` to get started

---

A powerful bridge/repeater application for Meshtastic radios that forwards messages between different channel configurations (e.g., LongFast and LongModerate).

## Headless Server Features (This Fork)

- ✅ **100% Headless Operation**: No GUI dependencies
- ✅ **Auto-Start on Boot**: Systemd service automatically starts on system boot
- ✅ **Auto-Restart on Crash**: Service automatically recovers from failures
- ✅ **Crash Protection**: Intelligent restart policies prevent restart loops
- ✅ **Production-Ready**: Optimized for Raspberry Pi and server deployments
- ✅ **Resource Efficient**: Minimal memory and CPU usage
- ✅ **Security Hardened**: Runs with minimal privileges

## Features

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

## Requirements

- Python 3.8+
- Two Meshtastic-compatible radios
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

Dependencies (Headless):
- meshtastic
- rich (for enhanced logging)
- pyserial

**Note**: This headless fork does NOT require `textual` (GUI framework). For the original GUI version, see the upstream repository.

## Usage

### Easy Way: Auto-Detection (Recommended)

Just connect both radios and run:

```bash
cd /home/mesh/meshtastic-bridge
./run.sh
```

The script will:
- Auto-detect connected radios
- Ask if you want GUI or headless mode
- Start the bridge automatically

Or run directly with auto-detection:

**With GUI:**
```bash
source venv/bin/activate
python gui.py
```

**Without GUI (headless):**
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

You can modify the message tracking settings in `bridge.py`:

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

## Files

- `bridge.py`: Core bridge logic and message handling
- `gui.py`: Textual-based terminal GUI
- `device_manager.py`: Auto-detection and settings verification
- `run.sh`: Interactive launcher script
- `install.sh`: Installation and setup script
- `list-devices.sh`: USB device detection utility
- `meshtastic-bridge.service`: systemd service file
- `requirements.txt`: Python dependencies
- `README.md`: Full documentation (this file)
- `QUICKSTART.md`: Quick start guide

## Future Enhancements

Completed:
- [x] Auto-detection of radios
- [x] Settings verification
- [x] Auto-start at boot (systemd)
- [x] Auto-restart on failure

Potential features to add:
- [ ] Configuration file for channel mapping
- [ ] Message filtering by content or sender
- [ ] Metrics export (Prometheus, etc.)
- [ ] Web interface
- [ ] Multiple radio support (>2)
- [ ] Message encryption/decryption
- [ ] SQLite database for message persistence
- [ ] MQTT bridge support

## License

MIT License - Feel free to use and modify as needed.

## Contributing

This is a personal project, but feel free to fork and enhance it!
