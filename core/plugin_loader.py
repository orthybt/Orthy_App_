# core/plugin_loader.py
import importlib
import os
import sys
import logging
from core.OrthyPlugin_Interface import OrthyPlugin

class PluginLoader:
    def __init__(self, plugin_directory='plugins'):
        self.plugin_directory = plugin_directory
        self.plugins = {}

    def load_plugins(self, manager_instance):
        """
        Loads all plugins from the specified directory.
        Each plugin should have a class that inherits from OrthyPlugin and implements required methods.
        """
        sys.path.insert(0, self.plugin_directory)  # Add plugin directory to sys.path

        for filename in os.listdir(self.plugin_directory):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(module_name)
                    for attribute_name in dir(module):
                        attribute = getattr(module, attribute_name)
                        if isinstance(attribute, type) and issubclass(attribute, OrthyPlugin) and attribute != OrthyPlugin:
                            plugin_instance = attribute()
                            plugin_instance.initialize(manager_instance)
                            self.plugins[plugin_instance.get_name()] = plugin_instance
                            logging.info(f"Loaded plugin: {plugin_instance.get_name()}")
                except Exception as e:
                    logging.error(f"Failed to load plugin {module_name}: {e}")

        sys.path.pop(0)  # Clean up sys.path

    def get_plugin(self, name):
        return self.plugins.get(name)

    def cleanup(self):
        for plugin in self.plugins.values():
            plugin.cleanup()
        self.plugins.clear()
