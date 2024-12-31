import tkinter as tk
import logging

class GuiManager:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        self.create_main_buttons()

    def create_main_buttons(self):
        # Main button frame
        button_frame = tk.Frame(self.root)
        button_frame.grid(row=0, column=0, sticky="nsew")
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Transparency
        self.transparency_button = tk.Button(
            button_frame, text="Transparency",
            command=self.toggle_transparency
        )
        self.transparency_button.grid(row=0, column=0, padx=2, pady=2)

        # Hide/Show Image
        self.hide_show_button = tk.Button(
            button_frame, text="Hide/Show",
            command=self.toggle_image_visibility
        )
        self.hide_show_button.grid(row=0, column=1, padx=2, pady=2)

        # Flip Horizontal
        self.flip_h_button = tk.Button(
            button_frame, text="Flip H",
            command=self.flip_image_horizontal
        )
        self.flip_h_button.grid(row=0, column=2, padx=2, pady=2)

        # Flip Vertical
        self.flip_v_button = tk.Button(
            button_frame, text="Flip V",
            command=self.flip_image_vertical
        )
        self.flip_v_button.grid(row=0, column=3, padx=2, pady=2)

        # Rotation Point
        self.rot_pt_button = tk.Button(
            button_frame, text="Rot Pt",
            command=self.toggle_rotation_point_mode
        )
        self.rot_pt_button.grid(row=0, column=4, padx=2, pady=2)

        # Zoom In/Out
        self.zoom_in_button = tk.Button(
            button_frame, text="+",
            command=self.zoom_in
        )
        self.zoom_in_button.grid(row=1, column=0, padx=2, pady=2)

        self.zoom_out_button = tk.Button(
            button_frame, text="-",
            command=self.zoom_out
        )
        self.zoom_out_button.grid(row=1, column=1, padx=2, pady=2)

        # Fine Zoom In/Out
        self.fine_zoom_in_button = tk.Button(
            button_frame, text="Fine +",
            command=self.fine_zoom_in
        )
        self.fine_zoom_in_button.grid(row=1, column=2, padx=2, pady=2)

        self.fine_zoom_out_button = tk.Button(
            button_frame, text="Fine -",
            command=self.fine_zoom_out
        )
        self.fine_zoom_out_button.grid(row=1, column=3, padx=2, pady=2)

        # Rotate +/-
        self.rotate_plus_button = tk.Button(
            button_frame, text="Rot +",
            command=self.fine_rotate_clockwise
        )
        self.rotate_plus_button.grid(row=1, column=4, padx=2, pady=2)

        self.rotate_minus_button = tk.Button(
            button_frame, text="Rot -",
            command=self.fine_rotate_counterclockwise
        )
        self.rotate_minus_button.grid(row=1, column=5, padx=2, pady=2)

        # Additional shape/style buttons
        shapes = ["angul", "ruler", "normal", "tapered", "Ovoide", "Narrow T", "Narrow O"]
        for idx, shape in enumerate(shapes):
            btn = tk.Button(
                button_frame,
                text=shape,
                command=lambda s=shape: self.handle_shape(s)
            )
            btn.grid(row=2, column=idx, padx=2, pady=2)

    def toggle_transparency(self):
        logging.info("Toggling transparency...")

    def toggle_image_visibility(self):
        logging.info("Toggling image visibility...")

    def flip_image_horizontal(self):
        logging.info("Flipping image horizontally...")

    def flip_image_vertical(self):
        logging.info("Flipping image vertically...")

    def toggle_rotation_point_mode(self):
        logging.info("Toggling rotation point mode...")

    def zoom_in(self):
        logging.info("Zoom in...")

    def zoom_out(self):
        logging.info("Zoom out...")

    def fine_zoom_in(self):
        logging.info("Fine zoom in...")

    def fine_zoom_out(self):
        logging.info("Fine zoom out...")

    def fine_rotate_clockwise(self):
        logging.info("Rotate image clockwise...")

    def fine_rotate_counterclockwise(self):
        logging.info("Rotate image counterclockwise...")

    def handle_shape(self, shape):
        logging.info(f"Shape selected: {shape}")