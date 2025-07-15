"""
Configuration Manager for CT-MA System.

Handles loading and managing configuration from YAML files with environment variable support.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from omegaconf import OmegaConf, DictConfig


class ConfigManager:
    """Configuration manager with support for YAML files and environment variables."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to main config file. If None, uses default.
        """
        self.config_dir = Path(__file__).parent.parent.parent / "config"
        self.config_path = config_path or (self.config_dir / "system_config.yaml")
        self.config = self._load_config()
    
    def _load_config(self) -> DictConfig:
        """Load configuration from YAML files."""
        try:
            # Load main config
            main_config = OmegaConf.load(self.config_path)
            
            # Load additional configs
            agent_config = OmegaConf.load(self.config_dir / "agent_prompts.yaml")
            rag_config = OmegaConf.load(self.config_dir / "rag_config.yaml")
            
            # Merge configs
            config = OmegaConf.merge(main_config, {"agents": agent_config.agents})
            config = OmegaConf.merge(config, {"rag": rag_config})
            
            # Resolve environment variables
            config = self._resolve_env_vars(config)
            
            return config
            
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def _resolve_env_vars(self, config: DictConfig) -> DictConfig:
        """Resolve environment variables in config values."""
        def resolve_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.getenv(env_var, value)
            elif isinstance(value, DictConfig):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            return value
        
        return OmegaConf.create({k: resolve_value(v) for k, v in config.items()})
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'models.llm.temperature')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            return OmegaConf.select(self.config, key, default=default)
        except Exception:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        OmegaConf.set(self.config, key, value)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Configuration section as dictionary
        """
        return OmegaConf.to_container(self.config.get(section, {}))
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            path: Output path. If None, overwrites original file.
        """
        output_path = path or self.config_path
        with open(output_path, 'w', encoding='utf-8') as f:
            OmegaConf.save(self.config, f)
    
    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration from dictionary.
        
        Args:
            updates: Dictionary of updates
        """
        update_config = OmegaConf.create(updates)
        self.config = OmegaConf.merge(self.config, update_config)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return OmegaConf.to_container(self.config, resolve=True)
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style setting."""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in configuration."""
        return OmegaConf.select(self.config, key) is not None
