# Quick Start Guide

## First-Time Setup

### 1. Install

Run the installation script (only needed once):

```bash
cd /home/mesh/meshtastic-bridge
./install.sh
```

This will:
- Set up permissions for USB access
- Install all dependencies
- Optionally install auto-start service
- Create desktop shortcut (optional)

**Important:** Log out and log back in after installation for USB permissions to take effect!

## Daily Use

### 1. Connect Your Radios

Plug both Meshtastic radios into your computer via USB.

### 2. Run the Bridge

#### Easiest Way: Auto-Detection (Recommended)

```bash
cd /home/mesh/meshtastic-bridge
./run.sh
```

Just press Enter to accept defaults and the bridge will:
- Automatically find your radios
- Start the GUI
- Begin bridging messages

#### Quick Launch (No Prompts)

**With GUI:**
```bash
cd /home/mesh/meshtastic-bridge
source venv/bin/activate
python gui.py
```

**Without GUI (headless):**
```bash
cd /home/mesh/meshtastic-bridge
source venv/bin/activate
python bridge.py
```

#### Manual Port Selection

If auto-detection doesn't work or you want to specify ports:

**With GUI:**
```bash
cd /home/mesh/meshtastic-bridge
source venv/bin/activate
python gui.py /dev/ttyUSB0 /dev/ttyUSB1
```

**Without GUI:**
```bash
cd /home/mesh/meshtastic-bridge
source venv/bin/activate
python bridge.py /dev/ttyUSB0 /dev/ttyUSB1
```

### 3. Optional: Find Your Devices

```bash
cd /home/mesh/meshtastic-bridge
./list-devices.sh
```

This shows all available USB serial ports.

## 4. Using the GUI

Once the GUI is running:

- **View Statistics**: Top panel shows message counts
- **View Status**: Middle panel shows radio connection status
- **View Messages**: Large panel shows all messages being forwarded
- **Send Messages**: Type in the input box at the bottom and press Enter or click a Send button

**Keyboard Shortcuts:**
- `q` or `Ctrl+C` - Quit
- `r` - Refresh
- `Tab` - Switch between input fields
- `Enter` - Send message (when in input field)

## 5. Stop the Bridge

Press `q` in the GUI or `Ctrl+C` in the terminal.

## Troubleshooting

### "Permission denied" on /dev/ttyUSB*

```bash
sudo usermod -a -G dialout $USER
```

Then log out and log back in.

### "No USB serial devices found"

- Check that radios are plugged in
- Try different USB ports
- Check if devices show up: `ls -l /dev/ttyUSB*`

### Connection hangs or fails

- Unplug and replug the radios
- Make sure they're powered on
- Try different USB cables
- Check if they appear in `dmesg` output

## Auto-Start at Boot (Optional)

If you want the bridge to start automatically when your computer boots:

### Install the Service

During installation, answer "yes" when asked about systemd service. Or install manually:

```bash
sudo cp meshtastic-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable meshtastic-bridge
sudo systemctl start meshtastic-bridge
```

### Check Service Status

```bash
sudo systemctl status meshtastic-bridge
```

### View Live Logs

```bash
sudo journalctl -u meshtastic-bridge -f
```

### Stop/Start Service

```bash
sudo systemctl stop meshtastic-bridge
sudo systemctl start meshtastic-bridge
```

**Note:** The auto-start service runs in headless mode (no GUI) and uses auto-detection.

## What's Happening?

When the bridge is running:

1. Both radios are automatically detected and connected
2. Radio settings are verified and logged
3. Any message received on Radio 1 is forwarded to Radio 2
4. Any message received on Radio 2 is forwarded to Radio 1
5. Message IDs are tracked to prevent infinite loops
6. All activity is logged and displayed in the GUI (or system logs if headless)

Messages are bridged **bidirectionally** between the two channel configurations (e.g., LongFast ↔ LongModerate).

## Need Help?

Check the full README.md for more detailed information and configuration options.
