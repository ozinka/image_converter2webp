import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QSlider, QHBoxLayout, QGridLayout,
    QMessageBox, QCheckBox, QComboBox, QDialogButtonBox, QTextBrowser, QDialog
)
from PyQt6.QtGui import QPixmap, QMouseEvent, QPalette, QColor
from PyQt6.QtCore import Qt, QPoint, QSettings
from PIL import Image
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtGui import QIcon, QFont

SCALE_FACTORS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]

APP_CAPTION = "JPG/PNG to WEBP Converter"


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in_MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class DraggableLabel(QLabel):
    def __init__(self, scroll_area, sync_scroll_area):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._dragging = False
        self._startPos = QPoint()
        self.scroll_area = scroll_area
        self.sync_scroll_area = sync_scroll_area
        self._h_scrollbar = self.scroll_area.horizontalScrollBar()
        self._v_scrollbar = self.scroll_area.verticalScrollBar()
        self._sync_h_scrollbar = self.sync_scroll_area.horizontalScrollBar()
        self._sync_v_scrollbar = self.sync_scroll_area.verticalScrollBar()

        self._h_scrollbar.valueChanged.connect(self.sync_scroll)
        self._v_scrollbar.valueChanged.connect(self.sync_scroll)

    def sync_scroll(self):
        self._sync_h_scrollbar.setValue(self._h_scrollbar.value())
        self._sync_v_scrollbar.setValue(self._v_scrollbar.value())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._startPos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            delta = event.pos() - self._startPos
            self._h_scrollbar.setValue(self._h_scrollbar.value() - delta.x())
            self._v_scrollbar.setValue(self._v_scrollbar.value() - delta.y())
            self.sync_scroll()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)


class ImageConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.image_path = None
        self.scale_index = SCALE_FACTORS.index(100)


    def initUI(self):
        self.setWindowTitle(APP_CAPTION)
        self.setGeometry(100, 100, 900, 600)
        self.setMinimumWidth(800)
        self.center_on_screen()

        layout = QVBoxLayout()

        # Create a larger font
        button_font = QFont()
        button_font.setPointSize(12)

        self.load_button = QPushButton("📂Load Image")
        self.load_button.setFont(button_font)
        self.load_button.setFixedHeight(45)
        self.load_button.clicked.connect(self.load_image)
        self.save_button = QPushButton("💾Save Image")
        self.save_button.setFixedHeight(45)
        self.save_button.setFont(button_font)
        self.save_button.clicked.connect(self.save_image)

        self.image_layout = QGridLayout()
        self.original_scroll = QScrollArea()
        self.converted_scroll = QScrollArea()

        self.original_label = DraggableLabel(self.original_scroll, self.converted_scroll)
        self.original_scroll.setWidget(self.original_label)
        self.original_scroll.setWidgetResizable(True)
        self.image_layout.addWidget(self.original_scroll, 1, 0)  # Row 1

        self.converted_label = DraggableLabel(self.converted_scroll, self.original_scroll)
        self.converted_scroll.setWidget(self.converted_label)
        self.converted_scroll.setWidgetResizable(True)
        self.image_layout.addWidget(self.converted_scroll, 1, 2)  # Row 1

        self.zoom_layout = QVBoxLayout()
        self.zoom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_in_button = QPushButton("➕")
        self.zoom_out_button = QPushButton("➖")
        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help_button = QPushButton("❓")

        self.zoom_in_button.setFixedWidth(30)
        self.zoom_out_button.setFixedWidth(30)
        self.zoom_label.setFixedWidth(30)
        self.help_button.setFixedWidth(30)
        self.help_button.setFixedHeight(30)

        self.zoom_layout.addStretch()
        self.zoom_layout.addWidget(self.zoom_in_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self.zoom_layout.addWidget(self.zoom_label)
        self.zoom_layout.addWidget(self.zoom_out_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self.zoom_layout.addStretch()
        self.zoom_layout.addWidget(self.help_button, 0, Qt.AlignmentFlag.AlignHCenter)

        self.image_layout.addLayout(self.zoom_layout, 1, 1)  # Row 1

        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.help_button.clicked.connect(self.show_help)

        # Add original size label
        self.original_size_label = QLabel("Original Size: -")
        self.image_layout.addWidget(self.original_size_label, 2, 0)

        # Add converted size label
        self.converted_size_label = QLabel("Converted Size: -")
        self.image_layout.addWidget(self.converted_size_label, 2, 2)

        # === Create a horizontal layout for Method and Lossless widgets (aligned right) ===
        options_layout = QHBoxLayout()
        options_layout.addStretch()  # Push widgets to the right

        # Method dropdown
        options_layout.addWidget(QLabel("Method:"))
        self.method_combo = QComboBox()
        for i in range(7):  # 0 through 6
            self.method_combo.addItem(str(i))
        self.method_combo.setCurrentIndex(6)
        self.method_combo.currentIndexChanged.connect(self.update_preview)
        options_layout.addWidget(self.method_combo)

        # Add spacing
        options_layout.addSpacing(10)

        # Lossless checkbox
        self.lossless_checkbox = QCheckBox("Lossless")
        self.lossless_checkbox.setChecked(False)
        self.lossless_checkbox.stateChanged.connect(self.update_preview)
        options_layout.addWidget(self.lossless_checkbox)

        # Add the options layout BELOW the converted image, aligned right (row 2, column 2)
        self.image_layout.addLayout(options_layout, 2, 2)

        # Add the image layout to the main layout
        layout.addLayout(self.image_layout)

        # Create and add slider layout
        slider_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setMinimum(10)
        self.quality_slider.setMaximum(100)
        self.quality_slider.setValue(80)
        self.quality_slider.valueChanged.connect(self.update_preview)
        slider_layout.addWidget(QLabel("Quality:"))
        slider_layout.addWidget(self.quality_slider)

        self.compression_label = QLabel("80%")
        slider_layout.addWidget(self.compression_label)
        layout.addLayout(slider_layout)

        # Create a horizontal layout for the buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.load_button)
        buttons_layout.addWidget(self.save_button)

        # Add the horizontal button layout to the main layout
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def show_help(self):
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setMinimumWidth(500)
        help_dialog.setMinimumHeight(400)

        layout = QVBoxLayout()

        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        help_text.setHtml("""
        <h2>Image Converter Help</h2>
        <p>This application allows you to convert JPG, JPEG, and PNG images to WEBP format with quality control.</p>

        <h3>Basic Controls</h3>
        <ul>
            <li><strong>📂Load Image</strong> - Open an image file from your computer</li>
            <li><strong>💾Save Image</strong> - Save the converted image to your computer</li>
            <li><strong>➕/➖</strong> - Zoom in and out of the images</li>
            <li><strong>Quality Slider</strong> - Adjust the compression quality (higher values = better quality but larger file size)</li>
        </ul>

        <h3>Advanced Options</h3>
        <ul>
            <li><strong>Method</strong> - Select the conversion algorithm (0-6). Higher values provide better quality and smaller file size but take longer to process.</li>
            <li><strong>Lossless</strong> - Enable for lossless compression (no quality loss, but larger file size)</li>
        </ul>

        <h3>Image Navigation</h3>
        <p>You can drag the images to pan around, and use the zoom controls to get a closer look at details.</p>

        <hr>
        <h3>About</h3>
        <p><strong>Image Converter v1.01</strong></p>
        <p>Developed by Vitaliy Osidach &copy; 2025</p>
        <p>GitHub Repository: <a href="https://github.com/ozinka/image_converter2webp">ozinka/image_converter2webp</a></p>
        <p>Built with:</p>
        <ul>
            <li>Python 3.13</li>
            <li>PyQt6</li>
            <li>Pillow (Python Imaging Library)</li>
            <li>Development assistance: ChatGPT, Claude</li>
        </ul>

        <h4>License</h4>
        <p>MIT License</p>
        <p>Copyright (c) 2025 Vitaliy Osidach</p>
        <p>Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:</p>

        <p>The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.</p>

        <p>THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.</p>
        """)

        layout.addWidget(help_text)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(help_dialog.accept)
        layout.addWidget(button_box)

        help_dialog.setLayout(layout)
        help_dialog.exec()

    def center_on_screen(self):
        """Centers the window on the screen."""
        # Get the screen geometry
        screen_geometry = QApplication.primaryScreen().availableGeometry()

        # Calculate the center position
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2

        # Move the window to the center
        self.move(x, y)

    def zoom_in(self):
        if self.scale_index < len(SCALE_FACTORS) - 1 and self.image_path:
            self.scale_index += 1
            self.update_zoom()

    def zoom_out(self):
        if self.scale_index > 0 and self.image_path:
            self.scale_index -= 1
            self.update_zoom()

    def update_zoom(self):
        if self.image_path:
            pixmap = QPixmap(self.image_path)
            scale_factor = SCALE_FACTORS[self.scale_index]
            scaled_pixmap = pixmap.scaled(pixmap.width() * scale_factor // 100,
                                          pixmap.height() * scale_factor // 100,
                                          Qt.AspectRatioMode.KeepAspectRatio)
            # Qt.TransformationMode.SmoothTransformation)
            self.original_label.setPixmap(scaled_pixmap)
            self.original_label.adjustSize()
            # self.converted_label.setPixmap(scaled_pixmap)
            # self.converted_label.adjustSize()
            self.zoom_label.setText(f"{scale_factor}%")
            self.convert_image()

    def update_preview(self):
        self.compression_label.setText(f"{self.quality_slider.value()}%")
        self.convert_image()

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            self.update_zoom()
            file_size = os.path.getsize(file_path) / 1024  # KB
            self.original_size_label.setText(f'Original Size: {file_size:.2f} KB')
            self.setWindowTitle("JPG/PNG to WEBP Converter - " + os.path.basename(self.image_path))

    def save_image(self):
        file_name = os.path.splitext(self.image_path)[0]
        if self.image_path:
            save_path, _ = QFileDialog.getSaveFileName(self, 'Save Image', file_name, 'WEBP Files (*.webp)')
            if save_path:
                img = Image.open(self.image_path)

                quality = self.quality_slider.value()
                method = int(self.method_combo.currentText())
                lossless = self.lossless_checkbox.isChecked()

                img.save(save_path, "WEBP",
                         quality=quality,
                         lossless=lossless,
                         method=method,
                         icc_profile=None)

    def convert_image(self):
        if self.image_path:
            img = Image.open(self.image_path)
            webp_path = "converted.webp"

            quality = self.quality_slider.value()
            method = int(self.method_combo.currentText())
            lossless = self.lossless_checkbox.isChecked()

            img.save(webp_path, "WEBP",
                     quality=quality,
                     lossless=lossless,
                     method=method,
                     icc_profile=None)

            pixmap = QPixmap(webp_path)
            scale_factor = SCALE_FACTORS[self.scale_index]
            scaled_pixmap = pixmap.scaled(pixmap.width() * scale_factor // 100,
                                          pixmap.height() * scale_factor // 100,
                                          Qt.AspectRatioMode.KeepAspectRatio)
            self.converted_label.setPixmap(scaled_pixmap)
            self.converted_label.adjustSize()

            estimated_size = os.path.getsize(webp_path) / 1024  # KB
            self.converted_size_label.setText(f'Estimated Size: {estimated_size:.2f} KB')

            os.remove(webp_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon_path = resource_path('media/favicon.ico')
    app.setWindowIcon(QIcon(icon_path))
    converter = ImageConverter()
    converter.show()
    sys.exit(app.exec())
