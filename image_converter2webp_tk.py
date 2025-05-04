import sys
import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import customtkinter as ctk
import ctypes
import time
import io
import threading

# Set the appearance mode and color theme
ctk.set_appearance_mode("System")  # Режим: "System", "Dark" або "Light"
ctk.set_default_color_theme("blue")  # Теми: "blue", "green", "dark-blue"

SCALE_FACTORS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]

APP_CAPTION = "JPG/PNG to WEBP Converter"


def timer_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()  # Record the start time
        result = func(*args, **kwargs)  # Call the function
        end_time = time.time()  # Record the end time
        duration = end_time - start_time  # Calculate the time difference
        print(f"Function {func.__name__} took {duration:.4f} seconds to execute.")
        return result

    return wrapper


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class ImageFrame(ctk.CTkFrame):
    def __init__(self, master, app=None, sync_frame=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.sync_frame = sync_frame

        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._scroll_x = 0  # Track scroll position
        self._scroll_y = 0  # Track scroll position

        self.SCALING_FACTOR = self.get_scaling_factor()
        print(f"Windows scaling factor: {self.SCALING_FACTOR}")

        # Create a canvas to hold the image
        self.canvas = ctk.CTkCanvas(self, highlightthickness=0, bd=0)
        self.canvas.pack(expand=True, fill="both")

        # Create a frame inside the canvas to hold the image
        self.image_container = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.image_container, anchor="nw")

        # Prevent automatic resizing based on content
        self.pack_propagate(False)

        # Image label
        self.image_label = ctk.CTkLabel(self.image_container, text="")
        self.image_label.pack(expand=True, fill="both")
        self.image_label.configure(width=400, height=300)

        # Configure canvas scrolling behavior
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.canvas.bind("<MouseWheel>", self.on_mouse_scroll)  # Windows/macOS
        self.canvas.bind("<Button-4>", self.on_mouse_scroll_linux)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_scroll_linux)  # Linux scroll down

        # Bind to configure event to update the scrollregion when the frame size changes
        self.bind("<Configure>", self.on_configure)
        self.image_container.bind("<Configure>", self.on_image_configure)

    def on_configure(self, event):
        # Update the scrollable area when the frame is resized
        self.update_scroll_region()

    def on_image_configure(self, event):
        # Update the scrollable area when the image container changes
        self.update_scroll_region()

    def update_scroll_region(self):
        # Update the canvas's scroll region to encompass the inner frame
        if hasattr(self.image_label, 'image') and self.image_label.image is not None:
            content_width = self.image_label.winfo_reqwidth()
            content_height = self.image_label.winfo_reqheight()
            frame_width = self.winfo_width()
            frame_height = self.winfo_height()

            # Set the scroll region to the size of the image
            self.canvas.configure(
                scrollregion=(0, 0, max(content_width, frame_width), max(content_height, frame_height)))

            # Ensure the image container is sized appropriately
            self.image_container.configure(width=content_width, height=content_height)

    def on_mouse_scroll(self, event):
        if event.delta > 0:
            self.app.zoom_in()
        elif event.delta < 0:
            self.app.zoom_out()

    def on_mouse_scroll_linux(self, event):
        if self.app:
            if event.num == 4:
                self.app.zoom_in()
            elif event.num == 5:
                self.app.zoom_out()

    # Get the Windows scaling factor
    def get_scaling_factor(self):
        if sys.platform == "win32":
            # Works only on Windows
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            # Get the DPI for the primary monitor
            hdc = user32.GetDC(None)
            dpi_x = gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX = 88
            user32.ReleaseDC(None, hdc)
            return dpi_x / 96
        else:
            # Default for other platforms
            return 1.0

    def on_press(self, event):
        self._dragging = True
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self.configure(cursor="fleur")

        # Save current scroll position
        self._scroll_x = self.canvas.canvasx(0)
        self._scroll_y = self.canvas.canvasy(0)

    def on_drag(self, event):
        if not self._dragging:
            return

        # Calculate movement delta
        delta_x = event.x - self._drag_start_x
        delta_y = event.y - self._drag_start_y

        # Calculate new scroll position
        new_x = self._scroll_x - delta_x
        new_y = self._scroll_y - delta_y

        # Apply boundaries
        content_width = self.image_label.winfo_reqwidth()
        content_height = self.image_label.winfo_reqheight()
        frame_width = self.winfo_width()
        frame_height = self.winfo_height()

        max_x = max(0, content_width - frame_width)
        max_y = max(0, content_height - frame_height)

        new_x = max(0, min(new_x, max_x))
        new_y = max(0, min(new_y, max_y))

        # Move the canvas view
        self.canvas.xview_moveto(new_x / content_width if content_width > 0 else 0)
        self.canvas.yview_moveto(new_y / content_height if content_height > 0 else 0)

        # Sync with other frame if needed
        if self.sync_frame:
            x_fraction = self.canvas.xview()
            y_fraction = self.canvas.yview()
            self.sync_frame.set_view_position(x_fraction, y_fraction)

    def set_view_position(self, x_fraction, y_fraction):
        # Set the view position based on fractions (0-1)
        self.canvas.xview_moveto(x_fraction[0])
        self.canvas.yview_moveto(y_fraction[0])

    def on_release(self, event):
        self._dragging = False
        self.configure(cursor="")

    def set_image(self, image):
        if hasattr(self.image_label, 'image') and self.image_label.image is not None:
            self.image_label.configure(image=image)
        else:
            self.image_label.configure(image=image)

        self.image_label.image = image  # Prevent GC

        # Update the scroll region after setting a new image
        # Use after() to ensure the widget has been updated
        self.after(100, self.update_scroll_region)


