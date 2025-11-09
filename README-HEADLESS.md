# Meshtastic Bridge - Headless Server Edition

**Production-ready headless server for bridging Meshtastic radio networks**

This is a headless (no GUI) server version of the Meshtastic Bridge that automatically starts on boot and restarts if it crashes. Perfect for dedicated server deployments, Raspberry Pi installations, or any scenario where you need a reliable, always-on bridge.

## Features

- **100% Headless Operation**: No GUI dependencies, runs as a background service
- **Auto-Start on Boot**: Automatically starts when the system boots
- **Auto-Restart on Crash**: Service automatically restarts if it fails
- **Crash Protection**: Prevents restart loops with intelligent backoff
- **Auto-Detection**: Automatically finds and connects to Meshtastic radios
- **Message Deduplication**: Prevents message loops and duplicate forwarding
- **Bidirectional Bridge**: Forwards messages between two radios seamlessly
- **Robust Logging**: All activity logged to systemd journal
- **Resource Management**: Optimized for low-resource systems
- **Security Hardening**: Runs with minimal privileges

## System Requirements

- **OS**: Linux with systemd (Ubuntu, Debian, Raspberry Pi OS, etc.)
- **Python**: 3.8 or higher
- **Hardware**: Two Meshtastic-compatible radios with USB connections
- **Permissions**: User account with sudo access

## Quick Start Installation

### Super Quick (One Command)

**Connect your radios, then run:**

```bash
git clone https://github.com/IceNet-01/meshtastic-bridge.git && cd meshtastic-bridge && ./install-auto.sh
```

Done! The script automatically:
- ✅ Installs all dependencies
- ✅ Configures permissions and service
- ✅ Enables auto-start and auto-restart
- ✅ Starts your bridge immediately

**Takes 2-3 minutes. No prompts needed.**

---

### Standard Installation (With Options)

If you already have the repository or want interactive installation:

```bash
git clone https://github.com/IceNet-01/meshtastic-bridge.git
cd meshtastic-bridge
./install-headless.sh          # Interactive mode
# or
./install-headless.sh --auto   # Fully automated
```

This script will:
- Configure user permissions (dialout group for USB access)
- Install system dependencies (python3-venv, python3-pip)
- Create Python virtual environment
- Install required Python packages (headless-only)
- Install and enable systemd service
- Configure auto-start on boot
- Configure auto-restart on crash
- Start the service automatically

Your bridge is now running and will survive reboots and crashes.

**📖 For detailed installation options and troubleshooting, see [INSTALL.md](INSTALL.md)**

## Service Management

### Check Service Status

```bash
sudo systemctl status meshtastic-bridge
```

### View Live Logs

```bash
# Follow logs in real-time
sudo journalctl -u meshtastic-bridge -f

# View last 100 lines
sudo journalctl -u meshtastic-bridge -n 100

# View logs from today
sudo journalctl -u meshtastic-bridge --since today
```

### Start/Stop/Restart Service

```bash
# Start the service
sudo systemctl start meshtastic-bridge

# Stop the service
sudo systemctl stop meshtastic-bridge

# Restart the service
sudo systemctl restart meshtastic-bridge
```

### Enable/Disable Auto-Start

```bash
# Enable auto-start on boot (default after installation)
sudo systemctl enable meshtastic-bridge

# Disable auto-start on boot
sudo systemctl disable meshtastic-bridge
```

## How It Works

### Auto-Detection

The bridge automatically detects connected Meshtastic radios via USB. It:
1. Scans all USB serial ports
2. Tests each device to verify it's a Meshtastic radio
3. Connects to the first two radios found
4. Begins forwarding messages between them

### Message Forwarding

- Messages received on Radio 1 are forwarded to Radio 2
- Messages received on Radio 2 are forwarded to Radio 1
- Each message is tracked to prevent loops and duplicates
- Message history is kept for 10 minutes (configurable)

### Auto-Restart Behavior

The service is configured with intelligent restart policies:

- **Always restart**: Service restarts automatically after any failure
- **10-second delay**: Waits 10 seconds before restarting
- **Crash protection**: Allows up to 5 restarts within 60 seconds
- **Recovery**: If restart limit is reached, system attempts recovery

### Resource Management

- **Minimal privileges**: Runs as regular user (not root)
- **Private /tmp**: Uses isolated temporary directory
- **USB access only**: Only has access to serial devices (dialout group)
- **Graceful shutdown**: 30-second timeout for clean stop

## Manual Operation

If you want to run the bridge manually without the systemd service:

```bash
cd /path/to/meshtastic-bridge
source venv/bin/activate
python3 bridge.py
```

### Manual Port Specification

If auto-detection isn't working, you can specify ports manually:

```bash
source venv/bin/activate
python3 bridge.py /dev/ttyUSB0 /dev/ttyUSB1
```

## Configuration

### Radio Requirements

Both radios should be configured with:
- Different channel configurations (e.g., LongFast and LongModerate)
- USB serial connection enabled
- Properly paired with your mesh network

