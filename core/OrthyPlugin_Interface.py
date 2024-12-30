# core/plugin_interface.py

from abc import ABC, abstractmethod

class OrthyPlugin(ABC):
    """Base class for Orthy plugins"""
    
    @abstractmethod
    def initialize(self, app_instance):
        """Called when plugin is loaded"""
        pass
    
    @abstractmethod
    def get_name(self):
        """Return plugin name"""
        pass
    
    @abstractmethod
    def get_btn_configs(self):
        """Return list of button configurations"""
        return []
    
    @abstractmethod
    def cleanup(self):
        """Called when plugin is unloaded"""
        pass