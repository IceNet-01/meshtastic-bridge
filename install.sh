#!/bin/bash
# Installation script for Meshtastic Bridge

set -e  # Exit on error

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Meshtastic Bridge Installation${NC}"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root!${NC}"
    echo "Run as your regular user. The script will use sudo when needed."
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Installation directory: $SCRIPT_DIR"
echo ""

# Step 1: Add user to dialout group for serial port access
echo -e "${YELLOW}[1/6] Configuring user permissions...${NC}"
if groups $USER | grep -q '\bdialout\b'; then
    echo "User $USER is already in dialout group"
else
    echo "Adding user $USER to dialout group..."
    sudo usermod -a -G dialout $USER
    echo -e "${YELLOW}NOTE: You will need to log out and log back in for group changes to take effect!${NC}"
fi
echo ""

# Step 2: Install system dependencies
echo -e "${YELLOW}[2/6] Checking system dependencies...${NC}"
if ! dpkg -l | grep -q python3-venv; then
    echo "Installing python3-venv..."
    sudo apt update
    sudo apt install -y python3-venv python3-pip
else
    echo "System dependencies already installed"
fi
echo ""

# Step 3: Set up virtual environment
echo -e "${YELLOW}[3/6] Setting up Python virtual environment...${NC}"
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    cd "$SCRIPT_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "Virtual environment already exists"
    cd "$SCRIPT_DIR"
    source venv/bin/activate
    echo "Upgrading packages..."
    pip install --upgrade -r requirements.txt
fi
echo ""

# Step 4: Make scripts executable
echo -e "${YELLOW}[4/6] Setting script permissions...${NC}"
chmod +x "$SCRIPT_DIR/bridge.py"
chmod +x "$SCRIPT_DIR/gui.py"
chmod +x "$SCRIPT_DIR/run.sh"
chmod +x "$SCRIPT_DIR/list-devices.sh"
chmod +x "$SCRIPT_DIR/device_manager.py"
echo "Scripts are now executable"
echo ""

# Step 5: Install systemd service
echo -e "${YELLOW}[5/6] Installing systemd service...${NC}"
read -p "Do you want to install the systemd service for auto-start at boot? [y/N]: " INSTALL_SERVICE
INSTALL_SERVICE=${INSTALL_SERVICE:-N}

if [[ "$INSTALL_SERVICE" =~ ^[Yy]$ ]]; then
    echo "Installing systemd service..."
    sudo cp "$SCRIPT_DIR/meshtastic-bridge.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable meshtastic-bridge.service
    echo -e "${GREEN}Service installed and enabled!${NC}"
    echo ""
    echo "Service management commands:"
    echo "  Start service:   sudo systemctl start meshtastic-bridge"
    echo "  Stop service:    sudo systemctl stop meshtastic-bridge"
    echo "  Check status:    sudo systemctl status meshtastic-bridge"
    echo "  View logs:       sudo journalctl -u meshtastic-bridge -f"
    echo ""
    read -p "Do you want to start the service now? [y/N]: " START_NOW
    START_NOW=${START_NOW:-N}
    if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
        sudo systemctl start meshtastic-bridge
        echo "Service started!"
        sleep 2
        sudo systemctl status meshtastic-bridge --no-pager
    fi
else
    echo "Skipping systemd service installation"
fi
echo ""

# Step 6: Create desktop shortcut (optional)
echo -e "${YELLOW}[6/6] Desktop integration...${NC}"
read -p "Do you want to create a desktop shortcut for the GUI? [y/N]: " CREATE_DESKTOP
CREATE_DESKTOP=${CREATE_DESKTOP:-N}

if [[ "$CREATE_DESKTOP" =~ ^[Yy]$ ]]; then
    DESKTOP_FILE="$HOME/Desktop/meshtastic-bridge.desktop"
    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Meshtastic Bridge
Comment=Bridge between Meshtastic radios
Exec=x-terminal-emulator -e "$SCRIPT_DIR/run.sh"
Icon=network-wireless
Terminal=true
Categories=Network;Utility;
EOF
    chmod +x "$DESKTOP_FILE"
    echo -e "${GREEN}Desktop shortcut created!${NC}"
else
    echo "Skipping desktop shortcut"
fi
echo ""

# Installation complete
echo "======================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "======================================"
echo ""
echo "Quick Start:"
echo "  1. Connect both Meshtastic radios via USB"
echo "  2. Run: cd $SCRIPT_DIR && ./run.sh"
echo ""
echo "Or run manually:"
echo "  GUI mode:       cd $SCRIPT_DIR && source venv/bin/activate && python gui.py"
echo "  Headless mode:  cd $SCRIPT_DIR && source venv/bin/activate && python bridge.py"
echo ""

if [[ "$INSTALL_SERVICE" =~ ^[Yy]$ ]]; then
    echo "Auto-start service:"
    echo "  The bridge will now start automatically at boot!"
    echo "  Check status with: sudo systemctl status meshtastic-bridge"
    echo ""
fi

if ! groups $USER | grep -q '\bdialout\b'; then
    echo -e "${YELLOW}IMPORTANT: You MUST log out and log back in for serial port access to work!${NC}"
fi

echo ""
echo "For more information, see:"
echo "  - README.md for full documentation"
echo "  - QUICKSTART.md for quick start guide"
echo ""
