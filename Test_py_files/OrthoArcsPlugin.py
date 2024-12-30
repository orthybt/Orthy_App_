import logging
from core.OrthyPlugin_Interface import OrthyPlugin

class OrthoArcsPlugin(OrthyPlugin):
    def __init__(self, button_factory):
        """
        button_factory should be an instance of ButtonFactory,
        which provides methods to create button configurations.
        """
        self.button_factory = button_factory
        self.app = None
        self.additional_images_visibility = {}
        # No direct references to other plugins here; we only
        # use plugin_loader from self.app inside toggle_predefined_image.

    def get_name(self):
        return "OrthoArcsPlugin"

    def initialize(self, app_instance):
        """
        Called when the plugin is loaded by the plugin_loader.
        """
        self.app = app_instance

    def get_buttons(self):
        """
        Returns a list of button configurations. For example, we can have
        multiple arc images, each toggled by its own button.
        """
        # Example arcs
        arcs = [
            ("NarrowOvoide).svg",   "NarrowOvoide"),
            ("NarrowTapered.svg",   "NarrowTapered"),
            ("Normal.svg",          "Normal"),
            ("Ovoid.svg",           "Ovoid"),
            ("Tapered.svg",         "Tapered"),
            # Add more as needed...
        ]

        button_configs = []
        for filename, image_key in arcs:
            # Is this image currently active/visible?
            is_active = self.additional_images_visibility.get(image_key, False)

            # The button factory call returns a config dictionary for a "predefined image" button.
            # We pass a lambda that will call toggle_predefined_image with the correct arguments
            # (image_key, filename, and the label to display in logs).
            btn_cfg = self.button_factory.get_predefined_image_button(
                image_filepath=filename,
                active_image_sentinel=is_active,
                action=lambda ik=image_key, fn=filename: self.toggle_predefined_image(ik, fn, ik)
            )
            button_configs.append(btn_cfg)

        return button_configs

    def toggle_predefined_image(self, image_key, filename, button_label):
        """
        Toggles a specific predefined image on/off, analogous to your snippet.
        Uses self.app to access the main window, images dictionary, etc.
        """
        if not self.additional_images_visibility.get(image_key, False):
            # Hide previously active image
            if self.app.active_image_name and self.app.active_image_name in self.app.images:
                self.app.images[self.app.active_image_name].visible = False

            # Load if not already loaded
            if image_key not in self.app.images:
                self.app.load_default_image(image_key, filename)
            else:
                self.app.images[image_key].visible = True
                self.app.draw_images()

            # Mark as now visible
            self.additional_images_visibility[image_key] = True
            logging.info(f"{image_key} image made visible.")

            self.app.previous_active_image_name = self.app.active_image_name
            self.app.active_image_name = image_key

            # Enable image control via plugin
            ic_plugin = self.app.plugin_loader.get_plugin("image_control_plugin")
            if ic_plugin:
                ic_plugin.toggle_image_control(True)

        else:
            # The image is currently on, so hide it
            if image_key in self.app.images:
                self.app.images[image_key].visible = False
                self.app.draw_images()

            self.additional_images_visibility[image_key] = False
            logging.info(f"{image_key} image hidden.")

            # Instead of restoring a previous image, just hide the window
            if self.app.image_window_visible:
                self.app.toggle_image_window()

            # Disable image control if we were controlling this image
            ic_plugin = self.app.plugin_loader.get_plugin("image_control_plugin")
            if ic_plugin:
                ic_plugin.toggle_image_control(False)

            # Redraw after changes
            self.app.draw_images()


    def cleanup(self):
        """
        Called when the plugin is unloaded by the plugin_loader.
        Perform any required cleanup here.
        """
        pass
