import sys
import os
import io
from time import perf_counter

from PIL import Image

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QSlider, QHBoxLayout,
                             QGridLayout, QCheckBox, QComboBox, QDialogButtonBox, QTextBrowser, QDialog)
from PyQt6.QtGui import QPixmap, QMouseEvent
from PyQt6.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtGui import QIcon, QFont

from about import about_text

SCALE_FACTORS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]

APP_CAPTION = "JPG/PNG/BMP to WEBP Converter"


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


class ImageConversionWorker(QObject):
    finished = pyqtSignal(bytes, float)
    started = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, image_path, quality, method, lossless):
        super().__init__()
        self.image_path = image_path
        self.quality = quality
        self.method = method  # Not used with Pillow, can be removed or repurposed
        self.lossless = lossless

    def run(self):
        self.started.emit()
        try:
            # Read image using Pillow
            img = Image.open(self.image_path).convert("RGBA")

            # Prepare WebP parameters
            webp_params = {
                'format': 'WEBP',
                'quality': self.quality,
            }
            if self.lossless:
                webp_params['lossless'] = True

            # Convert to bytes using Pillow
            buffer = io.BytesIO()
            img.save(buffer, **webp_params)

            webp_data = buffer.getvalue()
            estimated_size = len(webp_data) / 1024  # in KB
            self.finished.emit(webp_data, estimated_size)

        except Exception as e:
            self.error.emit(f"Error converting image: {str(e)}")


class ImageConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.image_path = None
        self.scale_index = SCALE_FACTORS.index(100)
        self.setAcceptDrops(True)
        self.center_on_screen()
        self._conversion_thread = None
        self._conversion_worker = None

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self.convert_image)

        self._last_conversion_params = None
        self._last_conversion_time_ms = 150  # Default debounce time in milliseconds, responsible for  UI convertion responsiveness

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
        self.load_button.clicked.connect(lambda: self.load_image(None))
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

        self.fps_overlay_label = QLabel("0 fps", self.converted_scroll)
        self.fps_overlay_label.setStyleSheet(
            "QLabel { background-color: rgba(0, 0, 0, 128); color: white; padding: 2px; }")
        self.fps_overlay_label.move(5, 5)
        self.fps_overlay_label.raise_()
        self.fps_overlay_label.show()

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

        # Add original size label and FPS label
        self.original_size_label = QLabel("Original Size: -")
        self.image_size_label = QLabel("Image size: -")
        original_info_layout = QHBoxLayout()
        original_info_layout.addWidget(self.original_size_label)
        original_info_layout.addStretch()
        original_info_layout.addWidget(self.image_size_label)

        self.image_layout.addLayout(original_info_layout, 2, 0)

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
        help_text.setHtml(about_text)

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
            self.original_label.setPixmap(scaled_pixmap)
            self.converted_label.setPixmap(scaled_pixmap)
            self.zoom_label.setText(f"{scale_factor}%")
            self.convert_image()

    def update_preview(self):
        self.compression_label.setText(f"{self.quality_slider.value()}%")

        # Calculate dynamic delay based on last conversion time
        delay = max(100, min(300, self._last_conversion_time_ms))
        self._debounce_timer.start(delay)

    def load_image(self, file_path=None):
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "",
                                                       "Images (*.png *.jpg *.jpeg *.bmp *.webp)")

        if file_path:
            self.image_path = file_path
            self.update_zoom()
            file_size = os.path.getsize(file_path) / 1024  # KB
            self.original_size_label.setText(f'Original Size: {file_size:.2f} KB')
            self.setWindowTitle("JPG/PNG/BMP to WEBP Converter - " + os.path.basename(self.image_path))

    def save_image(self):
        file_name = os.path.splitext(self.image_path)[0]
        if self.image_path:
            save_path, _ = QFileDialog.getSaveFileName(self, 'Save Image', file_name, 'WEBP Files (*.webp)')
            if save_path:
                try:
                    img = Image.open(self.image_path).convert("RGBA")

                    # Get settings
                    quality = self.quality_slider.value()
                    lossless = self.lossless_checkbox.isChecked()

                    # Prepare parameters for saving
                    save_params = {'format': 'WEBP'}
                    if lossless:
                        save_params['lossless'] = True
                    else:
                        save_params['quality'] = quality

                    # Save image using Pillow
                    img.save(save_path, **save_params)

                except Exception as e:
                    print(f"Error saving image: {e}")  # Replace with proper error dialog in UI

    def convert_image(self):
        if not self.image_path:
            return

        self._conversion_start_time = perf_counter()

        quality = self.quality_slider.value()
        method = int(self.method_combo.currentText())
        lossless = self.lossless_checkbox.isChecked()
        file_name = self.image_path

        params = (quality, method, lossless, file_name)
        if params == self._last_conversion_params:
            return  # No change, skip
        self._last_conversion_params = params

        # Optional: attempt to stop any existing thread cleanly without accessing deleted objects
        try:
            if self._conversion_thread and self._conversion_thread.isRunning():
                self._conversion_thread.quit()
                self._conversion_thread.wait()
        except RuntimeError:
            # The thread was already deleted; safely ignore
            pass

        quality = self.quality_slider.value()
        method = int(self.method_combo.currentText())
        lossless = self.lossless_checkbox.isChecked()

        # Create new thread and worker each time
        thread = QThread(self)
        worker = ImageConversionWorker(self.image_path, quality, method, lossless)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self.on_conversion_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        # Save references only while thread is alive
        self._conversion_thread = thread
        self._conversion_worker = worker

        thread.start()

    def on_conversion_finished(self, data, estimated_size):
        pixmap = QPixmap()
        pixmap.loadFromData(data, "WEBP")

        # Show FPS
        duration = (perf_counter() - self._conversion_start_time) * 1000  # ms
        self._last_conversion_time_ms = int(duration)

        if duration > 0:
            fps = 1000.0 / duration
            self.fps_overlay_label.setText(f"{fps:.1f} pfs")
            self.fps_overlay_label.adjustSize()
        else:
            self.fps_overlay_label.setText("0 pfs")
            self.fps_overlay_label.adjustSize()

        # Resize converted image
        scale_factor = SCALE_FACTORS[self.scale_index]
        scaled_pixmap = pixmap.scaled(pixmap.width() * scale_factor // 100,
                                      pixmap.height() * scale_factor // 100,
                                      Qt.AspectRatioMode.KeepAspectRatio)
        self.converted_label.setPixmap(scaled_pixmap)
        self.converted_label.adjustSize()
        self.converted_size_label.setText(f'Estimated Size: {estimated_size:.2f} KB')

        # Show actual image size under original image
        self.image_size_label.setText(f"Image size: {pixmap.width()}x{pixmap.height()} px")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.load_image(file_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon_path = resource_path('media/favicon.ico')
    app.setWindowIcon(QIcon(icon_path))
    converter = ImageConverter()
    converter.show()
    sys.exit(app.exec())