class HelpDialog(ctk.CTkToplevel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title("Help")
        self.geometry("500x600")
        self.withdraw()  # Hide window initially for positioning

        # Main frame with scrolling
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Help text
        help_text = ctk.CTkTextbox(main_frame, width=480, height=550)
        help_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Set the help text content
        help_text.insert("1.0", """
        Image Converter Help

        This application allows you to convert JPG, JPEG, and PNG images to WEBP format with quality control.

        Basic Controls:
        • 📂Load Image - Open an image file from your computer
        • 💾Save Image - Save the converted image to your computer
        • ➕/➖ - Zoom in and out of the images using keyboard shortcuts (Ctrl + '+' to zoom in, Ctrl + '-' to zoom out)
        • Quality Slider - Adjust the compression quality (higher values = better quality but larger file size)

        Advanced Options:
        • Method - Select the conversion algorithm (0-6). Higher values provide better quality and smaller file size but take longer to process.
        • Lossless - Enable for lossless compression (no quality loss, but larger file size)

        Image Navigation:
        • Mouse Wheel: Scroll up or down to zoom in or out.
            - For Windows/macOS: Use the mouse wheel to zoom in and out.
            - For Linux: Use the mouse buttons (Button-4 for scroll up, Button-5 for scroll down) to zoom.
        • Zoom Controls: You can use the zoom controls to get a closer look at details.

        Keyboard Shortcuts:
        • Ctrl + O: Load an image
        • Ctrl + S: Save the image
        • Ctrl + '+': Zoom in
        • Ctrl + '-': Zoom out
        • Ctrl + H: Show this help dialog
        • Ctrl + Q: Quit the application

        About:
        Image Converter v1.01
        Developed by Vitaliy Osidach © 2025

        GitHub Repository: https://github.com/ozinka/image_converter2webp

        Built with:
        • Python 3.13
        • CustomTkinter
        • Pillow (Python Imaging Library)
        • Development assistance: ChatGPT, Claude

        License:
        MIT License
        Copyright (c) 2025 Vitaliy Osidach

        Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:

        The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.

        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.
        """)

        help_text.configure(state="disabled")  # Make read-only

        # OK button
        ok_button = ctk.CTkButton(main_frame, text="OK", command=self.destroy)
        ok_button.pack(pady=10)

        # Position the dialog relative to parent
        self.update_idletasks()  # Update to get accurate dimensions
        self.center_on_parent(parent)
        self.deiconify()  # Show window after positioning

    def center_on_parent(self, parent):
        """Center the dialog on parent window"""
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        # Calculate position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        # Set position
        self.geometry(f"+{x}+{y}")


class ImageConverter(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.image_path = None
        self.scale_index = SCALE_FACTORS.index(100)
        self.original_image = None
        self.converted_image = None
        self.init_ui()
        self.load_image('media/app.webp')

    def init_ui(self):
        self.title(APP_CAPTION)
        self.geometry("900x600")
        self.minsize(800, 600)
        self.center_on_screen()

        # Keyboard shortcuts
        self.bind("<Control-o>", lambda e: self.load_image())
        self.bind("<Control-s>", lambda e: self.save_image())
        self.bind("<Control-plus>", lambda e: self.zoom_in())
        self.bind("<Control-minus>", lambda e: self.zoom_out())
        self.bind("<Control-h>", lambda e: self.show_help())
        self.bind("<Control-q>", lambda e: self.quit())

        # Main layout frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Images area frame
        images_frame = ctk.CTkFrame(main_frame)
        images_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Horizontal layout for images and zoom controls
        images_frame.grid_columnconfigure(0, weight=1)  # Original image
        images_frame.grid_columnconfigure(1, weight=0)  # Zoom controls
        images_frame.grid_columnconfigure(2, weight=1)  # Converted image
        images_frame.grid_rowconfigure(0, weight=1)  # Images

        # Create simple image frames for original and converted images
        self.original_frame = ImageFrame(images_frame, app=self)
        self.original_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.converted_frame = ImageFrame(images_frame, sync_frame=self.original_frame, app=self)
        self.original_frame.sync_frame = self.converted_frame
        self.converted_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # Zoom controls frame - centered vertically to the images
        zoom_frame = ctk.CTkFrame(images_frame, bg_color="transparent", fg_color="transparent")
        zoom_frame.grid(row=0, column=1, sticky="ns", padx=5, pady=5)

        # Make zoom frame use full height and create a container for buttons
        zoom_frame.grid_rowconfigure(0, weight=1)  # Top spacer
        zoom_frame.grid_rowconfigure(1, weight=0)  # Zoom controls
        zoom_frame.grid_rowconfigure(2, weight=1)  # Bottom spacer
        zoom_frame.grid_rowconfigure(3, weight=0)  # Help button

        # Container for zoom controls - centered vertically
        zoom_controls = ctk.CTkFrame(zoom_frame, fg_color="transparent")
        zoom_controls.grid(row=1, column=0)

        # Zoom controls
        self.zoom_in_button = ctk.CTkButton(zoom_controls, text="➕", width=30, command=self.zoom_in)
        self.zoom_in_button.pack(pady=5)

        self.zoom_label = ctk.CTkLabel(zoom_controls, text="100%")
        self.zoom_label.pack(pady=5)

        self.zoom_out_button = ctk.CTkButton(zoom_controls, text="➖", width=30, command=self.zoom_out)
        self.zoom_out_button.pack(pady=5)

        # Help button - aligned to bottom
        self.help_button = ctk.CTkButton(zoom_frame, text="❓", width=30, command=self.show_help)
        self.help_button.grid(row=3, column=0, sticky="s", pady=10)

        # Size labels
        self.original_size_label = ctk.CTkLabel(images_frame, text="Original Size: -")
        self.original_size_label.grid(row=1, column=0, sticky="w", padx=5)

        self.converted_size_label = ctk.CTkLabel(images_frame, text="Converted Size: -")
        self.converted_size_label.grid(row=1, column=2, sticky="w", padx=5)

        # Options frame for Method and Lossless (aligned right)
        options_frame = ctk.CTkFrame(images_frame, fg_color="transparent")
        options_frame.grid(row=1, column=2, sticky="e", padx=(0, 5))

        # Method dropdown
        self.method_combo = ctk.CTkComboBox(options_frame, values=[str(i) for i in range(7)], width=60)
        self.method_combo.set("6")
        self.method_combo.pack(side="right", padx=0)
        self.method_combo.configure(command=lambda _: self.update_preview())

        method_label = ctk.CTkLabel(options_frame, text="Method:")
        method_label.pack(side="right", padx=(0, 5))

        # Lossless checkbox
        self.lossless_var = tk.BooleanVar(value=False)
        self.lossless_checkbox = ctk.CTkCheckBox(options_frame, text="Lossless", variable=self.lossless_var,
                                                 command=self.update_preview)
        self.lossless_checkbox.pack(side="right", padx=(0, 0))

        # Quality slider frame
        slider_frame = ctk.CTkFrame(main_frame, bg_color="transparent", fg_color="transparent")
        slider_frame.pack(fill="x", padx=0, pady=5)

        # Quality slider
        quality_label = ctk.CTkLabel(slider_frame, text="Quality:")
        quality_label.pack(side="left", padx=5)

        self.quality_slider = ctk.CTkSlider(slider_frame, from_=10, to=100, number_of_steps=90)
        self.quality_slider.set(80)
        self.quality_slider.pack(side="left", expand=True, fill="x", padx=5)
        self.quality_slider.configure(command=lambda x: self.update_preview())

        self.compression_label = ctk.CTkLabel(slider_frame, text="80%")
        self.compression_label.pack(side="left", padx=5)

        # Buttons frame
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=0, pady=0)

        # Load and Save buttons
        self.load_button = ctk.CTkButton(buttons_frame, text="📂 Load Image", height=45,
                                         font=ctk.CTkFont(size=12), command=self.load_image)
        self.load_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

        self.save_button = ctk.CTkButton(buttons_frame, text="💾 Save Image", height=45,
                                         font=ctk.CTkFont(size=12), command=self.save_image)
        self.save_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

    def center_on_screen(self):
        """Centers the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def zoom_in(self):
        if self.scale_index < len(SCALE_FACTORS) - 1 and self.image_path:
            self.scale_index += 1
            self.update_zoom()

    def zoom_out(self):
        if self.scale_index > 0 and self.image_path:
            self.scale_index -= 1
            self.update_zoom()

    def resize_image(self, image, scale_factor):
        width = int(image.width * scale_factor / 100)
        height = int(image.height * scale_factor / 100)
        return image.resize((width, height), Image.BICUBIC), width, height

    def update_zoom(self):
        if self.image_path:
            scale_factor = SCALE_FACTORS[self.scale_index]
            self.zoom_label.configure(text=f"{scale_factor}%")

            # Load original image
            img = Image.open(self.image_path)
            img_resized, width, height = self.resize_image(img, scale_factor)

            # Convert to PhotoImage
            photo = ctk.CTkImage(light_image=img_resized, dark_image=img_resized, size=(width, height))

            # Update original image frame
            self.original_image = photo  # Keep reference
            self.original_frame.set_image(photo)

            # Update converted image
            self.convert_image()

    def update_preview(self):
        quality_value = int(self.quality_slider.get())
        self.compression_label.configure(text=f"{quality_value}%")
        self.convert_image()

    def load_image(self, file_path=None):
        if not file_path:
            file_path = filedialog.askopenfilename(
                title="Open Image",
                filetypes=[("Images", "*.png *.jpg *.jpeg")]
            )

        if file_path:
            try:
                self.image_path = file_path
                self.update_zoom()
                file_size = os.path.getsize(file_path) / 1024  # KB
                self.original_size_label.configure(text=f'Original Size: {file_size:.2f} KB')
                self.title(f"{APP_CAPTION} - {os.path.basename(self.image_path)}")
            except Exception as e:
                self.show_error(f"Error loading image: {e}")

    def save_image(self):
        if not self.image_path:
            return

        file_name = os.path.splitext(self.image_path)[0]
        save_path = filedialog.asksaveasfilename(
            title='Save Image',
            initialfile=os.path.basename(file_name),
            defaultextension=".webp",
            filetypes=[("WEBP Files", "*.webp")]
        )

        if save_path:
            img = Image.open(self.image_path)

            quality = int(self.quality_slider.get())
            method = int(self.method_combo.get())
            lossless = self.lossless_var.get()

            img.save(save_path, "WEBP",
                     quality=quality,
                     lossless=lossless,
                     method=method,
                     icc_profile=None)

    def convert_image(self):
        # Start conversion in a separate thread
        threading.Thread(target=self._convert_image_thread, daemon=True).start()

    @timer_decorator
    def _convert_image_thread(self):
        if not self.image_path:
            return

        # Convert image in memory
        img = Image.open(self.image_path)
        quality = int(self.quality_slider.get())
        method = int(self.method_combo.get())
        lossless = self.lossless_var.get()

        # Save to BytesIO instead of file
        buffer = io.BytesIO()
        img.save(buffer, "WEBP", quality=quality, lossless=lossless, method=method, icc_profile=None)

        # Get byte size
        estimated_size = len(buffer.getvalue()) / 1024  # KB
        self.converted_size_label.configure(text=f'Estimated Size: {estimated_size:.2f} KB')

        # Reset buffer position
        buffer.seek(0)

        # Load the converted image
        webp_img = Image.open(buffer)

        # Load the converted image
        scale_factor = SCALE_FACTORS[self.scale_index]

        webp_resized, width, height = self.resize_image(webp_img, scale_factor)

        # Convert to PhotoImage
        photo = ctk.CTkImage(light_image=webp_resized, dark_image=webp_resized, size=(width, height))

        # Update converted image frame
        self.converted_image = photo  # Keep reference
        self.after(0, lambda: self.converted_frame.set_image(photo))
        # self.converted_frame.set_image(photo)

    def show_help(self):
        help_dialog = HelpDialog(self)
        help_dialog.grab_set()  # Make dialog modal


if __name__ == "__main__":
    app = ImageConverter()
    app.mainloop()
