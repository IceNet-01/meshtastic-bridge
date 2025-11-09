# Headless Server Quick Start Guide

**Get your Meshtastic Bridge running in 5 minutes!**

## Prerequisites

- Linux system with systemd (Ubuntu, Debian, Raspberry Pi OS, etc.)
- Two Meshtastic radios with USB cables
- Internet connection for installation

## Installation Steps

### 1. Download/Clone the Project

```bash
git clone https://github.com/IceNet-01/meshtastic-bridge.git
cd meshtastic-bridge
```

### 2. Connect Your Radios

Plug both Meshtastic radios into USB ports on your server.

### 3. Run Installation

```bash
./install-headless.sh
```

When prompted "Do you want to start the service now?", press `Y` and Enter.

### 4. Verify It's Running

```bash
sudo systemctl status meshtastic-bridge
```

You should see: **Active: active (running)**

## View Live Activity

Watch messages being bridged in real-time:

```bash
sudo journalctl -u meshtastic-bridge -f
```

Press `Ctrl+C` to exit log viewer.

## That's It!

Your bridge is now:
- ✅ Running and forwarding messages
- ✅ Auto-starting on boot
- ✅ Auto-restarting if it crashes
- ✅ Logging all activity

## Common Commands

```bash
# Check if service is running
sudo systemctl status meshtastic-bridge

# View recent logs
sudo journalctl -u meshtastic-bridge -n 50

# Restart service
sudo systemctl restart meshtastic-bridge

# Stop service
sudo systemctl stop meshtastic-bridge

# Start service
sudo systemctl start meshtastic-bridge
```

## Troubleshooting

### "Permission denied" errors?

Log out and log back in (required for USB access):
```bash
logout
```

### Can't find radios?

Check they're connected:
```bash
./list-devices.sh
```

You should see `/dev/ttyUSB0` and `/dev/ttyUSB1` (or similar).

### Service keeps restarting?

Check logs for errors:
```bash
sudo journalctl -u meshtastic-bridge -n 100
```

## Need More Info?

See [README-HEADLESS.md](README-HEADLESS.md) for complete documentation.

---

**Questions?** Open an issue on GitHub!
