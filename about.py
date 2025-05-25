from version import __version__

about_text = f"""
            <h2>Image Converter Help</h2>
            <p>This application allows you to convert JPG/JPEG/PNG/BMP images to WEBP format with quality control.</p>

            <h3>Basic Controls</h3>
            <ul>
                <li><strong>📂Load Image</strong> - Open an image file from your computer</li>
                <li><strong>💾Save Image</strong> - Save the converted image to your computer</li>
                <li><strong>➕/➖</strong> - Zoom in and out of the images</li>
                <li><strong>Quality Slider</strong> - Adjust the compression quality (higher values = better quality but larger file size)</li>
                <li><strong>Drag and Drop</strong> - You can also drag image files directly onto the main window to open them</li>
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
            <p><strong>Image Converter {__version__}</strong></p>
            <p>Developed by Vitaliy Osidach &copy; 2025</p>
            <p>GitHub Repository: <a href="https://github.com/ozinka/image_converter2webp">ozinka/image_converter2webp</a></p>
            <p>Built with:</p>
            <ul>
                <li>Python 3.13</li>
                <li>PyQt6</li>
                <li>OpenCV2 (Python Imaging Library)</li>
                <li>Builders: PyInstaller, Nuitka</li>
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
        """