### Finding USB Ports

To see connected USB devices:

```bash
./list-devices.sh
```

Or manually:

```bash
ls -la /dev/ttyUSB* /dev/ttyACM*
```

### Verify Radio Settings

The bridge will automatically check radio settings on startup and log any recommendations.

## Troubleshooting

### Service won't start

Check the logs for errors:
```bash
sudo journalctl -u meshtastic-bridge -n 50
```

Common issues:
- **Permission denied**: Make sure your user is in the `dialout` group
  ```bash
  sudo usermod -a -G dialout $USER
  # Then log out and log back in
  ```
- **No radios found**: Verify radios are connected via USB
  ```bash
  ./list-devices.sh
  ```
- **Port access denied**: Check that radios aren't being used by another program

### Service keeps restarting

If the service is restarting frequently:
1. Check logs to identify the error
2. Verify both radios are connected and working
3. Test manually to isolate the issue:
   ```bash
   cd /path/to/meshtastic-bridge
   source venv/bin/activate
   python3 bridge.py
   ```

### Can't connect to radios

- Verify radios are powered on and connected via USB
- Check USB cables (try different cables)
- Run `dmesg | tail` to see recent USB connection events
- Check permissions: `ls -la /dev/ttyUSB*`

### Logs not showing messages

The bridge logs at INFO level by default. To see more detailed logs, you can modify the logging level in `bridge.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## System Integration

### Running on Raspberry Pi

This headless server is perfect for Raspberry Pi deployments:

1. Install Raspberry Pi OS Lite (headless)
2. Connect via SSH
3. Clone repository and run `./install-headless.sh`
4. Connect radios via USB
5. Done! Bridge runs automatically on boot

### Running in Docker (Future)

Docker support is planned for future releases. For now, use the systemd service for containerized deployments.

### Running on Multiple Servers

Each server can run one bridge instance. To run multiple instances on the same server, you'll need to:
1. Create separate installation directories
2. Create separate systemd service files with unique names
3. Ensure each instance uses different radios

## Performance

The headless bridge is lightweight and efficient:
- **Memory**: ~50-100 MB RAM
- **CPU**: Minimal (<1% on modern systems)
- **Network**: Uses only the Meshtastic radio network
- **Storage**: Minimal (logs rotate automatically via systemd)

## Security

Security features enabled by default:
- Runs as non-root user
- Minimal file system access
- Private /tmp directory
- No network listening (only USB serial)
- No privilege escalation
- Isolated process tree

## Dependencies

### System Dependencies
- Python 3.8+
- python3-venv
- python3-pip
- systemd

### Python Dependencies (Installed Automatically)
- meshtastic >= 2.7.0
- pyserial >= 3.5
- rich >= 14.2.0

**Note**: This headless version does NOT include GUI dependencies (textual) for minimal resource usage.

## Updating

To update to the latest version:

```bash
cd /path/to/meshtastic-bridge
git pull
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart meshtastic-bridge
```

## Uninstallation

To completely remove the bridge:

```bash
# Stop and disable service
sudo systemctl stop meshtastic-bridge
sudo systemctl disable meshtastic-bridge
sudo rm /etc/systemd/system/meshtastic-bridge.service
sudo systemctl daemon-reload

# Remove installation directory
cd ~
rm -rf /path/to/meshtastic-bridge
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Headless Meshtastic Bridge              │
│                                                 │
│  ┌───────────────┐       ┌──────────────────┐  │
│  │  Radio 1      │◄─────►│  Radio 2         │  │
│  │  (LongFast)   │       │  (LongModerate)  │  │
│  └───────────────┘       └──────────────────┘  │
│         │                         │             │
│         │                         │             │
│  ┌──────▼─────────────────────────▼──────────┐ │
│  │      Message Tracker & Forwarder          │ │
│  │  - Deduplication                          │ │
│  │  - Bidirectional forwarding               │ │
│  │  - Loop prevention                        │ │
│  └───────────────────────────────────────────┘ │
│                      │                          │
│                      ▼                          │
│          ┌───────────────────────┐              │
│          │  Logging & Monitoring │              │
│          │  (systemd journal)    │              │
│          └───────────────────────┘              │
└─────────────────────────────────────────────────┘
```

## Project Structure

```
meshtastic-bridge/
├── bridge.py                    # Core headless bridge logic
├── device_manager.py            # USB device detection
├── install-headless.sh          # Headless installation script
├── meshtastic-bridge.service    # Systemd service definition
├── list-devices.sh              # USB device listing utility
├── requirements.txt             # Python dependencies (headless-only)
├── README-HEADLESS.md          # This file
└── venv/                        # Python virtual environment (created during install)
```

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/IceNet-01/meshtastic-bridge/issues
- Documentation: See README.md for more details

## License

[Include your license information here]

## Credits

Built for the Meshtastic community to enable reliable, always-on radio bridges.

---

**Ready to deploy?** Run `./install-headless.sh` and you're live in minutes!
