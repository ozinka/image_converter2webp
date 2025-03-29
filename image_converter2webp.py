import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QSlider, QHBoxLayout, QGridLayout, QMessageBox
)
from PyQt6.QtGui import QPixmap, QMouseEvent
from PyQt6.QtCore import Qt, QPoint
from PIL import Image
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtGui import QIcon, QFont

SCALE_FACTORS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]


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
        self.setWindowTitle("JPG/PNG to WEBP Converter")
        self.setGeometry(100, 100, 900, 600)
        self.center_on_screen()

        layout = QVBoxLayout()

        # Create a larger font
        button_font = QFont()
        button_font.setPointSize(12)  # Increase this number for bigger text

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
        self.image_layout.addWidget(self.original_scroll, 0, 0)

        self.converted_label = DraggableLabel(self.converted_scroll, self.original_scroll)
        self.converted_scroll.setWidget(self.converted_label)
        self.converted_scroll.setWidgetResizable(True)
        self.image_layout.addWidget(self.converted_scroll, 0, 2)

        self.zoom_layout = QVBoxLayout()
        self.zoom_in_button = QPushButton("➕")
        self.zoom_out_button = QPushButton("➖")
        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add spacer at the top of zoom layout to push controls to middle
        self.zoom_layout.addStretch()

        # Add zoom controls grouped together
        self.zoom_layout.addWidget(self.zoom_in_button)
        self.zoom_layout.addWidget(self.zoom_label)
        self.zoom_layout.addWidget(self.zoom_out_button)

        # Add spacer at the bottom of zoom layout to center the controls
        self.zoom_layout.addStretch()

        self.image_layout.addLayout(self.zoom_layout, 0, 1)

        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)

        layout.addLayout(self.image_layout)
        self.original_size_label = QLabel("Original Size: -")
        self.converted_size_label = QLabel("Converted Size: -")
        self.image_layout.addWidget(self.original_size_label, 1, 0)
        self.image_layout.addWidget(self.converted_size_label, 1, 2)

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
        if self.scale_index < len(SCALE_FACTORS) - 1:
            self.scale_index += 1
            self.update_zoom()

    def zoom_out(self):
        if self.scale_index > 0:
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
            self.converted_label.setPixmap(scaled_pixmap)
            self.converted_label.adjustSize()
            self.zoom_label.setText(f"{scale_factor}%")
            # self.convert_image()

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

    def save_image(self):
        if self.image_path:
            save_path, _ = QFileDialog.getSaveFileName(self, 'Save Image', '', 'WEBP Files (*.webp)')
            if save_path:
                img = Image.open(self.image_path)
                img.save(save_path, 'WEBP', quality=self.quality_slider.value())
                print(f'Saved to: {save_path}')

    def convert_image(self):
        if self.image_path:
            img = Image.open(self.image_path)
            webp_path = "converted.webp"
            img.save(webp_path, "WEBP", quality=self.quality_slider.value())
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
    app_icon = QIcon("media/favicon.ico")  # Assumes the file is in the same directory as your script
    app.setWindowIcon(app_icon)
    converter = ImageConverter()
    converter.show()
    sys.exit(app.exec())
