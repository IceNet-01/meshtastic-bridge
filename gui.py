#!/usr/bin/env python3
"""
Meshtastic Bridge GUI - Terminal UI for monitoring and controlling the bridge
"""

import sys
from datetime import datetime
from threading import Thread
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, Input, DataTable, Log, Label
from textual.binding import Binding
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich import box

from bridge import MeshtasticBridge


class StatsPanel(Static):
    """Widget to display bridge statistics"""

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def on_mount(self):
        """Set up update timer"""
        self.set_interval(1, self.update_stats)

    def update_stats(self):
        """Update statistics display"""
        stats = self.bridge.get_stats()

        table = Table(box=box.ROUNDED, expand=True)
        table.add_column("Radio", style="cyan", width=12)
        table.add_column("Received", justify="right", style="green")
        table.add_column("Sent", justify="right", style="yellow")
        table.add_column("Errors", justify="right", style="red")

        table.add_row(
            "Radio 1",
            str(stats['radio1']['received']),
            str(stats['radio1']['sent']),
            str(stats['radio1']['errors'])
        )
        table.add_row(
            "Radio 2",
            str(stats['radio2']['received']),
            str(stats['radio2']['sent']),
            str(stats['radio2']['errors'])
        )

        tracker_stats = stats.get('tracker', {})
        table.add_row(
            "Total",
            str(tracker_stats.get('total_seen', 0)),
            str(tracker_stats.get('total_forwarded', 0)),
            "-"
        )

        self.update(table)


class NodeInfoPanel(Static):
    """Widget to display node information"""

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def on_mount(self):
        """Set up update timer"""
        self.set_interval(5, self.update_info)
        self.update_info()

    def update_info(self):
        """Update node information display"""
        table = Table(box=box.ROUNDED, expand=True, title="Node Information")
        table.add_column("Radio", style="cyan", width=12)
        table.add_column("Status", style="green")
        table.add_column("Info")

        # Radio 1 info
        info1 = self.bridge.get_node_info('radio1')
        status1 = "Connected" if self.bridge.interface1 else "Disconnected"
        info1_str = str(info1) if info1 else "No info available"

        table.add_row("Radio 1", status1, info1_str[:50])

        # Radio 2 info
        info2 = self.bridge.get_node_info('radio2')
        status2 = "Connected" if self.bridge.interface2 else "Disconnected"
        info2_str = str(info2) if info2 else "No info available"

        table.add_row("Radio 2", status2, info2_str[:50])

        self.update(table)


class MessageLog(Static):
    """Widget to display message log"""

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.messages = []

    def on_mount(self):
        """Set up update timer"""
        self.set_interval(1, self.update_messages)

    def update_messages(self):
        """Update message display"""
        recent = self.bridge.get_recent_messages(30)

        # Build display text
        lines = []
        for msg in recent:
            timestamp = msg['timestamp'].strftime('%H:%M:%S')
            from_node = msg['from'][-4:] if len(msg['from']) > 4 else msg['from']
            status = "[green]✓[/green]" if msg['forwarded'] else "[yellow]•[/yellow]"
            text = msg['text'][:60]

            line = f"{status} [{timestamp}] {from_node}: {text}"
            lines.append(line)

        content = "\n".join(lines) if lines else "[dim]No messages yet...[/dim]"
        self.update(content)


class MeshtasticBridgeApp(App):
    """Textual app for Meshtastic Bridge"""

    CSS = """
    Screen {
        background: $surface;
    }

    #stats-container {
        height: 8;
        border: solid $primary;
        margin: 1;
    }

    #nodes-container {
        height: 8;
        border: solid $primary;
        margin: 1;
    }

    #messages-container {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }

    #input-container {
        height: 5;
        border: solid $primary;
        margin: 1;
    }

    #send-button {
        margin-left: 1;
    }

    Label {
        padding: 1;
    }

    Input {
        margin: 1;
    }

    .panel-title {
        text-style: bold;
        color: $accent;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def compose(self) -> ComposeResult:
        """Compose the UI"""
        yield Header(show_clock=True)

        # Stats panel
        with Container(id="stats-container"):
            yield Label("[b]Bridge Statistics[/b]", classes="panel-title")
            yield StatsPanel(self.bridge)

        # Node info panel
        with Container(id="nodes-container"):
            yield Label("[b]Node Information[/b]", classes="panel-title")
            yield NodeInfoPanel(self.bridge)

        # Message log
        with Container(id="messages-container"):
            yield Label("[b]Message Log[/b]", classes="panel-title")
            yield ScrollableContainer(MessageLog(self.bridge))

        # Input area
        with Container(id="input-container"):
            yield Label("[b]Send Message[/b]", classes="panel-title")
            with Horizontal():
                yield Input(placeholder="Type message here...", id="message-input")
                yield Button("Send (Radio 1)", id="send-radio1", variant="primary")
                yield Button("Send (Radio 2)", id="send-radio2", variant="success")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        message_input = self.query_one("#message-input", Input)
        message = message_input.value.strip()

        if not message:
            return

        if event.button.id == "send-radio1":
            self.bridge.send_message(message, radio='radio1', channel=0)
        elif event.button.id == "send-radio2":
            self.bridge.send_message(message, radio='radio2', channel=0)

        # Clear input
        message_input.value = ""

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input"""
        if event.input.id == "message-input":
            # Default to radio 1
            message = event.input.value.strip()
            if message:
                self.bridge.send_message(message, radio='radio1', channel=0)
                event.input.value = ""

    def action_refresh(self) -> None:
        """Refresh the display"""
        self.refresh()

    def action_quit(self) -> None:
        """Quit the application"""
        self.bridge.close()
        self.exit()


def main():
    """Main entry point for the GUI"""
    # Support both auto-detection and manual port specification
    if len(sys.argv) == 3:
        # Manual mode
        port1 = sys.argv[1]
        port2 = sys.argv[2]
        print(f"Using specified ports: {port1} and {port2}")
        bridge = MeshtasticBridge(port1, port2, auto_detect=False)
    elif len(sys.argv) == 1:
        # Auto-detection mode
        print("Auto-detecting Meshtastic radios...")
        print("Please ensure both radios are connected via USB.")
        bridge = MeshtasticBridge(auto_detect=True)
    else:
        print("Usage: python gui.py [port1] [port2]")
        print("")
        print("Auto-detection mode (recommended):")
        print("  python gui.py")
        print("")
        print("Manual mode:")
        print("  python gui.py /dev/ttyUSB0 /dev/ttyUSB1")
        sys.exit(1)

    try:
        print("Connecting to radios...")
        bridge.connect()
        print("Connected! Starting GUI...")

        # Run the app
        app = MeshtasticBridgeApp(bridge)
        app.run()

    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
