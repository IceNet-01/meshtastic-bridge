#!/usr/bin/env python3
"""
Database Manager for Meshtastic Bridge
Provides SQLite persistence for messages, nodes, and statistics
"""

import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database for message persistence"""

    def __init__(self, db_path: str = './meshtastic_bridge.db', retention_days: int = 30):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file
            retention_days: Number of days to retain messages
        """
        self.db_path = db_path
        self.retention_days = retention_days
        self.conn: Optional[sqlite3.Connection] = None
        self.lock = Lock()

        # Create database directory if it doesn't exist
        db_dir = Path(db_path).parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)

        self._initialize_database()

    def _initialize_database(self):
        """Create database tables if they don't exist"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

            cursor = self.conn.cursor()

            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    msg_id TEXT NOT NULL,
                    from_node TEXT NOT NULL,
                    to_node TEXT,
                    text TEXT,
                    channel INTEGER,
                    timestamp DATETIME NOT NULL,
                    forwarded BOOLEAN DEFAULT 0,
                    source_radio TEXT,
                    target_radio TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(msg_id, timestamp)
                )
            ''')

            # Create index on timestamp for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp
                ON messages(timestamp DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_from_node
                ON messages(from_node)
            ''')

            # Nodes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT UNIQUE NOT NULL,
                    node_num INTEGER,
                    hw_model TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    info_json TEXT
                )
            ''')

            # Statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    radio_name TEXT NOT NULL,
                    received INTEGER DEFAULT 0,
                    sent INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    period TEXT DEFAULT 'hourly'
                )
            ''')

            # Settings table (for storing configuration)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Events table (for tracking system events)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    description TEXT,
                    data_json TEXT
                )
            ''')

            self.conn.commit()
            logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def add_message(self, msg_id: str, from_node: str, to_node: str, text: str,
                   channel: int, timestamp: datetime, forwarded: bool = False,
                   source_radio: str = None, target_radio: str = None) -> int:
        """
        Add a message to the database

        Returns:
            Message ID in database
        """
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO messages
                    (msg_id, from_node, to_node, text, channel, timestamp, forwarded, source_radio, target_radio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (msg_id, from_node, to_node, text, channel, timestamp, forwarded, source_radio, target_radio))

                self.conn.commit()

                # Update node statistics
                self.update_node(from_node)

                return cursor.lastrowid

            except Exception as e:
                logger.error(f"Failed to add message: {e}")
                return -1

    def mark_forwarded(self, msg_id: str) -> bool:
        """Mark a message as forwarded"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('''
                    UPDATE messages SET forwarded = 1 WHERE msg_id = ?
                ''', (msg_id,))
                self.conn.commit()
                return cursor.rowcount > 0

            except Exception as e:
                logger.error(f"Failed to mark message as forwarded: {e}")
                return False

    def get_messages(self, limit: int = 100, offset: int = 0,
                    from_node: str = None, channel: int = None,
                    start_time: datetime = None, end_time: datetime = None) -> List[Dict]:
        """
        Retrieve messages from database

        Args:
            limit: Maximum number of messages to return
            offset: Offset for pagination
            from_node: Filter by sender node
            channel: Filter by channel
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            List of message dictionaries
        """
        with self.lock:
            try:
                cursor = self.conn.cursor()

                query = 'SELECT * FROM messages WHERE 1=1'
                params = []

                if from_node:
                    query += ' AND from_node = ?'
                    params.append(from_node)

                if channel is not None:
                    query += ' AND channel = ?'
                    params.append(channel)

                if start_time:
                    query += ' AND timestamp >= ?'
                    params.append(start_time)

                if end_time:
                    query += ' AND timestamp <= ?'
                    params.append(end_time)

                query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
                params.extend([limit, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

            except Exception as e:
                logger.error(f"Failed to retrieve messages: {e}")
                return []

    def search_messages(self, search_text: str, limit: int = 100) -> List[Dict]:
        """Search messages by text content"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT * FROM messages
                    WHERE text LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (f'%{search_text}%', limit))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

            except Exception as e:
                logger.error(f"Failed to search messages: {e}")
                return []

    def update_node(self, node_id: str, info: Dict = None):
        """Update or insert node information"""
        with self.lock:
            try:
                cursor = self.conn.cursor()

                # Check if node exists
                cursor.execute('SELECT id FROM nodes WHERE node_id = ?', (node_id,))
                exists = cursor.fetchone()

                if exists:
                    # Update existing node
                    cursor.execute('''
                        UPDATE nodes
                        SET last_seen = CURRENT_TIMESTAMP,
                            message_count = message_count + 1
                        WHERE node_id = ?
                    ''', (node_id,))
                else:
                    # Insert new node
                    info_json = json.dumps(info) if info else None
                    cursor.execute('''
                        INSERT INTO nodes (node_id, info_json, message_count)
                        VALUES (?, ?, 1)
                    ''', (node_id, info_json))

                self.conn.commit()

            except Exception as e:
                logger.error(f"Failed to update node: {e}")

    def get_nodes(self, active_hours: int = 24) -> List[Dict]:
        """
        Get list of nodes

        Args:
            active_hours: Only return nodes active in last N hours (0 for all)

        Returns:
            List of node dictionaries
        """
        with self.lock:
            try:
                cursor = self.conn.cursor()

                if active_hours > 0:
                    cutoff = datetime.now() - timedelta(hours=active_hours)
                    cursor.execute('''
                        SELECT * FROM nodes
                        WHERE last_seen >= ?
                        ORDER BY last_seen DESC
                    ''', (cutoff,))
                else:
                    cursor.execute('SELECT * FROM nodes ORDER BY last_seen DESC')

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

            except Exception as e:
                logger.error(f"Failed to retrieve nodes: {e}")
                return []

    def record_statistics(self, radio_name: str, received: int, sent: int, errors: int, period: str = 'hourly'):
        """Record statistics snapshot"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO statistics (radio_name, received, sent, errors, period)
                    VALUES (?, ?, ?, ?, ?)
                ''', (radio_name, received, sent, errors, period))
                self.conn.commit()

            except Exception as e:
                logger.error(f"Failed to record statistics: {e}")

    def get_statistics(self, hours: int = 24, period: str = 'hourly') -> List[Dict]:
        """Get statistics for the last N hours"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cutoff = datetime.now() - timedelta(hours=hours)

                cursor.execute('''
                    SELECT * FROM statistics
                    WHERE timestamp >= ? AND period = ?
                    ORDER BY timestamp DESC
                ''', (cutoff, period))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

            except Exception as e:
                logger.error(f"Failed to retrieve statistics: {e}")
                return []

    def log_event(self, event_type: str, description: str, data: Dict = None):
        """Log a system event"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                data_json = json.dumps(data) if data else None

                cursor.execute('''
                    INSERT INTO events (event_type, description, data_json)
                    VALUES (?, ?, ?)
                ''', (event_type, description, data_json))
                self.conn.commit()

            except Exception as e:
                logger.error(f"Failed to log event: {e}")

    def get_events(self, limit: int = 100, event_type: str = None) -> List[Dict]:
        """Retrieve system events"""
        with self.lock:
            try:
                cursor = self.conn.cursor()

                if event_type:
                    cursor.execute('''
                        SELECT * FROM events
                        WHERE event_type = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (event_type, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM events
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (limit,))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

            except Exception as e:
                logger.error(f"Failed to retrieve events: {e}")
                return []

    def cleanup_old_messages(self) -> int:
        """Delete messages older than retention period"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cutoff = datetime.now() - timedelta(days=self.retention_days)

                cursor.execute('DELETE FROM messages WHERE timestamp < ?', (cutoff,))
                self.conn.commit()

                deleted = cursor.rowcount
                logger.info(f"Cleaned up {deleted} old messages")
                return deleted

            except Exception as e:
                logger.error(f"Failed to cleanup old messages: {e}")
                return 0

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        with self.lock:
            try:
                cursor = self.conn.cursor()

                stats = {}

                # Total messages
                cursor.execute('SELECT COUNT(*) as count FROM messages')
                stats['total_messages'] = cursor.fetchone()['count']

                # Forwarded messages
                cursor.execute('SELECT COUNT(*) as count FROM messages WHERE forwarded = 1')
                stats['forwarded_messages'] = cursor.fetchone()['count']

                # Messages today
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                cursor.execute('SELECT COUNT(*) as count FROM messages WHERE timestamp >= ?', (today,))
                stats['messages_today'] = cursor.fetchone()['count']

                # Total nodes
                cursor.execute('SELECT COUNT(*) as count FROM nodes')
                stats['total_nodes'] = cursor.fetchone()['count']

                # Active nodes (last 24 hours)
                cutoff_24h = datetime.now() - timedelta(hours=24)
                cursor.execute('SELECT COUNT(*) as count FROM nodes WHERE last_seen >= ?', (cutoff_24h,))
                stats['active_nodes_24h'] = cursor.fetchone()['count']

                # Most active sender
                cursor.execute('''
                    SELECT from_node, COUNT(*) as count
                    FROM messages
                    GROUP BY from_node
                    ORDER BY count DESC
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                if row:
                    stats['most_active_sender'] = {'node': row['from_node'], 'count': row['count']}

                return stats

            except Exception as e:
                logger.error(f"Failed to get summary stats: {e}")
                return {}

    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database: {e}")


def main():
    """Test database manager"""
    logging.basicConfig(level=logging.INFO)

    # Create database
    print("Initializing database...")
    db = DatabaseManager('./test_bridge.db')

    # Add some test messages
    print("\nAdding test messages...")
    now = datetime.now()

    db.add_message('msg1', '!abc123456', 'broadcast', 'Hello world!', 0, now, True, 'radio1', 'radio2')
    db.add_message('msg2', '!def789012', 'broadcast', 'Test message', 0, now, False, 'radio2', 'radio1')
    db.add_message('msg3', '!abc123456', '!xyz345678', 'Direct message', 0, now, True, 'radio1', 'radio2')

    # Retrieve messages
    print("\nRetrieving messages...")
    messages = db.get_messages(limit=10)
    for msg in messages:
        print(f"  {msg['timestamp']}: {msg['from_node']} -> {msg['to_node']}: {msg['text']}")

    # Get nodes
    print("\nActive nodes:")
    nodes = db.get_nodes()
    for node in nodes:
        print(f"  {node['node_id']}: {node['message_count']} messages")

    # Get summary stats
    print("\nSummary statistics:")
    stats = db.get_summary_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Log an event
    db.log_event('test', 'Database test completed', {'status': 'success'})

    # Close database
    db.close()
    print("\nDatabase test completed!")


if __name__ == "__main__":
    main()
