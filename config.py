#!/usr/bin/env python3
"""
Configuration Manager for Meshtastic Bridge
Supports YAML and JSON configuration files
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when there's a configuration error"""
    pass


class BridgeConfig:
    """Configuration manager for the Meshtastic Bridge"""

    DEFAULT_CONFIG = {
        'bridge': {
            'auto_detect': True,
            'ports': [],
            'message_tracking': {
                'max_age_minutes': 10,
                'max_messages': 1000
            }
        },
        'channels': {
            'mapping': {
                'LongFast': 'LongModerate',
                'LongModerate': 'LongFast'
            }
        },
        'filtering': {
            'enabled': False,
            'whitelist_nodes': [],
            'blacklist_nodes': [],
            'content_filters': {
                'keywords': [],
                'regex_patterns': []
            }
        },
        'database': {
            'enabled': False,
            'path': './meshtastic_bridge.db',
            'retention_days': 30
        },
        'metrics': {
            'enabled': False,
            'port': 9090,
            'path': '/metrics'
        },
        'mqtt': {
            'enabled': False,
            'broker': 'localhost',
            'port': 1883,
            'username': None,
            'password': None,
            'topic_prefix': 'meshtastic/bridge',
            'publish_incoming': True,
            'publish_outgoing': True
        },
        'web': {
            'enabled': False,
            'host': '0.0.0.0',
            'port': 8080,
            'api_enabled': True
        },
        'logging': {
            'level': 'INFO',
            'file': None,
            'max_bytes': 10485760,  # 10MB
            'backup_count': 5
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager

        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        # Start with default config
        config = self.DEFAULT_CONFIG.copy()

        # If no config path specified, look for default locations
        if not self.config_path:
            default_paths = [
                './meshtastic-bridge.yaml',
                './meshtastic-bridge.yml',
                './meshtastic-bridge.json',
                os.path.expanduser('~/.meshtastic-bridge.yaml'),
                os.path.expanduser('~/.config/meshtastic-bridge.yaml'),
                '/etc/meshtastic-bridge/config.yaml'
            ]

            for path in default_paths:
                if os.path.exists(path):
                    self.config_path = path
                    logger.info(f"Found configuration file: {path}")
                    break

        # Load from file if it exists
        if self.config_path and os.path.exists(self.config_path):
            try:
                config = self._merge_configs(config, self._read_config_file(self.config_path))
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
                raise ConfigurationError(f"Failed to load configuration: {e}")
        else:
            logger.info("Using default configuration (no config file found)")

        return config

    def _read_config_file(self, path: str) -> Dict[str, Any]:
        """Read configuration file (YAML or JSON)"""
        with open(path, 'r') as f:
            if path.endswith(('.yaml', '.yml')):
                if not YAML_AVAILABLE:
                    raise ConfigurationError("PyYAML not installed. Install with: pip install pyyaml")
                return yaml.safe_load(f) or {}
            elif path.endswith('.json'):
                return json.load(f)
            else:
                raise ConfigurationError(f"Unsupported config file format: {path}")

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two configuration dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Examples:
            config.get('bridge.auto_detect')
            config.get('mqtt.enabled')
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation

        Examples:
            config.set('bridge.auto_detect', True)
            config.set('mqtt.enabled', False)
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to file"""
        save_path = path or self.config_path

        if not save_path:
            raise ConfigurationError("No configuration path specified")

        # Determine format from extension
        with open(save_path, 'w') as f:
            if save_path.endswith(('.yaml', '.yml')):
                if not YAML_AVAILABLE:
                    raise ConfigurationError("PyYAML not installed. Install with: pip install pyyaml")
                yaml.dump(self.config, f, default_flow_style=False)
            elif save_path.endswith('.json'):
                json.dump(self.config, f, indent=2)
            else:
                raise ConfigurationError(f"Unsupported config file format: {save_path}")

        logger.info(f"Saved configuration to {save_path}")

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings/errors

        Returns:
            List of validation messages (empty if valid)
        """
        warnings = []

        # Validate bridge settings
        if not self.get('bridge.auto_detect') and not self.get('bridge.ports'):
            warnings.append("auto_detect is False but no ports specified")

        # Validate MQTT settings
        if self.get('mqtt.enabled'):
            if not self.get('mqtt.broker'):
                warnings.append("MQTT enabled but no broker specified")

        # Validate database settings
        if self.get('database.enabled'):
            db_path = self.get('database.path')
            if db_path:
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    warnings.append(f"Database directory does not exist: {db_dir}")

        # Validate web settings
        if self.get('web.enabled'):
            port = self.get('web.port')
            if not isinstance(port, int) or port < 1 or port > 65535:
                warnings.append(f"Invalid web port: {port}")

        # Validate metrics settings
        if self.get('metrics.enabled'):
            port = self.get('metrics.port')
            if not isinstance(port, int) or port < 1 or port > 65535:
                warnings.append(f"Invalid metrics port: {port}")

        return warnings

    def create_example_config(self, path: str) -> None:
        """Create an example configuration file"""
        example_config = {
            '# Meshtastic Bridge Configuration': None,
            'bridge': {
                'auto_detect': True,
                'ports': ['# /dev/ttyUSB0', '# /dev/ttyUSB1'],
                'message_tracking': {
                    'max_age_minutes': 10,
                    'max_messages': 1000
                }
            },
            'channels': {
                'mapping': {
                    'LongFast': 'LongModerate',
                    'LongModerate': 'LongFast'
                }
            },
            'filtering': {
                'enabled': False,
                'whitelist_nodes': [],
                'blacklist_nodes': [],
                'content_filters': {
                    'keywords': ['urgent', 'emergency'],
                    'regex_patterns': []
                }
            },
            'database': {
                'enabled': True,
                'path': './meshtastic_bridge.db',
                'retention_days': 30
            },
            'metrics': {
                'enabled': True,
                'port': 9090,
                'path': '/metrics'
            },
            'mqtt': {
                'enabled': False,
                'broker': 'localhost',
                'port': 1883,
                'username': None,
                'password': None,
                'topic_prefix': 'meshtastic/bridge',
                'publish_incoming': True,
                'publish_outgoing': True
            },
            'web': {
                'enabled': True,
                'host': '0.0.0.0',
                'port': 8080,
                'api_enabled': True
            },
            'logging': {
                'level': 'INFO',
                'file': './meshtastic-bridge.log',
                'max_bytes': 10485760,
                'backup_count': 5
            }
        }

        # Remove comment entries for JSON
        if path.endswith('.json'):
            example_config = {k: v for k, v in example_config.items() if not k.startswith('#')}

        with open(path, 'w') as f:
            if path.endswith(('.yaml', '.yml')):
                if not YAML_AVAILABLE:
                    raise ConfigurationError("PyYAML not installed. Install with: pip install pyyaml")
                yaml.dump(example_config, f, default_flow_style=False, sort_keys=False)
            elif path.endswith('.json'):
                json.dump(example_config, f, indent=2)
            else:
                raise ConfigurationError(f"Unsupported config file format: {path}")

        logger.info(f"Created example configuration file: {path}")


def main():
    """Test configuration manager"""
    logging.basicConfig(level=logging.INFO)

    # Create example config
    print("Creating example configuration file...")
    config = BridgeConfig()
    config.create_example_config('meshtastic-bridge-example.yaml')
    print("Example config created: meshtastic-bridge-example.yaml")

    # Load and validate
    print("\nLoading configuration...")
    config = BridgeConfig('meshtastic-bridge-example.yaml')

    print("\nConfiguration values:")
    print(f"  Auto-detect: {config.get('bridge.auto_detect')}")
    print(f"  Database enabled: {config.get('database.enabled')}")
    print(f"  MQTT enabled: {config.get('mqtt.enabled')}")
    print(f"  Web enabled: {config.get('web.enabled')}")

    print("\nValidating configuration...")
    warnings = config.validate()
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("Configuration is valid!")


if __name__ == "__main__":
    main()
