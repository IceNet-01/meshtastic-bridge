#!/bin/bash
# Helper script to run the Meshtastic Bridge

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Meshtastic Bridge Launcher${NC}"
echo "======================================"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

echo ""
echo "Detection Mode:"
echo "  [1] Auto-detect radios (recommended)"
echo "  [2] Manual port selection"
read -p "Choose mode [1]: " MODE
MODE=${MODE:-1}

if [ "$MODE" == "2" ]; then
    # Manual mode
    echo ""
    echo "Detecting USB serial devices..."
    DEVICES=($(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null))

    if [ ${#DEVICES[@]} -eq 0 ]; then
        echo -e "${RED}Error: No USB serial devices found!${NC}"
        echo "Please connect your Meshtastic radios and try again."
        exit 1
    fi

    echo -e "${GREEN}Found ${#DEVICES[@]} device(s):${NC}"
    for i in "${!DEVICES[@]}"; do
        echo "  [$i] ${DEVICES[$i]}"
    done

    # Determine which devices to use
    if [ ${#DEVICES[@]} -eq 1 ]; then
        echo -e "${RED}Error: Only one device found. Need at least 2 radios.${NC}"
        exit 1
    elif [ ${#DEVICES[@]} -eq 2 ]; then
        PORT1="${DEVICES[0]}"
        PORT2="${DEVICES[1]}"
        echo -e "${GREEN}Using detected devices:${NC}"
        echo "  Radio 1: $PORT1"
        echo "  Radio 2: $PORT2"
    else
        # More than 2 devices, ask user
        echo ""
        echo "Please select which devices to use:"
        read -p "Radio 1 device number [0]: " RADIO1
        RADIO1=${RADIO1:-0}
        read -p "Radio 2 device number [1]: " RADIO2
        RADIO2=${RADIO2:-1}

        PORT1="${DEVICES[$RADIO1]}"
        PORT2="${DEVICES[$RADIO2]}"

        echo -e "${GREEN}Selected:${NC}"
        echo "  Radio 1: $PORT1"
        echo "  Radio 2: $PORT2"
    fi
    MANUAL_PORTS="$PORT1 $PORT2"
else
    # Auto-detect mode
    echo -e "${GREEN}Using auto-detection mode${NC}"
    echo "The bridge will automatically detect and connect to your radios."
    MANUAL_PORTS=""
fi

# Ask whether to run GUI or headless
echo ""
read -p "Run with GUI? [Y/n]: " USE_GUI
USE_GUI=${USE_GUI:-Y}

echo ""
echo "======================================"
echo -e "${GREEN}Starting Meshtastic Bridge...${NC}"
echo "Press Ctrl+C to stop"
echo "======================================"
echo ""

if [[ "$USE_GUI" =~ ^[Yy]$ ]]; then
    python gui.py $MANUAL_PORTS
else
    python bridge.py $MANUAL_PORTS
fi
