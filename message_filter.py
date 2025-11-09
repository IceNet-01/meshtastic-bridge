#!/usr/bin/env python3
"""
Message Filtering System for Meshtastic Bridge
Supports content-based and sender-based filtering
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FilterRule:
    """Represents a message filter rule"""
    name: str
    filter_type: str  # 'keyword', 'regex', 'sender', 'channel'
    pattern: str
    action: str  # 'allow', 'block'
    priority: int = 0


class MessageFilter:
    """Filter messages based on configurable rules"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize message filter

        Args:
            config: Filter configuration dictionary
        """
        self.config = config or {}
        self.enabled = self.config.get('enabled', False)
        self.whitelist_nodes = set(self.config.get('whitelist_nodes', []))
        self.blacklist_nodes = set(self.config.get('blacklist_nodes', []))

        # Content filters
        content_filters = self.config.get('content_filters', {})
        self.keywords = set(content_filters.get('keywords', []))

        # Compile regex patterns
        self.regex_patterns = []
        for pattern in content_filters.get('regex_patterns', []):
            try:
                self.regex_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")

        # Channel filters
        self.allowed_channels = set(self.config.get('allowed_channels', []))
        self.blocked_channels = set(self.config.get('blocked_channels', []))

        # Custom filter rules
        self.custom_rules: List[FilterRule] = []
        self._load_custom_rules()

        # Statistics
        self.stats = {
            'total_checked': 0,
            'total_allowed': 0,
            'total_blocked': 0,
            'blocked_by_sender': 0,
            'blocked_by_content': 0,
            'blocked_by_channel': 0
        }

    def _load_custom_rules(self):
        """Load custom filter rules from configuration"""
        rules_config = self.config.get('custom_rules', [])

        for rule_data in rules_config:
            try:
                rule = FilterRule(
                    name=rule_data.get('name', 'Unnamed'),
                    filter_type=rule_data.get('type', 'keyword'),
                    pattern=rule_data.get('pattern', ''),
                    action=rule_data.get('action', 'allow'),
                    priority=rule_data.get('priority', 0)
                )
                self.custom_rules.append(rule)
            except Exception as e:
                logger.error(f"Failed to load custom rule: {e}")

        # Sort by priority (higher priority first)
        self.custom_rules.sort(key=lambda r: r.priority, reverse=True)

    def should_forward(self, message: Dict[str, Any]) -> bool:
        """
        Determine if a message should be forwarded

        Args:
            message: Message dictionary with keys: id, from, to, text, channel

        Returns:
            True if message should be forwarded, False otherwise
        """
        if not self.enabled:
            return True

        self.stats['total_checked'] += 1

        from_node = message.get('from', '')
        text = message.get('text', '')
        channel = message.get('channel', 0)

        # Check sender whitelist (takes precedence)
        if self.whitelist_nodes:
            if from_node not in self.whitelist_nodes:
                self.stats['total_blocked'] += 1
                self.stats['blocked_by_sender'] += 1
                logger.debug(f"Blocked message from {from_node}: not in whitelist")
                return False

        # Check sender blacklist
        if from_node in self.blacklist_nodes:
            self.stats['total_blocked'] += 1
            self.stats['blocked_by_sender'] += 1
            logger.debug(f"Blocked message from {from_node}: in blacklist")
            return False

        # Check channel filters
        if self.allowed_channels:
            if channel not in self.allowed_channels:
                self.stats['total_blocked'] += 1
                self.stats['blocked_by_channel'] += 1
                logger.debug(f"Blocked message on channel {channel}: not in allowed channels")
                return False

        if channel in self.blocked_channels:
            self.stats['total_blocked'] += 1
            self.stats['blocked_by_channel'] += 1
            logger.debug(f"Blocked message on channel {channel}: in blocked channels")
            return False

        # Check content filters
        if not self._check_content(text):
            self.stats['total_blocked'] += 1
            self.stats['blocked_by_content'] += 1
            logger.debug(f"Blocked message from {from_node}: content filter match")
            return False

        # Check custom rules
        if not self._check_custom_rules(message):
            self.stats['total_blocked'] += 1
            logger.debug(f"Blocked message from {from_node}: custom rule match")
            return False

        # Message passes all filters
        self.stats['total_allowed'] += 1
        return True

    def _check_content(self, text: str) -> bool:
        """
        Check if message content passes filters

        Args:
            text: Message text content

        Returns:
            True if content is allowed, False if blocked
        """
        if not text:
            return True

        text_lower = text.lower()

        # Check keywords
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                logger.debug(f"Content blocked: keyword '{keyword}' found")
                return False

        # Check regex patterns
        for pattern in self.regex_patterns:
            if pattern.search(text):
                logger.debug(f"Content blocked: regex pattern '{pattern.pattern}' matched")
                return False

        return True

    def _check_custom_rules(self, message: Dict[str, Any]) -> bool:
        """
        Check custom filter rules

        Args:
            message: Full message dictionary

        Returns:
            True if message is allowed, False if blocked
        """
        for rule in self.custom_rules:
            if self._evaluate_rule(rule, message):
                # Rule matched
                if rule.action == 'block':
                    logger.debug(f"Custom rule '{rule.name}' blocked message")
                    return False
                elif rule.action == 'allow':
                    logger.debug(f"Custom rule '{rule.name}' allowed message")
                    return True

        # No custom rules matched, allow by default
        return True

    def _evaluate_rule(self, rule: FilterRule, message: Dict[str, Any]) -> bool:
        """
        Evaluate if a rule matches a message

        Args:
            rule: FilterRule to evaluate
            message: Message dictionary

        Returns:
            True if rule matches, False otherwise
        """
        if rule.filter_type == 'keyword':
            text = message.get('text', '')
            return rule.pattern.lower() in text.lower()

        elif rule.filter_type == 'regex':
            text = message.get('text', '')
            try:
                pattern = re.compile(rule.pattern, re.IGNORECASE)
                return bool(pattern.search(text))
            except re.error:
                return False

        elif rule.filter_type == 'sender':
            from_node = message.get('from', '')
            return rule.pattern in from_node

        elif rule.filter_type == 'channel':
            channel = message.get('channel', 0)
            try:
                return channel == int(rule.pattern)
            except (ValueError, TypeError):
                return False

        return False

    def add_rule(self, rule: FilterRule):
        """Add a custom filter rule"""
        self.custom_rules.append(rule)
        self.custom_rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added filter rule: {rule.name}")

    def remove_rule(self, name: str) -> bool:
        """Remove a custom filter rule by name"""
        for i, rule in enumerate(self.custom_rules):
            if rule.name == name:
                self.custom_rules.pop(i)
                logger.info(f"Removed filter rule: {name}")
                return True
        return False

    def add_whitelist_node(self, node_id: str):
        """Add a node to the whitelist"""
        self.whitelist_nodes.add(node_id)
        logger.info(f"Added node to whitelist: {node_id}")

    def add_blacklist_node(self, node_id: str):
        """Add a node to the blacklist"""
        self.blacklist_nodes.add(node_id)
        logger.info(f"Added node to blacklist: {node_id}")

    def remove_whitelist_node(self, node_id: str):
        """Remove a node from the whitelist"""
        self.whitelist_nodes.discard(node_id)
        logger.info(f"Removed node from whitelist: {node_id}")

    def remove_blacklist_node(self, node_id: str):
        """Remove a node from the blacklist"""
        self.blacklist_nodes.discard(node_id)
        logger.info(f"Removed node from blacklist: {node_id}")

    def get_stats(self) -> Dict[str, int]:
        """Get filter statistics"""
        return self.stats.copy()

    def reset_stats(self):
        """Reset filter statistics"""
        self.stats = {
            'total_checked': 0,
            'total_allowed': 0,
            'total_blocked': 0,
            'blocked_by_sender': 0,
            'blocked_by_content': 0,
            'blocked_by_channel': 0
        }
        logger.info("Filter statistics reset")


def main():
    """Test message filter"""
    logging.basicConfig(level=logging.DEBUG)

    # Create filter with sample config
    config = {
        'enabled': True,
        'whitelist_nodes': [],
        'blacklist_nodes': ['!bad123456'],
        'content_filters': {
            'keywords': ['spam', 'advertisement'],
            'regex_patterns': [r'\b\d{3}-\d{3}-\d{4}\b']  # Phone numbers
        },
        'allowed_channels': [],
        'blocked_channels': [],
        'custom_rules': [
            {
                'name': 'Emergency Priority',
                'type': 'keyword',
                'pattern': 'EMERGENCY',
                'action': 'allow',
                'priority': 100
            }
        ]
    }

    filter_system = MessageFilter(config)

    # Test messages
    test_messages = [
        {
            'id': 1,
            'from': '!abc123456',
            'to': 'broadcast',
            'text': 'Hello everyone!',
            'channel': 0
        },
        {
            'id': 2,
            'from': '!bad123456',
            'to': 'broadcast',
            'text': 'This should be blocked',
            'channel': 0
        },
        {
            'id': 3,
            'from': '!xyz789012',
            'to': 'broadcast',
            'text': 'Check out this spam advertisement!',
            'channel': 0
        },
        {
            'id': 4,
            'from': '!def345678',
            'to': 'broadcast',
            'text': 'Call me at 555-123-4567',
            'channel': 0
        },
        {
            'id': 5,
            'from': '!ghi901234',
            'to': 'broadcast',
            'text': 'EMERGENCY: Need help!',
            'channel': 0
        }
    ]

    print("Testing message filter:\n")
    for msg in test_messages:
        result = filter_system.should_forward(msg)
        status = "✓ FORWARD" if result else "✗ BLOCK"
        print(f"{status}: {msg['from']}: {msg['text']}")

    print("\nFilter Statistics:")
    stats = filter_system.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
