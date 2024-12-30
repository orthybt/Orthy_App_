import tkinter as tk

class CustomButton(tk.Button):
    '''Custom button class that stores the plugin name(custom attribute!) and button object'''
    def __init__(self, button, plugin_name):
        self.button = button
        self.plugin_name = plugin_name

class ButtonFactory:

    def __init__(self):
        self.button_configs = {}
        self.buttons = {}

    def init_button_configs(self, ):
        self.button_configs = {
            'maestro_controls_cfg': 
                {'text': 'Maestro Controls', 
                 'command': self.button1_click},
            'low_level_key_remap_cfg': 
                {'text': 'Button 2', 'command': self.button2_click},
        }

    def create_button(self, parent, plugin_name, btn_cfg):{

    }
