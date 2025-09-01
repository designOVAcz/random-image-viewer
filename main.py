import sys
import os
import random
import time
import subprocess
import gc
import struct
import numpy as np
try:
    import pyopencl as cl
    GPU_AVAILABLE = True
    print("GPU acceleration (OpenCL) available")
except ImportError:
    cl = None
    GPU_AVAILABLE = False
    print("GPU acceleration not available (install pyopencl for GPU support)")
try:
    import winreg  # For Windows registry access (dark mode detection)
    import ctypes
    import ctypes.wintypes  # For Windows API calls (dark mode title bar)
except ImportError:
    winreg = None  # Not on Windows
    ctypes = None
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QFileDialog, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QSplitter, QSpinBox, QCheckBox,
    QStatusBar, QToolBar, QToolButton, QSizePolicy, QSlider, QHBoxLayout,
    QStyle, QStyleOptionSlider, QGridLayout, QMenu, QColorDialog, QComboBox
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QIcon, QColorTransform, QMouseEvent, QImageReader, QTransform, QAction, QShortcut, QImage
from PySide6.QtCore import Qt, QTimer, QSize, QElapsedTimer, QRect

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}

def setup_image_allocation_limit():
    """Increase Qt's image allocation limit to handle large images"""
    # Set allocation limit to 1GB (1024 MB) instead of default 256 MB
    QImageReader.setAllocationLimit(1024)

def get_image_file_size(file_path):
    """Get file size in MB for display purposes"""
    try:
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return size_mb
    except OSError:
        return 0

def is_windows_dark_mode():
    """Detect if Windows is using dark mode"""
    if not winreg or os.name != 'nt':
        return True  # Default to dark mode on non-Windows or if winreg unavailable
    
    try:
        # Check Windows theme setting
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(registry_key, "AppsUseLightTheme")
        winreg.CloseKey(registry_key)
        return value == 0  # 0 = dark mode, 1 = light mode
    except:
        return True  # Default to dark mode if detection fails

def enable_windows_dark_title_bar(window):
    """Enable dark mode title bar on Windows 10/11"""
    if not ctypes or os.name != 'nt':
        return  # Not on Windows or ctypes unavailable
    
    try:
        # Get the window handle
        hwnd = int(window.winId())
        print(f"DEBUG: Window handle: {hwnd}")
        
        # Try the Windows 11 method first (DWMWA_USE_IMMERSIVE_DARK_MODE = 20)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)  # Enable dark mode
        
        # Try to load dwmapi.dll and call DwmSetWindowAttribute
        dwmapi = ctypes.windll.dwmapi
        result = dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
        print(f"DEBUG: Windows 11 dark mode result: {result}")
        
        # If that fails, try the Windows 10 method (DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19)
        if result != 0:
            DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
            result2 = dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
            print(f"DEBUG: Windows 10 dark mode result: {result2}")
        
        return result == 0  # Return success status
        
    except Exception as e:
        print(f"DEBUG: Exception in dark title bar: {e}")
        return False

def get_adaptive_stylesheet():
    """Get stylesheet based on OS theme"""
    if is_windows_dark_mode():
        return DARK_STYLESHEET
    else:
        return LIGHT_STYLESHEET

def smart_load_pixmap(file_path, max_dimension=2048):
    """Load pixmap with smart downscaling for better performance"""
    try:
        # Check file size first
        file_size_mb = get_image_file_size(file_path)
        
        # Use QImageReader for better control over loading
        reader = QImageReader(file_path)
        if not reader.canRead():
            return None, f"Cannot read image format"
        
        # Get original size without loading the full image
        original_size = reader.size()
        if not original_size.isValid():
            return None, f"Invalid image dimensions"
        
        # Calculate if we need to scale down for performance
        scale_factor = 1.0
        if original_size.width() > max_dimension or original_size.height() > max_dimension:
            scale_factor = max_dimension / max(original_size.width(), original_size.height())
            scaled_size = QSize(
                int(original_size.width() * scale_factor),
                int(original_size.height() * scale_factor)
            )
            reader.setScaledSize(scaled_size)
        
        # Load the image (potentially scaled)
        image = reader.read()
        if image.isNull():
            return None, f"Failed to load image"
        
        # Convert to pixmap
        pixmap = QPixmap.fromImage(image)
        
        # For very large files, warn but continue
        if file_size_mb > 100:
            print(f"Large image loaded with scaling ({file_size_mb:.1f} MB): {os.path.basename(file_path)}")
        
        return pixmap, None
        
    except Exception as e:
        error_msg = f"Error loading image: {str(e)}"
        print(f"Exception loading {os.path.basename(file_path)}: {error_msg}")
        return None, error_msg

def safe_load_pixmap(file_path):
    """Safely load a pixmap with error handling for large images"""
    # Use the smart loader for better performance
    return smart_load_pixmap(file_path)

def get_images_in_folder(folder):
    image_paths = []
    for root, _, files in os.walk(folder):
        # Sort files in each directory to ensure deterministic traversal order
        for f in sorted(files, key=lambda n: n.lower()):
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                image_paths.append(os.path.join(root, f))
    # Final global sort so overall list is alphabetical by full path
    image_paths.sort(key=lambda p: p.lower())
    return image_paths

def emoji_icon(emoji="🎲", size=128):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    f = QFont()
    f.setPointSize(int(size * 0.7))
    p.setFont(f)
    p.drawText(pix.rect(), Qt.AlignCenter, emoji)
    p.end()
    return QIcon(pix)

class ClickableSlider(QSlider):
    """A slider that allows clicking anywhere on the track to jump to that position"""
    
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Get the slider's style options
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            
            # Get the groove rect (the track area)
            groove_rect = self.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self
            )
            
            if self.orientation() == Qt.Horizontal:
                # Calculate the position as a percentage of the groove width
                click_pos = event.position().x() - groove_rect.x()
                groove_width = groove_rect.width()
                if groove_width > 0:
                    percentage = max(0.0, min(1.0, click_pos / groove_width))
                    # Calculate the new value based on the slider's range
                    value_range = self.maximum() - self.minimum()
                    new_value = self.minimum() + int(percentage * value_range)
                    self.setValue(new_value)
                    return
            else:  # Vertical orientation
                click_pos = event.position().y() - groove_rect.y()
                groove_height = groove_rect.height()
                if groove_height > 0:
                    # For vertical sliders, top = maximum, bottom = minimum
                    percentage = max(0.0, min(1.0, 1.0 - (click_pos / groove_height)))
                    value_range = self.maximum() - self.minimum()
                    new_value = self.minimum() + int(percentage * value_range)
                    self.setValue(new_value)
                    return
        
        # Fall back to default behavior for dragging
        super().mousePressEvent(event)

DARK_STYLESHEET = """
QWidget { background-color: #232629; color: #b7bcc1; font-size: 11px; }
QLabel, QCheckBox, QSpinBox, QListWidget, QToolButton { font-size: 11px; color: #b7bcc1; }
QStatusBar { font-size: 10px; color: #888; }
QSplitter::handle { background: #232629; border: none; height: 1px; }
QPushButton, QToolButton {
    background: transparent;
    color: #c7ccd1;
    border: none;
    border-radius: 4px;
    min-width: 24px;
    min-height: 24px;
    font-size: 13px;
    padding: 0 2px;
}
QPushButton:hover, QToolButton:hover { background: #2e3034; }
QPushButton:checked, QToolButton:checked { background: #424242; color: #fff; }
QListWidget::item:selected { background: #354e6e; color: #fff; }
QCheckBox:checked { color: #424242; }
QSlider::groove:horizontal {
    background: #35383b;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #b7bcc1;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -4px 0;
}
QSlider::handle:horizontal:hover {
    background: #424242;
}
QSpinBox {
    background: #35383b;
    border: 1px solid #4a4d50;
    border-radius: 3px;
    padding: 2px;
    selection-background-color: #424242;
}
QToolBar::separator {
    background: #35383b;
    width: 1px;
    margin: 0 4px;
}
QToolBar {
    border: none;
    background: #232629;
}
QMenu {
    background: #232629;
    border: 1px solid #35383b;
    color: #b7bcc1;
}
QMenu::item {
    padding: 4px 20px;
    background: transparent;
}
QMenu::item:selected {
    background: #424242;
    color: #fff;
}
QMenu::separator {
    height: 1px;
    background: #35383b;
    margin: 2px 0;
}
"""

LIGHT_STYLESHEET = """
QWidget { background-color: #ffffff; color: #333333; font-size: 11px; }
QLabel, QCheckBox, QSpinBox, QListWidget, QToolButton { font-size: 11px; color: #333333; }
QStatusBar { font-size: 10px; color: #666; }
QSplitter::handle { background: #e0e0e0; border: none; height: 1px; }
QPushButton, QToolButton {
    background: transparent;
    color: #333333;
    border: none;
    border-radius: 4px;
    min-width: 24px;
    min-height: 24px;
    font-size: 13px;
    padding: 0 2px;
}
QPushButton:hover, QToolButton:hover { background: #e6e6e6; }
QPushButton:checked, QToolButton:checked { background: #0078d4; color: #fff; }
QListWidget::item:selected { background: #0078d4; color: #fff; }
QCheckBox:checked { color: #0078d4; }
QSlider::groove:horizontal {
    background: #e0e0e0;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #666666;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -4px 0;
}
QSlider::handle:horizontal:hover {
    background: #0078d4;
}
QSpinBox {
    background: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 3px;
    padding: 2px;
    selection-background-color: #0078d4;
}
QToolBar::separator {
    background: #cccccc;
    width: 1px;
    margin: 0 4px;
}
QToolBar {
    border: none;
    background: #f5f5f5;
}
QMenu {
    background: #ffffff;
    border: 1px solid #cccccc;
    color: #333333;
}
QMenu::item {
    padding: 4px 20px;
    background: transparent;
}
QMenu::item:selected {
    background: #0078d4;
    color: #fff;
}
QMenu::separator {
    height: 1px;
    background: #cccccc;
    margin: 2px 0;
}
"""

class CircularCountdown(QWidget):
    def __init__(self, total_time=0, parent=None):
        super().__init__(parent)
        self.total_time = 0
        self.remaining_time = 0      # The actual time left
        self.displayed_time = 0      # The smooth UI value
        self.parent_viewer = None    # Reference to main viewer
        self.is_paused = False       # Pause state indicator
        self.setFixedSize(QSize(24, 24))
        self.setCursor(Qt.PointingHandCursor)  # Show it's clickable
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(16)  # ~60 FPS

        self._last_update = time.monotonic()

    def set_parent_viewer(self, viewer):
        self.parent_viewer = viewer

    def set_paused(self, paused):
        self.is_paused = paused
        self.update()  # Redraw with pause indicator

    def set_total_time(self, seconds):
        self.total_time = float(max(1, seconds))
        self.update()

    def set_remaining_time(self, seconds):
        self.remaining_time = float(max(0, min(self.total_time, seconds)))
        self.update()

    def _on_tick(self):
        # Interpolate displayed_time toward remaining_time
        alpha = 0.18  # Smoothing factor (smaller = smoother/slower)
        self.displayed_time += (self.remaining_time - self.displayed_time) * alpha
        if abs(self.displayed_time - self.remaining_time) < 0.01:
            self.displayed_time = self.remaining_time
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)
        # Draw subtle background ring
        painter.setPen(QPen(QColor("#3d3e40"), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(rect)
        # Draw smooth progress arc
        if self.total_time > 0 and self.displayed_time > 0:
            fraction = self.displayed_time / self.total_time
            angle = int(360 * 16 * fraction)
            # Use different color when paused
            color = "#ff8080" if self.is_paused else "#80b2ff"
            painter.setPen(QPen(QColor(color), 3))
            painter.drawArc(rect, 90 * 16, -angle)
            
        # Draw pause indicator when paused
        if self.is_paused and self.total_time > 0:
            painter.setPen(QPen(QColor("#ff8080"), 2))
            painter.setBrush(QColor("#ff8080"))
            # Draw two small vertical bars (pause symbol)
            center_x = rect.center().x()
            center_y = rect.center().y()
            bar_height = 6
            bar_width = 2
            bar1_rect = QRect(center_x - 3, center_y - bar_height//2, bar_width, bar_height)
            bar2_rect = QRect(center_x + 1, center_y - bar_height//2, bar_width, bar_height)
            painter.drawRect(bar1_rect)
            painter.drawRect(bar2_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent_viewer:
            # Only allow pause/resume when timer is active
            if self.parent_viewer._auto_advance_active:
                self.parent_viewer.toggle_timer_pause()
        super().mousePressEvent(event)

class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_viewer = None
        self.setMouseTracking(True)
        
        # Zoom functionality
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_step = 0.1
        
        # Pan functionality for when zoomed
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.is_panning = False
        self.last_pan_point = None
        
        # Store original pixmap size for proper zoom calculations
        self.original_pixmap = None
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming"""
        if (self.parent_viewer and 
            self.parent_viewer.current_image and 
            self.pixmap() and 
            not self.pixmap().isNull()):
            
            # Accept the event to prevent it from propagating
            event.accept()
            
            # Get the wheel delta (positive = zoom in, negative = zoom out)
            delta = event.angleDelta().y()
            
            # Store mouse position for zoom centering
            mouse_pos = event.position()
            
            old_zoom = self.zoom_factor
            
            if delta > 0:
                # Zoom in
                new_zoom = min(self.zoom_factor * 1.1, self.max_zoom)
            else:
                # Zoom out
                new_zoom = max(self.zoom_factor / 1.1, self.min_zoom)
            
            if new_zoom != self.zoom_factor:
                # Calculate zoom center point
                if new_zoom > old_zoom:  # Zooming in
                    # Adjust pan offset to keep mouse position centered
                    zoom_ratio = new_zoom / old_zoom
                    widget_center_x = self.width() / 2
                    widget_center_y = self.height() / 2
                    
                    # Calculate offset from center
                    offset_from_center_x = mouse_pos.x() - widget_center_x
                    offset_from_center_y = mouse_pos.y() - widget_center_y
                    
                    # Adjust pan to keep point under mouse
                    self.pan_offset_x = self.pan_offset_x * zoom_ratio - offset_from_center_x * (zoom_ratio - 1)
                    self.pan_offset_y = self.pan_offset_y * zoom_ratio - offset_from_center_y * (zoom_ratio - 1)
                else:  # Zooming out
                    zoom_ratio = new_zoom / old_zoom
                    self.pan_offset_x *= zoom_ratio
                    self.pan_offset_y *= zoom_ratio
                
                self.zoom_factor = new_zoom
                
                # Reset pan when back to 100% or below
                if self.zoom_factor <= 1.0:
                    self.pan_offset_x = 0
                    self.pan_offset_y = 0
                    self.zoom_factor = 1.0
                
                # ZOOM OPTIMIZATION: Use debounced update to prevent excessive processing
                # during rapid wheel scrolling
                if hasattr(self.parent_viewer, '_zoom_update_timer'):
                    self.parent_viewer._zoom_update_timer.stop()
                else:
                    self.parent_viewer._zoom_update_timer = QTimer()
                    self.parent_viewer._zoom_update_timer.setSingleShot(True)
                    self.parent_viewer._zoom_update_timer.timeout.connect(
                        self.parent_viewer._smart_zoom_display)
                
                # Trigger immediate fast preview, then debounced final update
                self.parent_viewer._smart_zoom_display()  # Immediate cached display
                self.parent_viewer._zoom_update_timer.start(100)  # Debounced final update
                
                # Update status to show zoom level (but preserve LUT processing status if active)
                zoom_percent = int(self.zoom_factor * 100)
                
                # Check if LUT is processing in background
                if (hasattr(self.parent_viewer, '_async_processing_state') and 
                    self.parent_viewer._async_processing_state and
                    self.parent_viewer.current_lut):
                    # LUT processing active - show progress instead of just zoom
                    state = self.parent_viewer._async_processing_state
                    progress = (state['current_row'] / state['total_rows']) * 100
                    lut_name = self.parent_viewer.current_lut_name if self.parent_viewer.current_lut_name != "None" else "LUT"
                    if self.zoom_factor > 1.0:
                        self.parent_viewer.status.showMessage(f"Zoom: {zoom_percent}% - {lut_name} processing... {progress:.0f}% (Right-click drag to pan)")
                    else:
                        self.parent_viewer.status.showMessage(f"Zoom: {zoom_percent}% - {lut_name} processing... {progress:.0f}%")
                else:
                    # No LUT processing - show normal zoom status
                    if self.zoom_factor > 1.0:
                        self.parent_viewer.status.showMessage(f"Zoom: {zoom_percent}% (Right-click drag to pan)")
                    else:
                        self.parent_viewer.status.showMessage(f"Zoom: {zoom_percent}%")
        else:
            # Don't accept the event, let it propagate
            event.ignore()
    
    def mousePressEvent(self, event):
        # Handle middle-click for next image
        if event.button() == Qt.MiddleButton and self.parent_viewer:
            self.parent_viewer.show_next_image()
            event.accept()
            return
        
        # Handle right-click for panning when zoomed
        if (event.button() == Qt.RightButton and 
            self.zoom_factor > 1.0 and 
            self.pixmap() and 
            not self.pixmap().isNull()):
            
            self.is_panning = True
            self.last_pan_point = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        
        # Handle left-click for line drawing
        if (self.parent_viewer and 
            (self.parent_viewer.line_drawing_mode or self.parent_viewer.horizontal_line_drawing_mode or self.parent_viewer.free_line_drawing_mode) and 
            event.button() == Qt.LeftButton and 
            self.pixmap() and not self.pixmap().isNull()):
            
            # Get click position
            click_pos = event.position()
            
            # Get the currently displayed pixmap and label size
            displayed_pixmap = self.pixmap()
            label_size = self.size()
            
            # Get original image for coordinate reference
            try:
                original_pixmap, error = safe_load_pixmap(self.parent_viewer.current_image)
                if error or original_pixmap.isNull():
                    return
            except Exception:
                return
            
            # Use the original unrotated size for coordinate transformation
            original_size = original_pixmap.size()
            
            # For rotated images, we need to consider the displayed dimensions
            # The displayed image might have swapped width/height due to rotation
            rotation = self.parent_viewer.rotation_angle
            if rotation == 90 or rotation == 270:
                # At 90° and 270°, width and height are swapped
                display_reference_size = QSize(original_size.height(), original_size.width())
            else:
                # At 0° and 180°, dimensions stay the same
                display_reference_size = original_size
            
            # UNIFIED coordinate conversion - use the SAME logic as in display_image
            # Calculate the base scaled size that would be used at 100% zoom
            base_scaled = display_reference_size.scaled(label_size, Qt.KeepAspectRatio)
            
            # Apply zoom factor to get the actual displayed size
            zoomed_width = int(base_scaled.width() * self.zoom_factor)
            zoomed_height = int(base_scaled.height() * self.zoom_factor)
            
            # Calculate position within the label (including pan offset)
            draw_x = (label_size.width() - zoomed_width) // 2 + int(self.pan_offset_x)
            draw_y = (label_size.height() - zoomed_height) // 2 + int(self.pan_offset_y)
            
            # Get click position relative to the zoomed image
            rel_x = click_pos.x() - draw_x
            rel_y = click_pos.y() - draw_y
            
            # Check if click is within the zoomed image bounds
            if (0 <= rel_x <= zoomed_width and 0 <= rel_y <= zoomed_height):
                # Convert to display coordinate space using correct scale factors for rotation
                # For 90° and 270° rotations, we need to account for swapped dimensions
                if rotation == 90 or rotation == 270:
                    # When rotated 90°/270°, the displayed width/height correspond to original height/width
                    scale_x = zoomed_width / original_size.height()
                    scale_y = zoomed_height / original_size.width()
                else:
                    # Normal case (0° and 180°)
                    scale_x = zoomed_width / original_size.width()
                    scale_y = zoomed_height / original_size.height()
                
                # Convert to display coordinates (relative to the rotated image display space)
                display_x = rel_x / scale_x
                display_y = rel_y / scale_y
                
                # Transform coordinates back to original coordinate space
                # We need to reverse the transformation sequence used in display_image:
                # display_image applies: 1) flips first, 2) then rotation
                # So we reverse: 1) undo rotation first, 2) then undo flips
                
                rotation = self.parent_viewer.rotation_angle
                flipped_h = self.parent_viewer.flipped_h
                flipped_v = self.parent_viewer.flipped_v
                
                # Step 1: Undo rotation transformation
                if rotation == 0:
                    # No rotation
                    unrotated_x = display_x
                    unrotated_y = display_y
                elif rotation == 90:
                    # Undo 90° clockwise rotation (width/height swapped)
                    unrotated_x = display_y
                    unrotated_y = original_size.width() - display_x
                elif rotation == 180:
                    # Undo 180° rotation
                    unrotated_x = original_size.width() - display_x
                    unrotated_y = original_size.height() - display_y
                elif rotation == 270:
                    # Undo 270° clockwise rotation
                    unrotated_x = original_size.height() - display_y
                    unrotated_y = display_x
                else:
                    # Fallback for other angles
                    unrotated_x = display_x
                    unrotated_y = display_y
                
                # Step 2: Undo flip transformations to get original coordinates
                original_x = unrotated_x
                original_y = unrotated_y
                
                if flipped_h:
                    original_x = original_size.width() - unrotated_x
                if flipped_v:
                    original_y = original_size.height() - unrotated_y
                
                # Add lines using original coordinates (these will be transformed during display)
                if self.parent_viewer.line_drawing_mode:
                    self.parent_viewer.add_line(original_x)
                if self.parent_viewer.horizontal_line_drawing_mode:
                    self.parent_viewer.add_hline(original_y)
                if self.parent_viewer.free_line_drawing_mode:
                    self.parent_viewer.add_free_line_point(original_x, original_y)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.is_panning and self.last_pan_point is not None:
            # Calculate pan delta
            current_point = event.position()
            delta_x = current_point.x() - self.last_pan_point.x()
            delta_y = current_point.y() - self.last_pan_point.y()
            
            # Update pan offset
            self.pan_offset_x += delta_x
            self.pan_offset_y += delta_y
            
            # Update last point
            self.last_pan_point = current_point
            
            # Refresh the display using smart zoom system to preserve LUT processing
            if self.parent_viewer and self.parent_viewer.current_image:
                self.parent_viewer._smart_zoom_display()
            
            event.accept()
            return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton and self.is_panning:
            self.is_panning = False
            self.last_pan_point = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        
        super().mouseReleaseEvent(event)
    
    def show_context_menu(self, pos):
        """Show context menu with image and zoom options"""
        if not self.parent_viewer:
            return
        
        # Hide context menu when zoomed in to avoid interfering with panning
        if hasattr(self, 'zoom_factor') and self.zoom_factor > 1.0:
            return
            
        menu = QMenu(self)
        
        # --- Main actions ---
        open_action = QAction("Open Folder", self)
        open_action.triggered.connect(self.parent_viewer.choose_folder)
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        prev_action = QAction("Previous Image", self)
        prev_action.triggered.connect(self.parent_viewer.show_previous_image)
        menu.addAction(prev_action)
        
        next_action = QAction("Next Image", self)
        next_action.triggered.connect(self.parent_viewer._manual_next_image)
        menu.addAction(next_action)
        
        menu.addSeparator()
        
        # --- Zoom actions ---
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.parent_viewer.zoom_in)
        menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.parent_viewer.zoom_out)
        menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction("Reset Zoom", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.parent_viewer.reset_zoom)
        menu.addAction(reset_zoom_action)
        
        menu.addSeparator()
        
        # --- Transform actions ---
        flip_h_action = QAction("Flip Horizontal", self)
        flip_h_action.setShortcut("Ctrl+H")
        flip_h_action.triggered.connect(self.parent_viewer.flip_horizontal)
        menu.addAction(flip_h_action)
        
        flip_v_action = QAction("Flip Vertical", self)
        flip_v_action.setShortcut("Ctrl+V")
        flip_v_action.triggered.connect(self.parent_viewer.flip_vertical)
        menu.addAction(flip_v_action)
        
        menu.addSeparator()
        
        # --- View actions ---
        if self.parent_viewer.is_fullscreen:
            # When in fullscreen, show explicit exit option
            exit_fullscreen_action = QAction("Exit Fullscreen", self)
            exit_fullscreen_action.setShortcut("Esc")
            exit_fullscreen_action.triggered.connect(self.parent_viewer.exit_fullscreen)
            menu.addAction(exit_fullscreen_action)
            
            # Add force exit as backup
            force_exit_action = QAction("Force Exit Fullscreen", self)
            force_exit_action.setShortcut("Ctrl+Esc")
            force_exit_action.triggered.connect(self.parent_viewer.force_exit_fullscreen)
            menu.addAction(force_exit_action)
        else:
            # When not in fullscreen, show toggle option
            fullscreen_action = QAction("Enter Fullscreen", self)
            fullscreen_action.setShortcut("F11")
            fullscreen_action.triggered.connect(lambda: self.parent_viewer.toggle_fullscreen(True))
            menu.addAction(fullscreen_action)
        
        # UI visibility toggle (especially useful in fullscreen)
        ui_toggle_action = QAction("Show/Hide UI Elements", self)
        ui_toggle_action.setCheckable(True)
        ui_toggle_action.setChecked(self.parent_viewer.main_toolbar.isVisible())
        ui_toggle_action.toggled.connect(self.parent_viewer.toggle_toolbar_visibility)
        menu.addAction(ui_toggle_action)
        
        menu.addSeparator()
        
        # --- Settings ---
        if hasattr(self.parent_viewer, 'toggle_grayscale'):
            grayscale_action = QAction("Grayscale", self)
            grayscale_action.setCheckable(True)
            grayscale_action.setChecked(self.parent_viewer.grayscale_value > 0)
            grayscale_action.toggled.connect(self.parent_viewer.toggle_grayscale)
            menu.addAction(grayscale_action)
        
        if hasattr(self.parent_viewer, 'toggle_contrast'):
            contrast_action = QAction("Enhanced Contrast", self)
            contrast_action.setCheckable(True)
            contrast_action.setChecked(self.parent_viewer.contrast_value != 50)
            contrast_action.toggled.connect(self.parent_viewer.toggle_contrast)
            menu.addAction(contrast_action)
        
        if hasattr(self.parent_viewer, 'toggle_gamma'):
            gamma_action = QAction("Enhanced Brightness", self)
            gamma_action.setCheckable(True)
            gamma_action.setChecked(self.parent_viewer.gamma_value != 50)
            gamma_action.toggled.connect(self.parent_viewer.toggle_gamma)
            menu.addAction(gamma_action)
        
        # Show the menu
        menu.exec(self.mapToGlobal(pos))
    
    def reset_zoom(self):
        """Reset zoom to 100% and clear pan"""
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0

class ResponsiveEnhancementWidget(QWidget):
    """A responsive widget that adapts layout based on available width"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_viewer = None
        self.min_width_threshold = 280  # Reduced threshold for better detection
        self.current_layout_mode = "horizontal"  # Track current layout
        
        # Set minimum size to ensure visibility
        self.setMinimumSize(270, 24)
        self.setMaximumHeight(48)  # Allow for vertical layout
        
        # Create all controls
        self.create_controls()
        self.setup_horizontal_layout()  # Start with horizontal layout
        
    def create_controls(self):
        """Create all the enhancement controls"""
        # Grayscale controls
        self.gray_label = QLabel("Gray:")
        self.gray_label.setFixedWidth(30)
        self.gray_label.setStyleSheet("font-size: 9px;")
        
        self.grayscale_slider = ClickableSlider(Qt.Horizontal)
        self.grayscale_slider.setRange(0, 100)
        self.grayscale_slider.setValue(0)
        self.grayscale_slider.setFixedWidth(60)
        self.grayscale_slider.setFixedHeight(20)
        self.grayscale_slider.setToolTip("Grayscale: 0=Color, 100=B&W")
        
        # Contrast controls
        self.contrast_label = QLabel("Con:")
        self.contrast_label.setFixedWidth(25)
        self.contrast_label.setStyleSheet("font-size: 9px;")
        
        self.contrast_slider = ClickableSlider(Qt.Horizontal)
        self.contrast_slider.setRange(0, 200)
        self.contrast_slider.setValue(50)
        self.contrast_slider.setFixedWidth(60)
        self.contrast_slider.setFixedHeight(20)
        self.contrast_slider.setToolTip("Contrast: 50=Normal, 0=Flat, 200=Extreme")
        
        # Gamma controls
        self.gamma_label = QLabel("Gam:")
        self.gamma_label.setFixedWidth(25)
        self.gamma_label.setStyleSheet("font-size: 9px;")
        
        self.gamma_slider = ClickableSlider(Qt.Horizontal)
        self.gamma_slider.setRange(-200, 500)  # New range: -200=very dark, 0=normal, 500=very bright
        self.gamma_slider.setValue(0)
        self.gamma_slider.setFixedWidth(60)
        self.gamma_slider.setFixedHeight(20)
        self.gamma_slider.setToolTip("Gamma: -200=Very Dark, 0=Normal, 500=Very Bright")
        
        # Reset button
        self.reset_btn = QToolButton()
        self.reset_btn.setText("↺")
        self.reset_btn.setToolTip("Reset Enhancements")
        self.reset_btn.setFixedSize(16, 20)
    
    def setup_horizontal_layout(self):
        """Setup horizontal layout for wide windows"""
        self.clear_layout()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        layout.setSpacing(2)
        
        layout.addWidget(self.gray_label)
        layout.addWidget(self.grayscale_slider)
        layout.addWidget(self.contrast_label)
        layout.addWidget(self.contrast_slider)
        layout.addWidget(self.gamma_label)
        layout.addWidget(self.gamma_slider)
        layout.addWidget(self.reset_btn)
        
        self.current_layout_mode = "horizontal"
        self.setMaximumHeight(24)  # Single row height
        
    def setup_vertical_layout(self):
        """Setup vertical/grid layout for narrow windows"""
        self.clear_layout()
        
        layout = QGridLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)  # Small margins
        layout.setSpacing(1)
        
        # Row 1: Gray and Contrast
        layout.addWidget(self.gray_label, 0, 0)
        layout.addWidget(self.grayscale_slider, 0, 1)
        layout.addWidget(self.contrast_label, 0, 2)
        layout.addWidget(self.contrast_slider, 0, 3)
        
        # Row 2: Gamma and Reset
        layout.addWidget(self.gamma_label, 1, 0)
        layout.addWidget(self.gamma_slider, 1, 1)
        layout.addWidget(self.reset_btn, 1, 2, 1, 2)  # Span 2 columns
        
        self.current_layout_mode = "vertical"
        self.setMaximumHeight(48)  # Two row height
    
    def clear_layout(self):
        """Remove all widgets from current layout"""
        if self.layout():
            while self.layout().count():
                child = self.layout().takeAt(0)
                if child.widget():
                    child.widget().setParent(None)
            # Schedule the layout for deletion
            self.layout().deleteLater()
    
    def resizeEvent(self, event):
        # Simple debounced resize handling
        self.resize_timer.start(100)  # 100ms debounce
        super().resizeEvent(event)
        
    def _delayed_resize(self):
        """Handle resize events with a delay to improve performance"""
        # Check if we need to move sliders to second row
        current_width = self.width()
        should_use_two_rows = current_width < self.width_threshold
        
        # Only switch if the mode actually needs to change AND we have minimal hysteresis
        if should_use_two_rows != self.two_row_mode:
            # Reduced hysteresis to prevent rapid switching
            if should_use_two_rows and current_width < (self.width_threshold - 10):
                self._update_toolbar_layout(current_width)
            elif not should_use_two_rows and current_width > (self.width_threshold + 10):
                self._update_toolbar_layout(current_width)
        
        # Handle image display resize using smart caching system
        if self.current_image:
            # Use smart zoom display to preserve LUT caching during resize
            self._smart_zoom_display()

    def sizeHint(self):
        """Provide a size hint for the layout system"""
        if self.current_layout_mode == "horizontal":
            return QSize(270, 24)
        else:
            return QSize(200, 48)
    
    def set_parent_viewer(self, viewer):
        """Connect to parent viewer and setup signal connections"""
        self.parent_viewer = viewer
        self.grayscale_slider.valueChanged.connect(viewer.update_grayscale)
        self.contrast_slider.valueChanged.connect(viewer.update_contrast)
        self.gamma_slider.valueChanged.connect(viewer.update_gamma)
        self.reset_btn.clicked.connect(viewer.reset_enhancements)

class GPULutProcessor:
    """GPU-accelerated LUT processing using OpenCL"""
    
    def __init__(self):
        self.context = None
        self.queue = None
        self.program = None
        self.device = None
        self.gpu_enabled = False
        self.max_buffer_size = 0
        self._force_reinit = True  # CRITICAL: Force GPU reinit to test reversed indexing formula
        
        # Cache kernels to avoid repeated retrieval
        self._kernel_cache = {}
        
        if GPU_AVAILABLE:
            self._initialize_gpu()
    
    def _initialize_gpu(self):
        """Initialize OpenCL context and compile kernels"""
        try:
            # Get available platforms and devices
            platforms = cl.get_platforms()
            if not platforms:
                print("No OpenCL platforms found")
                return
            
            # Try to find a GPU device first, fallback to any device
            device = None
            for platform in platforms:
                try:
                    devices = platform.get_devices(cl.device_type.GPU)
                    if devices:
                        device = devices[0]
                        print(f"Using GPU: {device.name}")
                        break
                except:
                    continue
            
            # If no GPU found, try any device
            if device is None:
                for platform in platforms:
                    try:
                        devices = platform.get_devices()
                        if devices:
                            device = devices[0]
                            print(f"Using device: {device.name}")
                            break
                    except:
                        continue
            
            if device is None:
                print("No suitable OpenCL device found")
                return
            
            # Create context and command queue
            self.context = cl.Context([device])
            self.queue = cl.CommandQueue(self.context)
            self.device = device
            
            # Get device limits
            self.max_buffer_size = device.max_mem_alloc_size
            print(f"GPU max buffer size: {self.max_buffer_size // (1024*1024)} MB")
            
            # Compile OpenCL kernel
            kernel_source = self._get_lut_kernel_source()
            self.program = cl.Program(self.context, kernel_source).build()
            
            self.gpu_enabled = True
            print("GPU LUT processing initialized successfully")
            
            # Cache kernels for reuse to avoid repeated retrieval warning
            self._cache_kernels()
            
        except Exception as e:
            print(f"Failed to initialize GPU: {e}")
            print("GPU initialization details:")
            try:
                import traceback
                traceback.print_exc()
                
                # Try to get more detailed OpenCL information
                if GPU_AVAILABLE and cl:
                    platforms = cl.get_platforms()
                    print(f"Available OpenCL platforms: {len(platforms)}")
                    for i, platform in enumerate(platforms):
                        print(f"  Platform {i}: {platform.name}")
                        try:
                            devices = platform.get_devices()
                            print(f"    Devices: {len(devices)}")
                            for j, device in enumerate(devices):
                                print(f"      Device {j}: {device.name} ({device.vendor})")
                        except Exception as dev_e:
                            print(f"    Error getting devices: {dev_e}")
                else:
                    print("OpenCL not available")
            except Exception as debug_e:
                print(f"Error getting GPU debug info: {debug_e}")
            
            self.gpu_enabled = False
    
    def _cache_kernels(self):
        """Cache OpenCL kernels to avoid repeated retrieval"""
        if self.program and self.gpu_enabled:
            try:
                self._kernel_cache['apply_lut_3d'] = cl.Kernel(self.program, 'apply_lut_3d')
                self._kernel_cache['draw_lines_gpu'] = cl.Kernel(self.program, 'draw_lines_gpu')
                print("GPU kernels cached successfully")
            except Exception as e:
                print(f"Error caching kernels: {e}")
    
    def _get_lut_kernel_source(self):
        """OpenCL kernel source code for LUT processing"""
        return """
        __kernel void apply_lut_3d(
            __global uchar4* image,
                // IMPORTANT: use flat float array instead of float3 to avoid 16-byte stride padding issues
                __global const float* lut_data,
            const int width,
            const int height,
            const int lut_size,
            const float strength
        ) {
            int gid = get_global_id(0);
            
            if (gid >= width * height) return;
            
            // Get pixel - Qt RGB32 format stores BGRA bytes in memory
            uchar4 pixel = image[gid];
            
            // CONFIRMED: Channel mapping is correct! 
            // GPU: pixel.x=Blue, pixel.y=Green, pixel.z=Red, pixel.w=Alpha
            float b = pixel.x / 255.0f;  // Blue
            float g = pixel.y / 255.0f;  // Green
            float r = pixel.z / 255.0f;  // Red
            
            // Clamp input values
            r = clamp(r, 0.0f, 1.0f);
            g = clamp(g, 0.0f, 1.0f);
            b = clamp(b, 0.0f, 1.0f);
            
                // High-quality trilinear interpolation
                // Position in LUT space (0 .. lut_size-1)
                float rf = r * (float)(lut_size - 1);
                float gf = g * (float)(lut_size - 1);
                float bf = b * (float)(lut_size - 1);

                int r0 = (int)floor(rf); int r1; float fr;
                if (r0 >= lut_size - 1) { r0 = lut_size - 2; r1 = lut_size - 1; fr = 1.0f; } else { r1 = r0 + 1; fr = rf - (float)r0; }
                int g0 = (int)floor(gf); int g1; float fg;
                if (g0 >= lut_size - 1) { g0 = lut_size - 2; g1 = lut_size - 1; fg = 1.0f; } else { g1 = g0 + 1; fg = gf - (float)g0; }
                int b0 = (int)floor(bf); int b1; float fb;
                if (b0 >= lut_size - 1) { b0 = lut_size - 2; b1 = lut_size - 1; fb = 1.0f; } else { b1 = b0 + 1; fb = bf - (float)b0; }

                // Helper lambda-like macro to fetch color (r,g,b indices)
                #define LUT_IDX(R,G,B) (((R) + (G) * lut_size + (B) * lut_size * lut_size) * 3)
                int i000 = LUT_IDX(r0,g0,b0);
                int i100 = LUT_IDX(r1,g0,b0);
                int i010 = LUT_IDX(r0,g1,b0);
                int i110 = LUT_IDX(r1,g1,b0);
                int i001 = LUT_IDX(r0,g0,b1);
                int i101 = LUT_IDX(r1,g0,b1);
                int i011 = LUT_IDX(r0,g1,b1);
                int i111 = LUT_IDX(r1,g1,b1);

                float3 c000 = (float3)(lut_data[i000+0], lut_data[i000+1], lut_data[i000+2]);
                float3 c100 = (float3)(lut_data[i100+0], lut_data[i100+1], lut_data[i100+2]);
                float3 c010 = (float3)(lut_data[i010+0], lut_data[i010+1], lut_data[i010+2]);
                float3 c110 = (float3)(lut_data[i110+0], lut_data[i110+1], lut_data[i110+2]);
                float3 c001 = (float3)(lut_data[i001+0], lut_data[i001+1], lut_data[i001+2]);
                float3 c101 = (float3)(lut_data[i101+0], lut_data[i101+1], lut_data[i101+2]);
                float3 c011 = (float3)(lut_data[i011+0], lut_data[i011+1], lut_data[i011+2]);
                float3 c111 = (float3)(lut_data[i111+0], lut_data[i111+1], lut_data[i111+2]);

                // Interpolate along R
                float3 c00 = c000 + (c100 - c000) * fr;
                float3 c10 = c010 + (c110 - c010) * fr;
                float3 c01 = c001 + (c101 - c001) * fr;
                float3 c11 = c011 + (c111 - c011) * fr;
                // Interpolate along G
                float3 c0 = c00 + (c10 - c00) * fg;
                float3 c1 = c01 + (c11 - c01) * fg;
                // Interpolate along B
                float3 c_final = c0 + (c1 - c0) * fb;

                float lut_r = c_final.x;
                float lut_g = c_final.y;
                float lut_b = c_final.z;
                #undef LUT_IDX
            
            // Apply strength blending
            float final_r, final_g, final_b;
            if (strength < 0.01f) {
                final_r = r;
                final_g = g;
                final_b = b;
            } else {
                final_r = r * (1.0f - strength) + lut_r * strength;
                final_g = g * (1.0f - strength) + lut_g * strength;
                final_b = b * (1.0f - strength) + lut_b * strength;
            }
            
            // Clamp final values
            final_r = clamp(final_r, 0.0f, 1.0f);
            final_g = clamp(final_g, 0.0f, 1.0f);
            final_b = clamp(final_b, 0.0f, 1.0f);
            
            // Write back in correct BGRA format
            image[gid].x = (uchar)(final_b * 255.0f);  // Blue
            image[gid].y = (uchar)(final_g * 255.0f);  // Green
            image[gid].z = (uchar)(final_r * 255.0f);  // Red
            image[gid].w = 255;  // Alpha
        }
        
        __kernel void draw_lines_gpu(
            __global uchar4* image,
            __global int* vertical_lines,
            __global int* horizontal_lines,
            __global int4* free_lines,  // start_x, start_y, end_x, end_y
            const int width,
            const int height,
            const int num_vertical,
            const int num_horizontal,
            const int num_free,
            const uchar4 line_color,
            const int line_thickness
        ) {
            int x = get_global_id(0);
            int y = get_global_id(1);
            
            if (x >= width || y >= height) return;
            
            int pixel_idx = y * width + x;
            bool draw_pixel = false;
            
            // Check vertical lines
            for (int i = 0; i < num_vertical; i++) {
                int line_x = vertical_lines[i];
                int distance = abs(x - line_x);
                if (distance <= line_thickness / 2) {
                    draw_pixel = true;
                    break;
                }
            }
            
            // Check horizontal lines
            if (!draw_pixel) {
                for (int i = 0; i < num_horizontal; i++) {
                    int line_y = horizontal_lines[i];
                    int distance = abs(y - line_y);
                    if (distance <= line_thickness / 2) {
                        draw_pixel = true;
                        break;
                    }
                }
            }
            
            // Check free lines (using distance to line segment)
            if (!draw_pixel) {
                for (int i = 0; i < num_free; i++) {
                    int4 line = free_lines[i];
                    int x1 = line.x, y1 = line.y, x2 = line.z, y2 = line.w;
                    
                    // Calculate distance from point to line segment
                    int dx = x2 - x1;
                    int dy = y2 - y1;
                    int line_len_sq = dx * dx + dy * dy;
                    
                    if (line_len_sq == 0) {
                        // Line is actually a point
                        int dist_sq = (x - x1) * (x - x1) + (y - y1) * (y - y1);
                        if (dist_sq <= (line_thickness / 2) * (line_thickness / 2)) {
                            draw_pixel = true;
                            break;
                        }
                    } else {
                        // Project point onto line segment
                        int t_num = (x - x1) * dx + (y - y1) * dy;
                        float t = (float)t_num / line_len_sq;
                        t = clamp(t, 0.0f, 1.0f);
                        
                        int proj_x = x1 + (int)(t * dx);
                        int proj_y = y1 + (int)(t * dy);
                        
                        int dist_sq = (x - proj_x) * (x - proj_x) + (y - proj_y) * (y - proj_y);
                        if (dist_sq <= (line_thickness / 2) * (line_thickness / 2)) {
                            draw_pixel = true;
                            break;
                        }
                    }
                }
            }
            
            // Draw the pixel if it's part of any line
            if (draw_pixel) {
                image[pixel_idx] = line_color;
            }
        }
        """
    
    def apply_lut_gpu(self, image, lut_data, lut_size, strength_factor=1.0):
        """Apply LUT using GPU acceleration"""
        if not self.gpu_enabled:
            return None
            
        try:
            width = image.width()
            height = image.height()
            total_pixels = width * height
            
            # Convert image to numpy array
            image_array = self._qimage_to_numpy(image)
            
            # Convert LUT data to numpy array
            lut_array = self._prepare_lut_data(lut_data, lut_size)
            
            # Optimized for 12GB GPU - conservative thresholds to avoid OUT_OF_RESOURCES
            image_size_bytes = image_array.nbytes
            lut_size_bytes = lut_array.nbytes
            total_size = image_size_bytes + lut_size_bytes
            
            # For 12GB GPU, process directly without chunking - simpler and more reliable
            print(f"Using direct GPU processing for {width}x{height} image ({total_pixels} pixels, {total_size//1024//1024}MB)")
            return self._apply_lut_full(image_array, lut_array, width, height, lut_size, strength_factor)
                
        except Exception as e:
            print(f"GPU LUT processing failed: {e}")
            return None
    
    def _qimage_to_numpy(self, qimage):
        """Convert QImage to numpy array for GPU processing"""
        # Use RGB32 format which is consistent and well-defined
        if qimage.format() != qimage.Format.Format_RGB32:
            qimage = qimage.convertToFormat(qimage.Format.Format_RGB32)
        
        width = qimage.width()
        height = qimage.height()
        
        # Get raw image data
        ptr = qimage.constBits()
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 4))
        
        # Create a copy to ensure it's writable
        return np.copy(arr)
    
    def _prepare_lut_data(self, lut_data, lut_size):
        """Convert LUT data to GPU format"""
        # Convert list of tuples to numpy array
        lut_array = np.array(lut_data, dtype=np.float32)
        
        # DEBUG: Print first few LUT values to check data format
        print(f"LUT DEBUG: First 3 LUT entries:")
        for i in range(min(3, len(lut_data))):
            print(f"  LUT[{i}]: {lut_data[i]} -> numpy: {lut_array[i]}")
        
        # Ensure it's the right shape for OpenCL float3
        expected_size = lut_size * lut_size * lut_size
        if lut_array.shape[0] != expected_size:
            raise ValueError(f"LUT data size mismatch: expected {expected_size}, got {lut_array.shape[0]}")
        
        # Ensure the array is contiguous and properly shaped for float3
        if lut_array.shape[1] != 3:
            raise ValueError(f"LUT data should have 3 components (RGB), got {lut_array.shape[1]}")
        
        # Make sure the array is C-contiguous for proper GPU transfer
        lut_array = np.ascontiguousarray(lut_array, dtype=np.float32)
        
        print(f"LUT DEBUG: Array shape: {lut_array.shape}, dtype: {lut_array.dtype}, contiguous: {lut_array.flags['C_CONTIGUOUS']}")
        return lut_array
    
    def _apply_lut_full(self, image_array, lut_array, width, height, lut_size, strength_factor):
        """Apply LUT using full image processing"""
        try:
            # Flatten image array for processing
            image_flat = image_array.reshape(-1, 4).astype(np.uint8)
            
            # Create OpenCL buffers
            image_buffer = cl.Buffer(self.context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=image_flat)
            lut_buffer = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=lut_array)
            
            # Set kernel arguments using cached kernel
            kernel = self._kernel_cache.get('apply_lut_3d')
            if not kernel:
                kernel = cl.Kernel(self.program, 'apply_lut_3d')
                self._kernel_cache['apply_lut_3d'] = kernel
            
            kernel.set_args(image_buffer, lut_buffer, np.int32(width), np.int32(height), np.int32(lut_size), np.float32(strength_factor))
            
            # Execute kernel
            global_size = (width * height,)
            cl.enqueue_nd_range_kernel(self.queue, kernel, global_size, None)
            
            # Read result back
            result_flat = np.empty_like(image_flat)
            cl.enqueue_copy(self.queue, result_flat, image_buffer)
            self.queue.finish()
            
            # Reshape back to original form
            result_array = result_flat.reshape(image_array.shape)
            
            # Convert back to QImage
            return self._numpy_to_qimage(result_array, width, height)
            
        except Exception as e:
            print(f"Full GPU processing error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _apply_lut_chunked(self, image_array, lut_array, width, height, lut_size, strength_factor):
        """Apply LUT using chunked processing for large images"""
        try:
            # Use reasonable chunk size for 12GB GPU - larger chunks for better performance
            # Process 200 rows at a time for good performance without resource issues
            rows_per_chunk = 200  # Larger chunks for 12GB GPU
            
            print(f"Processing {width}x{height} image in chunks of {rows_per_chunk} rows ({rows_per_chunk * width} pixels per chunk)")
            
            # Create LUT buffer once
            lut_buffer = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=lut_array)
            
            result_array = np.copy(image_array)
            
            # Process in chunks
            for start_row in range(0, height, rows_per_chunk):
                end_row = min(start_row + rows_per_chunk, height)
                chunk_height = end_row - start_row
                
                # Extract chunk and flatten for GPU processing
                chunk_data = image_array[start_row:end_row, :, :].reshape(-1, 4).astype(np.uint8)
                
                # Create chunk buffer
                chunk_buffer = cl.Buffer(self.context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=chunk_data)
                
                # Set kernel arguments for chunked processing using cached kernel
                kernel = self._kernel_cache.get('apply_lut_chunked')
                if not kernel:
                    kernel = cl.Kernel(self.program, 'apply_lut_chunked')
                    self._kernel_cache['apply_lut_chunked'] = kernel
                
                kernel.set_args(chunk_buffer, lut_buffer, np.int32(width), np.int32(height), 
                               np.int32(lut_size), np.float32(strength_factor), 
                               np.int32(start_row), np.int32(chunk_height))
                
                # Execute kernel with 1D work-group (more compatible)
                total_pixels = width * chunk_height
                global_size = (total_pixels,)
                # Use 1D indexing to avoid work-group size issues
                cl.enqueue_nd_range_kernel(self.queue, kernel, global_size, None)
                
                # Read chunk result back
                chunk_result_flat = np.empty_like(chunk_data)
                cl.enqueue_copy(self.queue, chunk_result_flat, chunk_buffer)
                self.queue.finish()
                
                # Reshape and copy back to result
                chunk_result = chunk_result_flat.reshape((chunk_height, width, 4))
                result_array[start_row:end_row, :, :] = chunk_result
            
            return self._numpy_to_qimage(result_array, width, height)
            
        except Exception as e:
            print(f"Chunked GPU processing error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _numpy_to_qimage(self, array, width, height):
        """Convert numpy array back to QImage"""
        # Ensure data is contiguous
        if not array.flags['C_CONTIGUOUS']:
            array = np.ascontiguousarray(array)
        
        # Create QImage from numpy array using RGB32 format
        qimage = QImage(array.data, width, height, width * 4, QImage.Format.Format_RGB32)
        
        # Return a copy to ensure the data persists
        return qimage.copy()
    
    def draw_lines_gpu(self, image, vertical_lines, horizontal_lines, free_lines, line_color, line_thickness):
        """Draw lines on image using GPU acceleration"""
        if not self.gpu_enabled:
            return None
            
        try:
            width = image.width()
            height = image.height()

            # Ensure consistent RGB32 (BGRA) format to match kernel expectation
            if image.format() != image.Format.Format_RGB32:
                image = image.convertToFormat(image.Format.Format_RGB32)
            image_array = self._qimage_to_numpy(image)
            
            # Prepare line data
            vertical_array = np.array(vertical_lines, dtype=np.int32) if vertical_lines else np.array([], dtype=np.int32)
            horizontal_array = np.array(horizontal_lines, dtype=np.int32) if horizontal_lines else np.array([], dtype=np.int32)
            
            # Convert free lines to flat array [x1, y1, x2, y2, x1, y1, x2, y2, ...]
            free_array = np.array([], dtype=np.int32)
            if free_lines:
                free_flat = []
                for line in free_lines:
                    start_x, start_y = line['start']
                    end_x, end_y = line['end']
                    free_flat.extend([int(start_x), int(start_y), int(end_x), int(end_y)])
                free_array = np.array(free_flat, dtype=np.int32).reshape(-1, 4)
            
            # Pack color as BGRA for in-memory layout (Qt RGB32)
            color_bgra = np.array([line_color.blue(), line_color.green(), line_color.red(), line_color.alpha()], dtype=np.uint8)
            
            # Create OpenCL buffers
            image_flat = image_array.reshape(-1, 4).astype(np.uint8)
            image_buffer = cl.Buffer(self.context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=image_flat)
            
            # Create buffers for line data (handle empty arrays)
            if len(vertical_array) > 0:
                vertical_buffer = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=vertical_array)
            else:
                vertical_buffer = cl.Buffer(self.context, cl.mem_flags.READ_ONLY, 4)
                
            if len(horizontal_array) > 0:
                horizontal_buffer = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=horizontal_array)
            else:
                horizontal_buffer = cl.Buffer(self.context, cl.mem_flags.READ_ONLY, 4)
                
            if len(free_array) > 0:
                free_buffer = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=free_array)
            else:
                free_buffer = cl.Buffer(self.context, cl.mem_flags.READ_ONLY, 16)  # 4 ints
            
            # Set kernel arguments using cached kernel to avoid repeated retrieval warning
            kernel = self._kernel_cache.get('draw_lines_gpu')
            if not kernel:
                kernel = cl.Kernel(self.program, 'draw_lines_gpu')
                self._kernel_cache['draw_lines_gpu'] = kernel
            kernel.set_arg(0, image_buffer)
            kernel.set_arg(1, vertical_buffer)
            kernel.set_arg(2, horizontal_buffer)
            kernel.set_arg(3, free_buffer)
            kernel.set_arg(4, np.int32(width))
            kernel.set_arg(5, np.int32(height))
            kernel.set_arg(6, np.int32(len(vertical_lines) if vertical_lines else 0))
            kernel.set_arg(7, np.int32(len(horizontal_lines) if horizontal_lines else 0))
            kernel.set_arg(8, np.int32(len(free_lines) if free_lines else 0))
            kernel.set_arg(9, color_bgra)
            kernel.set_arg(10, np.int32(line_thickness))
            
            # Execute kernel
            global_size = (width, height)
            cl.enqueue_nd_range_kernel(self.queue, kernel, global_size, None)
            
            # Read result back
            result_array = np.empty_like(image_flat)
            cl.enqueue_copy(self.queue, result_array, image_buffer)
            self.queue.finish()
            
            # Convert back to QImage (RGB32/BGRA)
            result_array = result_array.reshape(height, width, 4)
            result_image = QImage(result_array.data, width, height, width * 4, QImage.Format.Format_RGB32)
            return QPixmap.fromImage(result_image)
            
        except Exception as e:
            print(f"GPU line drawing failed: {e}")
            return None
    
    def is_available(self):
        """Check if GPU processing is available, handle reinit if needed"""
        if hasattr(self, '_force_reinit') and self._force_reinit:
            print("Reinitializing GPU processor with DEBUG kernels...")
            self._force_reinit = False
            self._kernel_cache.clear()  # Clear kernel cache to force recompilation
            if GPU_AVAILABLE:
                self._initialize_gpu()
        return self.gpu_enabled
    
    def get_device_info(self):
        """Get information about the GPU device"""
        if not self.gpu_enabled or not self.device:
            return "GPU not available"
        
        try:
            device_name = self.device.name
            device_vendor = self.device.vendor
            max_memory = self.device.max_mem_alloc_size // (1024 * 1024)
            compute_units = self.device.max_compute_units
            
            return f"{device_vendor} {device_name} ({max_memory}MB, {compute_units} CUs)"
        except:
            return "GPU device info unavailable"

    def cleanup(self):
        """Clean up GPU resources"""
        if self.context:
            self.context = None
        if self.queue:
            self.queue = None
        self.gpu_enabled = False

class RandomImageViewer(QMainWindow):
    # ...existing code...
    def _compute_line_transform(self):
        """Compute scaling and offset for mapping original image coords to current displayed pixmap.
        Returns dict with scale_x, scale_y, draw_x, draw_y. Now supports rotation and flips."""
        try:
            if not hasattr(self, 'original_pixmap') or not self.original_pixmap:
                return None
            if not self.image_label or not self.image_label.pixmap():
                return None
            
            original_size = self.original_pixmap.size()
            label_size = self.image_label.size()
            zoom_factor = getattr(self.image_label, 'zoom_factor', 1.0)
            
            # For rotated images (90° and 270°), the display dimensions are swapped
            if self.rotation_angle == 90 or self.rotation_angle == 270:
                # Use swapped dimensions as reference for scaling
                display_reference_size = QSize(original_size.height(), original_size.width())
            else:
                # 0° and 180° keep the same dimensions
                display_reference_size = original_size
            
            # Base scaled size at 100% (aspect fit) using the correct reference dimensions
            base_scaled = display_reference_size.scaled(label_size, Qt.KeepAspectRatio)
            zoomed_width = int(base_scaled.width() * zoom_factor)
            zoomed_height = int(base_scaled.height() * zoom_factor)
            draw_x = (label_size.width() - zoomed_width) // 2 + int(getattr(self.image_label, 'pan_offset_x', 0))
            draw_y = (label_size.height() - zoomed_height) // 2 + int(getattr(self.image_label, 'pan_offset_y', 0))
            scale_x = zoomed_width / original_size.width() if original_size.width() else 1.0
            scale_y = zoomed_height / original_size.height() if original_size.height() else 1.0
            return {
                'scale_x': scale_x,
                'scale_y': scale_y,
                'draw_x': draw_x,
                'draw_y': draw_y,
                'zoomed_width': zoomed_width,
                'zoomed_height': zoomed_height
            }
        except Exception as e:
            print(f"_compute_line_transform error: {e}")
            return None
    def _fast_line_update(self):
        """Fast path to redraw only lines over current displayed image using GPU if available.
        Falls back to full display_image if prerequisites missing.
        Assumes self.current_image is path to original image file."""
        try:
            if not self.current_image:
                return
            if not (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
                return
            if not self.lines_visible:
                return
            # Get currently displayed pixmap (may already have LUT/enhancements applied)
            current_pixmap = self.image_label.pixmap()
            if (not current_pixmap) or current_pixmap.isNull():
                # Fallback: full redraw
                self.display_image(self.current_image)
                return
            # If rotation or flips are active we must avoid the GPU fast-path (it expects non-transformed pixmaps).
            # Allow the CPU fallback below to handle transformed images, so DO NOT call display_image()
            transforms_active = (self.rotation_angle != 0 or self.flipped_h or self.flipped_v)
            # Use GPU accelerated overlay when possible & image large enough
            # Only use GPU accelerated overlay when no transforms are active
            if (not transforms_active and hasattr(self, 'gpu_processor') and self.gpu_processor and 
                self.gpu_processor.is_available() and 
                current_pixmap.width() * current_pixmap.height() > 100000):
                # Convert to image in BGRA/rgba format
                image = current_pixmap.toImage()
                if image.format() != image.Format.Format_RGBA8888:
                    image = image.convertToFormat(image.Format.Format_RGBA8888)
                # Prepare scaled coordinates (since current_pixmap is already scaled/zoomed)
                # We assume original_pixmap exists to compute scale; if not, fallback
                if not hasattr(self, 'original_pixmap') or not self.original_pixmap:
                    self.display_image(self.current_image)
                    return
                tx = self._compute_line_transform()
                if not tx:
                    self.display_image(self.current_image)
                    return
                scale_x = tx['scale_x']; scale_y = tx['scale_y']
                draw_x = tx['draw_x']; draw_y = tx['draw_y']
                # If current pixmap already equals zoomed image (no letterbox), ignore draw offsets
                if current_pixmap.width() == tx['zoomed_width'] and current_pixmap.height() == tx['zoomed_height']:
                    offset_x = 0; offset_y = 0
                else:
                    offset_x = draw_x; offset_y = draw_y
                scaled_vertical = [int(x * scale_x) + offset_x for x in self.drawn_lines]
                scaled_horizontal = [int(y * scale_y) + offset_y for y in self.drawn_horizontal_lines]
                scaled_free = []
                for line in self.drawn_free_lines:
                    (sx, sy) = line['start']; (ex, ey) = line['end']
                    scaled_free.append({'start': (int(sx * scale_x) + offset_x, int(sy * scale_y) + offset_y),
                                        'end':   (int(ex * scale_x) + offset_x, int(ey * scale_y) + offset_y)})
                gpu_result = self.gpu_processor.draw_lines_gpu(
                    image,
                    scaled_vertical,
                    scaled_horizontal,
                    scaled_free,
                    self.line_color,
                    self.line_thickness
                )
                if gpu_result is not None:
                    # After GPU draw, verify free lines rendered; if none (possible off-screen), do CPU overlay pass
                    if self.drawn_free_lines:
                        overlay = gpu_result.copy()
                        painter = QPainter(overlay)
                        # Keep non-free lines non-antialiased for crispness and speed,
                        # but enable antialiasing for free-form lines for better visual quality.
                        painter.setPen(QPen(self.line_color, self.line_thickness, Qt.SolidLine))
                        painter.setRenderHint(QPainter.Antialiasing, True)
                        for line in self.drawn_free_lines:
                            (sx, sy) = line['start']; (ex, ey) = line['end']
                            painter.drawLine(int(sx * scale_x) + offset_x, int(sy * scale_y) + offset_y,
                                             int(ex * scale_x) + offset_x, int(ey * scale_y) + offset_y)
                        painter.end()
                        self.image_label.setPixmap(overlay)
                    else:
                        self.image_label.setPixmap(gpu_result)
                    return
            # CPU fallback: manually paint over current_pixmap copy
            overlay = current_pixmap.copy()
            painter = QPainter(overlay)
            # Default to no antialiasing (vertical/horizontal lines remain crisp).
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setPen(QPen(self.line_color, self.line_thickness, Qt.SolidLine))
            tx = self._compute_line_transform()
            if tx:
                scale_x = tx['scale_x']; scale_y = tx['scale_y']
                draw_x = tx['draw_x']; draw_y = tx['draw_y']
                if overlay.width() == tx['zoomed_width'] and overlay.height() == tx['zoomed_height']:
                    offset_x = 0; offset_y = 0
                else:
                    offset_x = draw_x; offset_y = draw_y
                
                # Get original size for transformation calculations
                original_size = self.original_pixmap.size() if hasattr(self, 'original_pixmap') and self.original_pixmap else QSize(1, 1)
                
                # Apply coordinate transformations based on rotation and flips
                if self.rotation_angle != 0 or self.flipped_h or self.flipped_v:
                    # Handle vertical lines with transformations
                    for x in self.drawn_lines:
                        # Apply flip transformations first
                        transformed_x = x
                        if self.flipped_h:
                            transformed_x = original_size.width() - x
                        
                        # Then apply rotation transformation
                        if self.rotation_angle == 90:
                            # Vertical line becomes horizontal
                            dy = int(transformed_x * scale_y) + offset_y
                            if 0 <= dy < overlay.height():
                                painter.drawLine(0, dy, overlay.width(), dy)
                        elif self.rotation_angle == 180:
                            # Vertical line stays vertical but position changes
                            final_x = original_size.width() - transformed_x
                            dx = int(final_x * scale_x) + offset_x
                            if 0 <= dx < overlay.width():
                                painter.drawLine(dx, 0, dx, overlay.height())
                        elif self.rotation_angle == 270:
                            # Vertical line becomes horizontal
                            final_y = original_size.height() - transformed_x
                            dy = int(final_y * scale_y) + offset_y
                            if 0 <= dy < overlay.height():
                                painter.drawLine(0, dy, overlay.width(), dy)
                        else:
                            # No rotation, just flips applied
                            dx = int(transformed_x * scale_x) + offset_x
                            if 0 <= dx < overlay.width():
                                painter.drawLine(dx, 0, dx, overlay.height())
                    
                    # Handle horizontal lines with transformations
                    for y in self.drawn_horizontal_lines:
                        # Apply flip transformations first
                        transformed_y = y
                        if self.flipped_v:
                            transformed_y = original_size.height() - y
                        
                        # Then apply rotation transformation
                        if self.rotation_angle == 90:
                            # Horizontal line becomes vertical
                            final_x = original_size.width() - transformed_y
                            dx = int(final_x * scale_x) + offset_x
                            if 0 <= dx < overlay.width():
                                painter.drawLine(dx, 0, dx, overlay.height())
                        elif self.rotation_angle == 180:
                            # Horizontal line stays horizontal but position changes
                            final_y = original_size.height() - transformed_y
                            dy = int(final_y * scale_y) + offset_y
                            if 0 <= dy < overlay.height():
                                painter.drawLine(0, dy, overlay.width(), dy)
                        elif self.rotation_angle == 270:
                            # Horizontal line becomes vertical
                            dx = int(transformed_y * scale_x) + offset_x
                            if 0 <= dx < overlay.width():
                                painter.drawLine(dx, 0, dx, overlay.height())
                        else:
                            # No rotation, just flips applied
                            dy = int(transformed_y * scale_y) + offset_y
                            if 0 <= dy < overlay.height():
                                painter.drawLine(0, dy, overlay.width(), dy)
                    
                    # Handle free lines with transformations
                    for line in self.drawn_free_lines:
                        start_x, start_y = line['start']
                        end_x, end_y = line['end']
                        
                        # Apply flip transformations first
                        flip_start_x = start_x if not self.flipped_h else original_size.width() - start_x
                        flip_start_y = start_y if not self.flipped_v else original_size.height() - start_y
                        flip_end_x = end_x if not self.flipped_h else original_size.width() - end_x
                        flip_end_y = end_y if not self.flipped_v else original_size.height() - end_y
                        
                        # Then apply rotation transformation
                        if self.rotation_angle == 90:
                            display_start_x = int((original_size.width() - flip_start_y) * scale_x) + offset_x
                            display_start_y = int(flip_start_x * scale_y) + offset_y
                            display_end_x = int((original_size.width() - flip_end_y) * scale_x) + offset_x
                            display_end_y = int(flip_end_x * scale_y) + offset_y
                        elif self.rotation_angle == 180:
                            display_start_x = int((original_size.width() - flip_start_x) * scale_x) + offset_x
                            display_start_y = int((original_size.height() - flip_start_y) * scale_y) + offset_y
                            display_end_x = int((original_size.width() - flip_end_x) * scale_x) + offset_x
                            display_end_y = int((original_size.height() - flip_end_y) * scale_y) + offset_y
                        elif self.rotation_angle == 270:
                            display_start_x = int(flip_start_y * scale_x) + offset_x
                            display_start_y = int((original_size.height() - flip_start_x) * scale_y) + offset_y
                            display_end_x = int(flip_end_y * scale_x) + offset_x
                            display_end_y = int((original_size.height() - flip_end_x) * scale_y) + offset_y
                        else:
                            # No rotation, just flips applied
                            display_start_x = int(flip_start_x * scale_x) + offset_x
                            display_start_y = int(flip_start_y * scale_y) + offset_y
                            display_end_x = int(flip_end_x * scale_x) + offset_x
                            display_end_y = int(flip_end_y * scale_y) + offset_y
                        
                        # Enable antialiasing for free-form lines for smoother appearance
                        painter.setRenderHint(QPainter.Antialiasing, True)
                        painter.drawLine(display_start_x, display_start_y, display_end_x, display_end_y)
                        painter.setRenderHint(QPainter.Antialiasing, False)
                else:
                    # No transformations needed - simple case
                    for x in self.drawn_lines:
                        dx = int(x * scale_x) + offset_x
                        if 0 <= dx < overlay.width():
                            painter.drawLine(dx, 0, dx, overlay.height())
                    for y in self.drawn_horizontal_lines:
                        dy = int(y * scale_y) + offset_y
                        if 0 <= dy < overlay.height():
                            painter.drawLine(0, dy, overlay.width(), dy)
                    for line in self.drawn_free_lines:
                        (sx, sy) = line['start']; (ex, ey) = line['end']
                        painter.drawLine(int(sx * scale_x) + offset_x, int(sy * scale_y) + offset_y,
                                         int(ex * scale_x) + offset_x, int(ey * scale_y) + offset_y)
            else:
                # Fallback simple proportional scaling when transform computation fails
                if hasattr(self, 'original_pixmap') and self.original_pixmap:
                    orig_w = self.original_pixmap.width(); orig_h = self.original_pixmap.height()
                    disp_w = current_pixmap.width(); disp_h = current_pixmap.height()
                    scale_x = disp_w / orig_w if orig_w else 1.0
                    scale_y = disp_h / orig_h if orig_h else 1.0
                else:
                    scale_x = scale_y = 1.0
                # Simple drawing without coordinate transformations (fallback)
                for x in self.drawn_lines:
                    dx = int(x * scale_x)
                    if 0 <= dx < overlay.width():
                        painter.drawLine(dx, 0, dx, overlay.height())
                for y in self.drawn_horizontal_lines:
                    dy = int(y * scale_y)
                    if 0 <= dy < overlay.height():
                        painter.drawLine(0, dy, overlay.width(), dy)
                for line in self.drawn_free_lines:
                    (sx, sy) = line['start']; (ex, ey) = line['end']
                    painter.drawLine(int(sx * scale_x), int(sy * scale_y), int(ex * scale_x), int(ey * scale_y))
            painter.end()
            self.image_label.setPixmap(overlay)
        except Exception as e:
            print(f"_fast_line_update failed: {e}; skipping line overlay to prevent loops")
            # DO NOT call display_image here as it can cause infinite loops with rotation + LUT
            # Instead, just skip the line overlay and let the current image display without lines
    # ...existing code...
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle("Random Image Viewer")
        self.setGeometry(100, 100, 950, 650)
        
        # Enable drag and drop for folders
        self.setAcceptDrops(True)
        
        self.folder = None
        self.images = []
        self.history = []
        self.current_image = None
        self.current_index = -1
        self.history_index = -1  # NEW: For navigation
        
        # Performance optimization: Cache management for large collections
        self.pixmap_cache = {}  # Cache for loaded pixmaps
        self.max_cache_size = 20  # Increased cache size for better performance with large collections
        self.scaled_cache = {}  # Cache for scaled versions
        self.last_size = None  # Track resize events
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._delayed_resize)
        self.resize_timer.setInterval(50)  # 50ms delay for resize debouncing
        
        # Line drawing functionality
        self.line_drawing_mode = False
        self.horizontal_line_drawing_mode = False
        self.free_line_drawing_mode = False  # New: Free line drawing mode
        self.drawn_lines = []  # List of x positions for vertical lines
        self.drawn_horizontal_lines = []  # List of y positions for horizontal lines
        self.drawn_free_lines = []  # List of free lines, each with start and end points
        self.current_line_start = None  # Store first click point for free line
        self.lines_visible = True  # New: Toggle line visibility
        self.line_thickness = 1
        self.line_color = QColor("#242424")  # Default white color for lines

        # Always on top functionality
        self.always_on_top = False

        # Fullscreen functionality
        self.is_fullscreen = False
        self.normal_geometry = None  # Store window geometry before fullscreen

        # Image enhancement parameters
        self.grayscale_value = 0  # 0 = color, 100 = full grayscale
        self.contrast_value = 50  # 50 = normal, -130 to 200 range
        self.gamma_value = 0     # 0 = normal, -200 to +500 range
        self.rotation_angle = 0   # Rotation angle in degrees
        self.flipped_h = False    # Horizontal flip state
        self.flipped_v = False    # Vertical flip state
        self.original_pixmap = None  # Cache original image for fast processing
        self.enhancement_cache = {}  # Cache enhanced versions
        
        # LUT (Look-Up Table) support
        self.current_lut = None   # Currently loaded LUT data
        self.current_lut_name = "None"  # Name of current LUT
        self.lut_folder = None    # Folder containing CUBE LUT files
        self.lut_files = []       # List of available LUT files
        self.lut_strength = 100   # LUT application strength (0-100%)
        self.lut_cache = {}       # Cache for loaded LUTs to avoid reloading
        # Separate enable flag so a selected LUT can be temporarily disabled without clearing selection
        self.lut_enabled = False
        # Track whether cached last processed image contained LUT so we don't reuse it when disabled
        self._last_processed_has_lut = False
        
        # GPU acceleration
        self.gpu_processor = GPULutProcessor()
        # Force complete reinitialization to use corrected kernels
        self.gpu_processor._force_reinit = True
        # Also clear any cached kernels to ensure clean reload
        self.gpu_processor._kernel_cache = {}
        print(f"GPU Status: {self.gpu_processor.get_device_info()}")
        print("TEST: Changed LUT indexing from RGB to BGR order")

        self.timer_interval = 60  # seconds
        self.timer_remaining = 0
        self._auto_advance_active = False
        self._timer_paused = False  # NEW: Timer pause state

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        
        # Sorting mode for navigation
        self.random_mode = True  # Default to random mode
        
        # Store original window flags for UI toggle
        self.original_window_flags = None
        
        # Window dragging and resizing for frameless mode
        self.dragging = False
        self.drag_start_position = None
        self.resizing = False
        self.resize_edge = None
        self.resize_margin = 10  # Pixel margin for resize detection
        self.timer.timeout.connect(self._on_timer_tick)

        self.init_ui()
        # Set initial window geometry (width 885 triggers two-row layout below threshold 900)
        try:
            self.resize(885, 700)
        except Exception as _e:
            pass
        
        # Store original window flags for UI toggle functionality
        self.original_window_flags = self.windowFlags()
        
        # Force layout evaluation after initial resize
        QTimer.singleShot(0, self._delayed_resize)
        # Auto-set default LUT folder if present
        # NOTE: trailing backslash in a raw string would escape the quote -> syntax error
        self.default_lut_path = r"L:\_ART\LUTS"
        if os.path.isdir(self.default_lut_path):
            self.lut_folder = self.default_lut_path
            try:
                self.lut_files = self.scan_lut_folder(self.default_lut_path)
                if hasattr(self, 'lut_combo') and self.lut_files:
                    # Populate combo if empty
                    self.lut_combo.clear()
                    self.lut_combo.addItem("None")
                    for lut_file in self.lut_files:
                        rel = os.path.relpath(lut_file, self.lut_folder)
                        self.lut_combo.addItem(rel)
                    self.current_lut_name = "None"
                print(f"Default LUT folder loaded: {self.default_lut_path} ({len(self.lut_files)} files)")
            except Exception as e:
                print(f"Failed loading default LUT folder {self.default_lut_path}: {e}")

    def init_ui(self):
        # Create main toolbar
        self.main_toolbar = QToolBar("Main Toolbar")
        self.main_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.TopToolBarArea, self.main_toolbar)
        self.main_toolbar.setMovable(False)
        self.main_toolbar.setStyleSheet("QToolBar { spacing: 4px; }")

        # Force a toolbar break to ensure next toolbar goes on new line
        self.addToolBarBreak(Qt.TopToolBarArea)
        
        # Create secondary toolbar for sliders (initially hidden) - this will be BELOW main toolbar
        self.slider_toolbar = QToolBar("Slider Toolbar")
        self.slider_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.TopToolBarArea, self.slider_toolbar)
        self.slider_toolbar.setMovable(False)
        self.slider_toolbar.setStyleSheet("QToolBar { spacing: 4px; background: #2a2d30; border-top: 1px solid #35383b; }")
        self.slider_toolbar.setMinimumHeight(32)  # Ensure minimum height
        self.slider_toolbar.setMaximumHeight(40)  # Set reasonable max height
        self.slider_toolbar.hide()

        # Track which mode we're in
        self.two_row_mode = False
        self.width_threshold = 900  # Increased threshold - switch to two rows below this width

        # Setup main toolbar with all controls
        self._setup_main_toolbar()
        
        # Setup enhancement controls on BOTH toolbars permanently
        self._setup_enhancement_controls()

        # Central widget and layout setup
        central_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(central_splitter)

        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(6, 6, 6, 6)

        self.image_label = ImageLabel("Open a folder to start")
        self.image_label.parent_viewer = self
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setToolTip("")

        image_layout.addWidget(self.image_label)
        image_widget.setLayout(image_layout)
        central_splitter.addWidget(image_widget)

        self.history_list = QListWidget()
        self.history_list.setMaximumWidth(180)
        self.history_list.itemClicked.connect(self.on_history_clicked)
        self.history_list.hide()
        central_splitter.addWidget(self.history_list)
        central_splitter.setSizes([900, 100])

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.path_label = QLabel()

        self.statusBar().addPermanentWidget(self.path_label)
        self.path_label.linkActivated.connect(self.open_in_explorer)

        self.update_image_info()
        self._update_title()
        
        # Add global shortcuts that bypass normal event handling
        self.setup_global_shortcuts()
        
        # Initialize toggle button states
        self._update_enhancement_menu_states()
        if hasattr(self, 'grayscale_toggle_btn'):
            self.grayscale_toggle_btn.setChecked(self.grayscale_value > 0)
        if hasattr(self, 'contrast_toggle_btn'):
            self.contrast_toggle_btn.setChecked(self.contrast_value != 50)
        if hasattr(self, 'gamma_toggle_btn'):
            self.gamma_toggle_btn.setChecked(self.gamma_value != 0)

    def setup_global_shortcuts(self):
        """Setup global shortcuts that work even when focus is elsewhere"""
        print("Setting up global shortcuts...")
        
        # Emergency exit fullscreen shortcuts
        self.escape_shortcut = QShortcut("Esc", self)
        self.escape_shortcut.activated.connect(self.emergency_exit_fullscreen)
        
        self.f11_shortcut = QShortcut("F11", self)
        self.f11_shortcut.activated.connect(self.emergency_toggle_fullscreen)
        
        self.ctrl_esc_shortcut = QShortcut("Ctrl+Esc", self)
        self.ctrl_esc_shortcut.activated.connect(self.force_exit_fullscreen)
        
        # Alt+F4 as ultimate emergency exit
        self.alt_f4_shortcut = QShortcut("Alt+F4", self)
        self.alt_f4_shortcut.activated.connect(self.emergency_close)
        
        # Essential application shortcuts
        self.ctrl_o_shortcut = QShortcut("Ctrl+O", self)
        self.ctrl_o_shortcut.activated.connect(self.choose_folder)
        
        self.ctrl_r_shortcut = QShortcut("Ctrl+R", self)
        self.ctrl_r_shortcut.activated.connect(self.reset_enhancements)
        
        # Zoom shortcuts
        self.ctrl_plus_shortcut = QShortcut("Ctrl++", self)
        self.ctrl_plus_shortcut.activated.connect(self.zoom_in)
        
        self.ctrl_minus_shortcut = QShortcut("Ctrl+-", self)
        self.ctrl_minus_shortcut.activated.connect(self.zoom_out)
        
        self.ctrl_0_shortcut = QShortcut("Ctrl+0", self)
        self.ctrl_0_shortcut.activated.connect(self.reset_zoom)
        
        print("Global shortcuts set up successfully")

    def emergency_exit_fullscreen(self):
        """Emergency exit from fullscreen or minimal mode"""
        print("EMERGENCY: Escape shortcut activated")
        if self.is_fullscreen:
            self.force_exit_fullscreen()
        elif not self.main_toolbar.isVisible():
            print("EMERGENCY: Restoring UI from minimal mode")
            self.toggle_toolbar_visibility(True)  # Show UI

    def emergency_toggle_fullscreen(self):
        """Emergency toggle fullscreen"""
        print("EMERGENCY: F11 shortcut activated")
        if self.is_fullscreen:
            self.force_exit_fullscreen()
        else:
            self.toggle_fullscreen(True)

    def emergency_close(self):
        """Emergency close application"""
        print("EMERGENCY: Alt+F4 activated - closing application")
        self.close()

    def _setup_main_toolbar(self):
        toolbar = self.main_toolbar

        def add_spacer(width):
            s = QWidget(); s.setFixedWidth(width); toolbar.addWidget(s)

        # Open folder
        open_btn = QToolButton(); open_btn.setText("📁"); open_btn.setToolTip("Open Folder"); open_btn.setFixedSize(24,24); open_btn.clicked.connect(self.choose_folder); toolbar.addWidget(open_btn)
        add_spacer(4)

        # Line tools
        self.line_tool_btn = QToolButton(); self.line_tool_btn.setText("📏"); self.line_tool_btn.setToolTip("Draw Vertical Lines"); self.line_tool_btn.setCheckable(True); self.line_tool_btn.setFixedSize(24,24); self.line_tool_btn.toggled.connect(self.toggle_line_drawing); toolbar.addWidget(self.line_tool_btn)
        add_spacer(4)
        self.hline_tool_btn = QToolButton(); self.hline_tool_btn.setText("━"); self.hline_tool_btn.setToolTip("Draw Horizontal Lines"); self.hline_tool_btn.setCheckable(True); self.hline_tool_btn.setFixedSize(24,24); self.hline_tool_btn.toggled.connect(self.toggle_hline_drawing); toolbar.addWidget(self.hline_tool_btn)
        add_spacer(4)
        self.free_line_tool_btn = QToolButton(); self.free_line_tool_btn.setText("╱"); self.free_line_tool_btn.setToolTip("Draw Free Lines (2 clicks per line)"); self.free_line_tool_btn.setCheckable(True); self.free_line_tool_btn.setFixedSize(24,24); self.free_line_tool_btn.toggled.connect(self.toggle_free_line_drawing); toolbar.addWidget(self.free_line_tool_btn)
        add_spacer(4)
        self.undo_line_btn = QToolButton(); self.undo_line_btn.setText("↶"); self.undo_line_btn.setToolTip("Undo Last Line"); self.undo_line_btn.setFixedSize(24,24); self.undo_line_btn.clicked.connect(self.undo_last_line); toolbar.addWidget(self.undo_line_btn)
        add_spacer(4)
        self.line_thickness_spin = QSpinBox(); self.line_thickness_spin.setRange(1,10); self.line_thickness_spin.setValue(self.line_thickness); self.line_thickness_spin.setSuffix("px"); self.line_thickness_spin.setFixedHeight(24); self.line_thickness_spin.setFixedWidth(50); self.line_thickness_spin.setToolTip("Line Thickness"); self.line_thickness_spin.valueChanged.connect(self.update_line_thickness); toolbar.addWidget(self.line_thickness_spin)
        add_spacer(4)
        self.line_color_btn = QToolButton(); self.line_color_btn.setText("🎨"); self.line_color_btn.setToolTip("Choose Line Color"); self.line_color_btn.setFixedSize(24,24); self.line_color_btn.clicked.connect(self.choose_line_color); self.line_color_btn.setStyleSheet(f"QToolButton {{ background-color: {self.line_color.name()}; border:1px solid #666; }}"); toolbar.addWidget(self.line_color_btn)
        for color_hex, color_name, emoji in [("#ffffff","White","⚪"),("#000000","Black","⚫"),("#808080","Grey","⚪")]:
            btn=QToolButton(); btn.setText(emoji); btn.setToolTip(f"Set Line Color to {color_name}"); btn.setFixedSize(18,24); btn.clicked.connect(lambda checked, c=color_hex: self.set_line_color(c)); btn.setStyleSheet("QToolButton { border:1px solid #444; margin:1px; }"); toolbar.addWidget(btn)
        add_spacer(4)
        clear_lines_btn = QToolButton(); clear_lines_btn.setText("🗑"); clear_lines_btn.setToolTip("Clear All Lines"); clear_lines_btn.setFixedSize(24,24); clear_lines_btn.clicked.connect(self.clear_lines); toolbar.addWidget(clear_lines_btn)
        add_spacer(4)
        self.toggle_lines_btn = QToolButton(); self.toggle_lines_btn.setText("👁"); self.toggle_lines_btn.setToolTip("Toggle Line Visibility On/Off"); self.toggle_lines_btn.setCheckable(True); self.toggle_lines_btn.setChecked(True); self.toggle_lines_btn.setFixedSize(24,24); self.toggle_lines_btn.toggled.connect(self.toggle_line_visibility); toolbar.addWidget(self.toggle_lines_btn)
        add_spacer(8)
        # Enhancement toggles
        self.grayscale_toggle_btn = QToolButton(); self.grayscale_toggle_btn.setText("🌑"); self.grayscale_toggle_btn.setToolTip("Toggle Grayscale On/Off"); self.grayscale_toggle_btn.setCheckable(True); self.grayscale_toggle_btn.setFixedSize(24,24); self.grayscale_toggle_btn.toggled.connect(self.toggle_grayscale); toolbar.addWidget(self.grayscale_toggle_btn)
        add_spacer(4)
        self.contrast_toggle_btn = QToolButton(); self.contrast_toggle_btn.setText("🔆"); self.contrast_toggle_btn.setToolTip("Toggle Enhanced Contrast On/Off"); self.contrast_toggle_btn.setCheckable(True); self.contrast_toggle_btn.setFixedSize(24,24); self.contrast_toggle_btn.toggled.connect(self.toggle_contrast); toolbar.addWidget(self.contrast_toggle_btn)
        add_spacer(4)
        self.gamma_toggle_btn = QToolButton(); self.gamma_toggle_btn.setText("💡"); self.gamma_toggle_btn.setToolTip("Toggle Enhanced Brightness On/Off"); self.gamma_toggle_btn.setCheckable(True); self.gamma_toggle_btn.setFixedSize(24,24); self.gamma_toggle_btn.toggled.connect(self.toggle_gamma); toolbar.addWidget(self.gamma_toggle_btn)
        # LUT toggle
        self.lut_toggle_btn = QToolButton(); self.lut_toggle_btn.setText("🎞"); self.lut_toggle_btn.setToolTip("Toggle LUT On/Off (preserves selection)"); self.lut_toggle_btn.setCheckable(True); self.lut_toggle_btn.setFixedSize(24,24); self.lut_toggle_btn.toggled.connect(self.toggle_lut_enabled); self.lut_toggle_btn.setChecked(False); toolbar.addWidget(self.lut_toggle_btn)
        add_spacer(8)
        # Navigation & timer
        prev_btn = QToolButton(); prev_btn.setText("⬅"); prev_btn.setToolTip("Previous Image (Go Back in History)"); prev_btn.setFixedSize(24,24); prev_btn.clicked.connect(self.show_previous_image); toolbar.addWidget(prev_btn)
        add_spacer(4)
        next_btn = QToolButton(); next_btn.setText("🎲"); next_btn.setToolTip("Show Next Image"); next_btn.setFixedSize(24,24); next_btn.clicked.connect(self._manual_next_image); toolbar.addWidget(next_btn)
        add_spacer(4)
        # Sort order toggle
        self.sort_order_button = QToolButton(); self.sort_order_button.setCheckable(True); self.sort_order_button.setChecked(True); self.sort_order_button.setText("🔀"); self.sort_order_button.setToolTip("Toggle Random/Alphabetical Order"); self.sort_order_button.setFixedSize(24,24); self.sort_order_button.toggled.connect(self.toggle_sort_order); toolbar.addWidget(self.sort_order_button)
        add_spacer(4)
        self.timer_button = QToolButton(); self.timer_button.setCheckable(True); self.timer_button.setText("⚡"); self.timer_button.setToolTip("Toggle Auto Advance"); self.timer_button.setFixedSize(24,24); self.timer_button.toggled.connect(self.toggle_timer); toolbar.addWidget(self.timer_button)
        add_spacer(4)
        self.timer_spin = QSpinBox(); self.timer_spin.setRange(1,3600); self.timer_spin.setValue(self.timer_interval); self.timer_spin.setSuffix(" s"); self.timer_spin.setFixedHeight(24); self.timer_spin.setFixedWidth(60); self.timer_spin.valueChanged.connect(self.update_timer_interval); toolbar.addWidget(self.timer_spin)
        add_spacer(4)
        self.circle_timer = CircularCountdown(self.timer_spin.value()); self.circle_timer.set_parent_viewer(self); toolbar.addWidget(self.circle_timer)
        add_spacer(4)
        # Save current view button
        save_btn = QToolButton(); save_btn.setText("💾"); save_btn.setToolTip("Save current view (includes LUT, enhancements and lines)"); save_btn.setFixedSize(24,24); save_btn.clicked.connect(self.save_current_view); toolbar.addWidget(save_btn)
        add_spacer(6)

    def _setup_enhancement_controls(self):
        """Setup the enhancement controls - put them on main toolbar initially"""
        # Add a separator before enhancement controls for easy identification
        self.enhancement_separator = self.main_toolbar.addSeparator()
        
        # Create enhancement controls on the main toolbar initially
        self._create_enhancement_widgets_on_toolbar(self.main_toolbar)
        
        # Add action buttons to the main toolbar initially
        self._add_action_buttons_to_toolbar(self.main_toolbar)

        # History checkbox on main toolbar
        self.show_history_checkbox = QCheckBox("History")
        self.show_history_checkbox.setChecked(False)
        self.show_history_checkbox.setFixedHeight(24)
        self.show_history_checkbox.stateChanged.connect(self.toggle_history_panel)
        self.main_toolbar.addWidget(self.show_history_checkbox)

        # Add stretch to push everything to the left
        spacer_stretch = QWidget()
        spacer_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main_toolbar.addWidget(spacer_stretch)

    def _update_toolbar_layout(self, width):
        """Move sliders between main toolbar and second row based on window width"""
        should_use_two_rows = width < self.width_threshold
        
        # Only switch if the mode actually needs to change
        if should_use_two_rows == self.two_row_mode:
            return
        
        if should_use_two_rows and not self.two_row_mode:
            print(f"Switching to two-row mode at width {width}")
            
            # Store current slider values and history checkbox state
            gray_val = getattr(self, 'grayscale_slider', None)
            gray_val = gray_val.value() if gray_val else self.grayscale_value
            contrast_val = getattr(self, 'contrast_slider', None)
            contrast_val = contrast_val.value() if contrast_val else self.contrast_value
            gamma_val = getattr(self, 'gamma_slider', None)
            gamma_val = gamma_val.value() if gamma_val else self.gamma_value
            history_checked = getattr(self, 'show_history_checkbox', None)
            history_checked = history_checked.isChecked() if history_checked else False
            
            # Store LUT settings before recreating controls
            lut_strength_val = getattr(self, 'lut_strength_slider', None)
            lut_strength_val = lut_strength_val.value() if lut_strength_val else self.lut_strength
            current_lut_selection = getattr(self, 'lut_combo', None)
            current_lut_selection = current_lut_selection.currentText() if current_lut_selection else "None"
            
            # Find and remove enhancement widgets AND action buttons from main toolbar
            actions_to_remove = []
            found_separator = False
            
            for action in self.main_toolbar.actions():
                if hasattr(self, 'enhancement_separator') and action == self.enhancement_separator:
                    found_separator = True
                    actions_to_remove.append(action)
                elif found_separator:
                    actions_to_remove.append(action)
            
            # Remove the actions
            for action in actions_to_remove:
                self.main_toolbar.removeAction(action)
            
            # Clear and setup slider toolbar with both sliders and action buttons
            self.slider_toolbar.clear()
            self._create_enhancement_widgets_on_toolbar(self.slider_toolbar)
            
            # Add spacer before action buttons
            spacer_before_actions = QWidget()
            spacer_before_actions.setFixedWidth(12)
            self.slider_toolbar.addWidget(spacer_before_actions)
            
            # Add action buttons to second toolbar
            self._add_action_buttons_to_toolbar(self.slider_toolbar)
            
            # Restore slider values
            if hasattr(self, 'grayscale_slider'):
                self.grayscale_slider.setValue(gray_val)
                self.contrast_slider.setValue(contrast_val)
                self.gamma_slider.setValue(gamma_val)
            if hasattr(self, 'lut_strength_slider'):
                self.lut_strength_slider.setValue(lut_strength_val)
            
            # Restore LUT selection after recreating combo box
            if hasattr(self, 'lut_combo'):
                # Always populate the combo box if we have a folder selected
                if self.lut_folder and self.lut_files:
                    self.update_lut_combo()
                    # Then restore the selection if there was one
                    if current_lut_selection != "None":
                        index = self.lut_combo.findText(current_lut_selection)
                        if index >= 0:
                            self.lut_combo.setCurrentIndex(index)
            
            # Add History checkbox to slider toolbar
            spacer_before_history = QWidget()
            spacer_before_history.setFixedWidth(8)
            self.slider_toolbar.addWidget(spacer_before_history)
            
            self.show_history_checkbox = QCheckBox("History")
            self.show_history_checkbox.setChecked(history_checked)
            self.show_history_checkbox.setFixedHeight(24)
            self.show_history_checkbox.stateChanged.connect(self.toggle_history_panel)
            self.slider_toolbar.addWidget(self.show_history_checkbox)
            
            # Show second toolbar and update mode
            self.slider_toolbar.show()
            self.two_row_mode = True
            print("DEBUG: Second toolbar should now be visible")
            print(f"DEBUG: Slider toolbar visible: {self.slider_toolbar.isVisible()}")
            print(f"DEBUG: Slider toolbar widget count: {len([self.slider_toolbar.widgetForAction(a) for a in self.slider_toolbar.actions() if self.slider_toolbar.widgetForAction(a)])}")
            
            # Force update the UI
            self.slider_toolbar.update()
            self.repaint()
            
        elif not should_use_two_rows and self.two_row_mode:
            print(f"Switching to single-row mode at width {width}")
            
            # Store current values
            gray_val = getattr(self, 'grayscale_slider', None)
            gray_val = gray_val.value() if gray_val else self.grayscale_value
            contrast_val = getattr(self, 'contrast_slider', None)
            contrast_val = contrast_val.value() if contrast_val else self.contrast_value
            gamma_val = getattr(self, 'gamma_slider', None)
            gamma_val = gamma_val.value() if gamma_val else self.gamma_value
            history_checked = getattr(self, 'show_history_checkbox', None)
            history_checked = history_checked.isChecked() if history_checked else False
            
            # Store LUT settings before recreating controls
            lut_strength_val = getattr(self, 'lut_strength_slider', None)
            lut_strength_val = lut_strength_val.value() if lut_strength_val else self.lut_strength
            current_lut_selection = getattr(self, 'lut_combo', None)
            current_lut_selection = current_lut_selection.currentText() if current_lut_selection else "None"
            
            # Clear and hide slider toolbar
            self.slider_toolbar.clear()
            self.slider_toolbar.hide()
            
            # Re-add enhancement separator to main toolbar
            self.enhancement_separator = self.main_toolbar.addSeparator()
            
            # Add enhancement controls back to main toolbar
            self._create_enhancement_widgets_on_toolbar(self.main_toolbar)
            
            # Add action buttons back to main toolbar
            self._add_action_buttons_to_toolbar(self.main_toolbar)
            
            # Restore values
            if hasattr(self, 'grayscale_slider'):
                self.grayscale_slider.setValue(gray_val)
                self.contrast_slider.setValue(contrast_val)
                self.gamma_slider.setValue(gamma_val)
            
            # Restore LUT settings
            if hasattr(self, 'lut_strength_slider'):
                self.lut_strength_slider.setValue(lut_strength_val)
            
            # Restore LUT folder and selection
            if hasattr(self, 'lut_combo') and self.lut_folder:
                self.update_lut_combo()  # Repopulate combo box with current folder
                # Find and restore the previous selection
                combo_index = self.lut_combo.findText(current_lut_selection)
                if combo_index >= 0:
                    self.lut_combo.setCurrentIndex(combo_index)
                    # Ensure LUT is applied if one was selected
                    if current_lut_selection != "None":
                        self.apply_selected_lut(current_lut_selection)
            
            # Add History checkbox back to main toolbar
            self.show_history_checkbox = QCheckBox("History")
            self.show_history_checkbox.setChecked(history_checked)
            self.show_history_checkbox.setFixedHeight(24)
            self.show_history_checkbox.stateChanged.connect(self.toggle_history_panel)
            self.main_toolbar.addWidget(self.show_history_checkbox)
            
            # Add stretch to main toolbar
            spacer_stretch = QWidget()
            spacer_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.main_toolbar.addWidget(spacer_stretch)
            
            self.two_row_mode = False
            print("DEBUG: Returned to single-row mode")

    def _add_action_buttons_to_toolbar(self, toolbar):
        """Add action buttons (reset zoom, rotate, flip, etc.) to the specified toolbar"""
        # Reset zoom button
        self.reset_zoom_btn = QToolButton()
        self.reset_zoom_btn.setText("🔄")
        self.reset_zoom_btn.setToolTip("Reset Zoom to 100%")
        self.reset_zoom_btn.setFixedSize(24, 24)
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        toolbar.addWidget(self.reset_zoom_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Rotate 90 degrees button
        self.rotate_btn = QToolButton()
        self.rotate_btn.setText("↻")
        self.rotate_btn.setToolTip("Rotate Image 90 degrees")
        self.rotate_btn.setFixedSize(24, 24)
        self.rotate_btn.clicked.connect(self.rotate_image_90)
        toolbar.addWidget(self.rotate_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Flip horizontal button
        self.flip_h_btn = QToolButton()
        self.flip_h_btn.setText("⟷")
        self.flip_h_btn.setToolTip("Flip Image Horizontally")
        self.flip_h_btn.setCheckable(True)
        self.flip_h_btn.setFixedSize(24, 24)
        self.flip_h_btn.clicked.connect(self.flip_horizontal)
        toolbar.addWidget(self.flip_h_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Flip vertical button
        self.flip_v_btn = QToolButton()
        self.flip_v_btn.setText("↕")
        self.flip_v_btn.setToolTip("Flip Image Vertically")
        self.flip_v_btn.setCheckable(True)
        self.flip_v_btn.setFixedSize(24, 24)
        self.flip_v_btn.clicked.connect(self.flip_vertical)
        toolbar.addWidget(self.flip_v_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Copy to clipboard button
        self.copy_btn = QToolButton()
        self.copy_btn.setText("📋")
        self.copy_btn.setToolTip("Copy Current Image to Clipboard (with lines and enhancements)")
        self.copy_btn.setFixedSize(24, 24)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        toolbar.addWidget(self.copy_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Fullscreen button
        self.fullscreen_btn = QToolButton()
        self.fullscreen_btn.setText("⛶")
        self.fullscreen_btn.setToolTip("Toggle Fullscreen (F11)")
        self.fullscreen_btn.setCheckable(True)
        self.fullscreen_btn.setFixedSize(24, 24)
        self.fullscreen_btn.toggled.connect(self.toggle_fullscreen)
        toolbar.addWidget(self.fullscreen_btn)

        toolbar.addSeparator()

        # Always on top button
        self.always_on_top_btn = QToolButton()
        self.always_on_top_btn.setText("📌")
        self.always_on_top_btn.setToolTip("Always on Top")
        self.always_on_top_btn.setCheckable(True)
        self.always_on_top_btn.setFixedSize(24, 24)
        self.always_on_top_btn.toggled.connect(self.toggle_always_on_top)
        toolbar.addWidget(self.always_on_top_btn)

    def _create_enhancement_widgets_on_toolbar(self, toolbar):
        """Create enhancement widgets on the specified toolbar"""
        # Add some spacing before the enhancement controls
        spacer_start = QWidget()
        spacer_start.setFixedWidth(8)
        toolbar.addWidget(spacer_start)
        
        # Grayscale slider
        gray_label = QLabel("Gray:")
        gray_label.setFixedWidth(30)
        gray_label.setStyleSheet("font-size: 9px; margin-right: 2px;")
        toolbar.addWidget(gray_label)
        
        self.grayscale_slider = ClickableSlider(Qt.Horizontal)
        self.grayscale_slider.setRange(0, 100)
        self.grayscale_slider.setValue(self.grayscale_value)
        self.grayscale_slider.setFixedWidth(70)  # Increased width for easier clicking
        self.grayscale_slider.setFixedHeight(24)  # Increased height for easier clicking
        self.grayscale_slider.setStyleSheet("QSlider { margin: 2px 4px; }")  # Add margins around slider
        self.grayscale_slider.setToolTip("Grayscale: 0=Color, 100=B&W")
        self.grayscale_slider.valueChanged.connect(self.update_grayscale)
        toolbar.addWidget(self.grayscale_slider)

        # Small spacer between sliders
        spacer1 = QWidget()
        spacer1.setFixedWidth(4)
        toolbar.addWidget(spacer1)

        # Contrast slider
        contrast_label = QLabel("Con:")
        contrast_label.setFixedWidth(25)
        contrast_label.setStyleSheet("font-size: 9px; margin-right: 2px;")
        toolbar.addWidget(contrast_label)
        
        self.contrast_slider = ClickableSlider(Qt.Horizontal)
        self.contrast_slider.setRange(-130, 200)
        self.contrast_slider.setValue(self.contrast_value)
        self.contrast_slider.setFixedWidth(70)  # Increased width for easier clicking
        self.contrast_slider.setFixedHeight(24)  # Increased height for easier clicking
        self.contrast_slider.setStyleSheet("QSlider { margin: 2px 4px; }")  # Add margins around slider
        self.contrast_slider.setToolTip("Contrast: 50=Normal, -130=Grey, 200=Extreme")
        self.contrast_slider.valueChanged.connect(self.update_contrast)
        toolbar.addWidget(self.contrast_slider)

        # Small spacer between sliders
        spacer2 = QWidget()
        spacer2.setFixedWidth(4)
        toolbar.addWidget(spacer2)

        # Gamma slider
        gamma_label = QLabel("Gam:")
        gamma_label.setFixedWidth(25)
        gamma_label.setStyleSheet("font-size: 9px; margin-right: 2px;")
        toolbar.addWidget(gamma_label)
        
        self.gamma_slider = ClickableSlider(Qt.Horizontal)
        self.gamma_slider.setRange(-200, 500)  # New range: -200=very dark, 0=normal, 500=very bright
        self.gamma_slider.setValue(self.gamma_value)
        self.gamma_slider.setFixedWidth(70)  # Increased width for easier clicking
        self.gamma_slider.setFixedHeight(24)  # Increased height for easier clicking
        self.gamma_slider.setStyleSheet("QSlider { margin: 2px 4px; }")  # Add margins around slider
        self.gamma_slider.setToolTip("Gamma: -200=Very Dark, 0=Normal, 500=Very Bright")
        self.gamma_slider.valueChanged.connect(self.update_gamma)
        toolbar.addWidget(self.gamma_slider)

        # Small spacer between sliders
        spacer3 = QWidget()
        spacer3.setFixedWidth(4)
        toolbar.addWidget(spacer3)

        # LUT controls
        lut_label = QLabel("LUT:")
        lut_label.setFixedWidth(25)
        lut_label.setStyleSheet("font-size: 9px; margin-right: 2px;")
        toolbar.addWidget(lut_label)
        
        # LUT selection button
        self.lut_btn = QToolButton()
        self.lut_btn.setText("📁")
        self.lut_btn.setToolTip("Select LUT Folder")
        self.lut_btn.setFixedSize(20, 24)
        self.lut_btn.clicked.connect(self.choose_lut_folder)
        toolbar.addWidget(self.lut_btn)
        
        # LUT dropdown (combo box)
        self.lut_combo = QComboBox()
        self.lut_combo.addItem("None")
        self.lut_combo.setFixedWidth(80)
        self.lut_combo.setFixedHeight(24)
        self.lut_combo.setToolTip("Select LUT")
        # Style the dropdown to be wider when opened
        self.lut_combo.setStyleSheet("""
            QComboBox {
                min-width: 80px;
            }
            QComboBox QAbstractItemView {
                min-width: 200px;
                max-width: 300px;
            }
        """)
        self.lut_combo.currentTextChanged.connect(self.apply_selected_lut)
        toolbar.addWidget(self.lut_combo)
        
        # LUT strength slider
        self.lut_strength_slider = ClickableSlider(Qt.Horizontal)
        self.lut_strength_slider.setRange(0, 100)
        self.lut_strength_slider.setValue(self.lut_strength)
        self.lut_strength_slider.setFixedWidth(50)
        self.lut_strength_slider.setFixedHeight(24)
        self.lut_strength_slider.setStyleSheet("QSlider { margin: 2px 4px; }")
        self.lut_strength_slider.setToolTip("LUT Strength: 0=Off, 100=Full")
        self.lut_strength_slider.valueChanged.connect(self.update_lut_strength)
        toolbar.addWidget(self.lut_strength_slider)

        # Small spacer before reset button
        spacer4 = QWidget()
        toolbar.addWidget(spacer4)

        # Reset button
        reset_btn = QToolButton()
        reset_btn.setText("↺")
        reset_btn.setToolTip("Reset Enhancements")
        reset_btn.setFixedSize(20, 24)  # Slightly larger for easier clicking
        reset_btn.setStyleSheet("QToolButton { margin: 2px; }")  # Add margin around button
        reset_btn.clicked.connect(self.reset_enhancements)
        toolbar.addWidget(reset_btn)

    def _update_title(self):
        count = len(self.images)
        folder_name = os.path.basename(self.folder) if self.folder else ""
        self.setWindowTitle(f"Random Image Viewer - {folder_name} ({count} images found)")

    def update_image_info(self, img_path=None):
        if img_path is None or not os.path.exists(img_path):
            self.status.showMessage("")
            return
        base = os.path.basename(img_path)
        
        # Use safe loading for image info
        pixmap, error = safe_load_pixmap(img_path)
        if error:
            info = f"{base} - {error}"
        elif not pixmap.isNull():
            file_size_mb = get_image_file_size(img_path)
            if file_size_mb > 10:  # Show file size for large files
                info = f"{base} – {pixmap.width()}x{pixmap.height()} ({file_size_mb:.1f} MB)"
            else:
                info = f"{base} – {pixmap.width()}x{pixmap.height()}"
        else:
            info = base
        self.status.showMessage(info)

    def show_random_image(self):
        try:
            if not self.images:
                return
            # Clear lines when showing a new random image
            self.drawn_lines.clear()
            self.drawn_horizontal_lines.clear()
            self.drawn_free_lines.clear()
            self.current_line_start = None
            # Reset rotation angle and flips for new image
            self.rotation_angle = 0
            self.flipped_h = False
            self.flipped_v = False
            # Reset button states safely
            if hasattr(self, 'flip_h_btn') and self.flip_h_btn is not None:
                self.flip_h_btn.setChecked(False)
            if hasattr(self, 'flip_v_btn') and self.flip_v_btn is not None:
                self.flip_v_btn.setChecked(False)
            available = [img for img in self.images if img not in self.history]
            if not available:
                self.history.clear()
                self.history_list.clear()
                available = self.images[:]
            img_path = random.choice(available)
            self._display_image_with_lut_preview(img_path)
            self.add_to_history(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()
        except Exception as e:
            print(f"Error in show_random_image: {e}")
            # Don't let the error crash the app, just log it
            import traceback
            traceback.print_exc()

    def _manual_next_image(self):
        if not self.images:
            return

        if self.random_mode:
            self.show_random_image()
        else:
            # Sequential mode
            if self.current_image and self.current_image in self.images:
                try:
                    current_list_index = self.images.index(self.current_image)
                    next_index = (current_list_index + 1) % len(self.images)
                except ValueError:
                    next_index = 0
            else:
                next_index = 0
            
            img_path = self.images[next_index]
            self._display_image_with_lut_preview(img_path)
            self.add_to_history(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()

    def display_image(self, img_path):
        # Clear LUT processing cache when changing images to prevent memory buildup
        if hasattr(self, 'current_image') and self.current_image != img_path:
            self.clear_lut_cache()
        
        # Create cache key including enhancement settings, rotation, and flips
        cache_key = f"{img_path}_{self.grayscale_value}_{self.contrast_value}_{self.gamma_value}_{self.rotation_angle}_{self.flipped_h}_{self.flipped_v}_{self.current_lut_name}_{self.lut_strength}"
        
        # Check enhanced cache first
        if cache_key in self.enhancement_cache:
            pixmap = self.enhancement_cache[cache_key]
        else:
            # Check base pixmap cache
            if img_path in self.pixmap_cache:
                base_pixmap = self.pixmap_cache[img_path]
            else:
                base_pixmap, error = safe_load_pixmap(img_path)
                if error:
                    self.image_label.setText(error)
                    self.status.showMessage(os.path.basename(img_path))
                    return
                
                # Cache the base pixmap
                self._manage_cache(self.pixmap_cache, img_path, base_pixmap)
            
            # SMART LUT PROCESSING: Use full quality when lines are present
            if self.lut_enabled and self.current_lut and self.lut_strength > 0:
                # Check if we have cached LUT result (with lines)
                lut_cache_key = self._get_lut_cache_key()
                if (hasattr(self, '_lut_process_cache') and 
                    lut_cache_key in self._lut_process_cache):
                    # Use cached full-quality LUT result
                    pixmap = self._lut_process_cache[lut_cache_key].copy()
                else:
                    # Need full LUT processing - especially important for lines
                    if (self.lines_visible and 
                        (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines)):
                        # Lines present: FORCE full quality async LUT processing
                        self.current_image = img_path  # Set this first
                        
                        # Show fast preview immediately while full processing happens
                        self.status.showMessage(f"Rendering lines with LUT... (preview)")
                        QApplication.processEvents()
                        
                        # Create fast preview with lines for immediate feedback
                        fast_pixmap = self.apply_fast_enhancements(base_pixmap.copy())
                        
                        # Apply basic transforms to preview
                        if self.rotation_angle != 0 or self.flipped_h or self.flipped_v:
                            fast_pixmap = self._apply_quick_transforms(fast_pixmap)
                        
                        # Scale and show preview immediately
                        preview_scaled = self._scale_pixmap(fast_pixmap, img_path)
                        self.image_label.setPixmap(preview_scaled)
                        QApplication.processEvents()
                        
                        # Start full quality processing
                        self._start_async_lut_processing()
                        return  # Exit here - async processing will complete display
                    else:
                        # No lines: Can use fast enhancement for quick preview
                        pixmap = self.apply_fast_enhancements(base_pixmap.copy())
            elif self.grayscale_value > 0 or self.contrast_value != 50 or self.gamma_value != 0:
                # Only basic enhancements needed
                pixmap = self.apply_fast_enhancements(base_pixmap.copy())
            else:
                pixmap = base_pixmap
            
            # Apply rotation and flips if needed
            if self.rotation_angle != 0 or self.flipped_h or self.flipped_v:
                image = pixmap.toImage()
                
                # Apply flips first
                if self.flipped_h:
                    transform_h = QTransform().scale(-1, 1)
                    image = image.transformed(transform_h)
                if self.flipped_v:
                    transform_v = QTransform().scale(1, -1)
                    image = image.transformed(transform_v)
                
                # Apply rotation
                if self.rotation_angle != 0:
                    transform_rot = QTransform()
                    transform_rot.rotate(self.rotation_angle)
                    image = image.transformed(transform_rot)
                
                pixmap = QPixmap.fromImage(image)
            
            # Cache the enhanced and rotated version
            self._manage_cache(self.enhancement_cache, cache_key, pixmap)
        
        # Cache the original for line drawing reference
        self.original_pixmap = pixmap.copy()
        
        # Scale FIRST, then draw lines on the scaled version
        scaled_pixmap = self._scale_pixmap(pixmap, img_path)
        
        # Draw lines on the scaled pixmap if any exist AND lines are visible
        if self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
            final_pixmap = scaled_pixmap.copy()
            painter = QPainter(final_pixmap)
            painter.setRenderHint(QPainter.Antialiasing, False)
            
            # Use user-selected color and thickness
            pen_color = self.line_color
            pen_thickness = self.line_thickness
            painter.setPen(QPen(pen_color, pen_thickness, Qt.SolidLine))
            
            # Get the transformation parameters for line drawing
            original_size = self.original_pixmap.size()
            label_size = self.image_label.size()
            zoom_factor = self.image_label.zoom_factor
            
            # UNIFIED coordinate calculation - use the same logic for ALL zoom levels
            # Calculate the base scaled size that would be used at 100% zoom
            base_scaled = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Apply zoom factor to get the actual displayed size
            zoomed_width = int(base_scaled.width() * zoom_factor)
            zoomed_height = int(base_scaled.height() * zoom_factor)
            
            # Calculate position within the final pixmap (including pan offset)
            draw_x = (label_size.width() - zoomed_width) // 2 + int(self.image_label.pan_offset_x)
            draw_y = (label_size.height() - zoomed_height) // 2 + int(self.image_label.pan_offset_y)
            
            # Scale factors from original to zoomed display (works for all zoom levels)
            scale_x = zoomed_width / original_size.width()
            scale_y = zoomed_height / original_size.height()
            
            # Handle transformations for line drawing (flips and rotation)
            if self.rotation_angle != 0 or self.flipped_h or self.flipped_v:
                # Get the original image dimensions for proper line transformation
                # We need to apply the same transformation sequence: flips first, then rotation
                
                # Draw vertical lines (adjusted for flips and rotation)
                for x in self.drawn_lines:
                    # Apply flip transformations first
                    transformed_x = x
                    if self.flipped_h:
                        transformed_x = original_size.width() - x
                    
                    # Then apply rotation transformation
                    if self.rotation_angle == 90:
                        # Vertical line becomes horizontal
                        transformed_y = transformed_x
                        display_y = int(transformed_y * scale_y) + draw_y
                        if 0 <= display_y < final_pixmap.height():
                            painter.drawLine(0, display_y, final_pixmap.width(), display_y)
                    elif self.rotation_angle == 180:
                        # Vertical line stays vertical but position changes
                        final_x = original_size.width() - transformed_x
                        display_x = int(final_x * scale_x) + draw_x
                        if 0 <= display_x < final_pixmap.width():
                            painter.drawLine(display_x, 0, display_x, final_pixmap.height())
                    elif self.rotation_angle == 270:
                        # Vertical line becomes horizontal
                        final_y = original_size.height() - transformed_x
                        display_y = int(final_y * scale_y) + draw_y
                        if 0 <= display_y < final_pixmap.height():
                            painter.drawLine(0, display_y, final_pixmap.width(), display_y)
                    else:
                        # No rotation, just flips applied
                        display_x = int(transformed_x * scale_x) + draw_x
                        if 0 <= display_x < final_pixmap.width():
                            painter.drawLine(display_x, 0, display_x, final_pixmap.height())
                
                # Draw horizontal lines (adjusted for flips and rotation)
                for y in self.drawn_horizontal_lines:
                    # Apply flip transformations first
                    transformed_y = y
                    if self.flipped_v:
                        transformed_y = original_size.height() - y
                    
                    # Then apply rotation transformation
                    if self.rotation_angle == 90:
                        # Horizontal line becomes vertical
                        final_x = original_size.width() - transformed_y
                        display_x = int(final_x * scale_x) + draw_x
                        if 0 <= display_x < final_pixmap.width():
                            painter.drawLine(display_x, 0, display_x, final_pixmap.height())
                    elif self.rotation_angle == 180:
                        # Horizontal line stays horizontal but position changes
                        final_y = original_size.height() - transformed_y
                        display_y = int(final_y * scale_y) + draw_y
                        if 0 <= display_y < final_pixmap.height():
                            painter.drawLine(0, display_y, final_pixmap.width(), display_y)
                    elif self.rotation_angle == 270:
                        # Horizontal line becomes vertical
                        display_x = int(transformed_y * scale_x) + draw_x
                        if 0 <= display_x < final_pixmap.width():
                            painter.drawLine(display_x, 0, display_x, final_pixmap.height())
                    else:
                        # No rotation, just flips applied
                        display_y = int(transformed_y * scale_y) + draw_y
                        if 0 <= display_y < final_pixmap.height():
                            painter.drawLine(0, display_y, final_pixmap.width(), display_y)
                
                # Draw free lines (adjusted for flips and rotation)
                for line in self.drawn_free_lines:
                    start_x, start_y = line['start']
                    end_x, end_y = line['end']
                    
                    # Apply flip transformations first
                    flip_start_x = start_x
                    flip_start_y = start_y
                    flip_end_x = end_x
                    flip_end_y = end_y
                    
                    if self.flipped_h:
                        flip_start_x = original_size.width() - start_x
                        flip_end_x = original_size.width() - end_x
                    if self.flipped_v:
                        flip_start_y = original_size.height() - start_y
                        flip_end_y = original_size.height() - end_y
                    
                    # Then apply rotation transformation
                    if self.rotation_angle == 90:
                        # 90° rotation transformations
                        display_start_x = int((original_size.width() - flip_start_y) * scale_x) + draw_x
                        display_start_y = int(flip_start_x * scale_y) + draw_y
                        display_end_x = int((original_size.width() - flip_end_y) * scale_x) + draw_x
                        display_end_y = int(flip_end_x * scale_y) + draw_y
                    elif self.rotation_angle == 180:
                        # 180° rotation: both coordinates are flipped
                        display_start_x = int((original_size.width() - flip_start_x) * scale_x) + draw_x
                        display_start_y = int((original_size.height() - flip_start_y) * scale_y) + draw_y
                        display_end_x = int((original_size.width() - flip_end_x) * scale_x) + draw_x
                        display_end_y = int((original_size.height() - flip_end_y) * scale_y) + draw_y
                    elif self.rotation_angle == 270:
                        # 270° rotation transformations
                        display_start_x = int(flip_start_y * scale_x) + draw_x
                        display_start_y = int((original_size.height() - flip_start_x) * scale_y) + draw_y
                        display_end_x = int(flip_end_y * scale_x) + draw_x
                        display_end_y = int((original_size.height() - flip_end_x) * scale_y) + draw_y
                    else:
                        # No rotation, just flips applied
                        display_start_x = int(flip_start_x * scale_x) + draw_x
                        display_start_y = int(flip_start_y * scale_y) + draw_y
                        display_end_x = int(flip_end_x * scale_x) + draw_x
                        display_end_y = int(flip_end_y * scale_y) + draw_y
                    
                    # Draw the line with more lenient bounds checking
                    tolerance = 10  # pixels
                    min_x = min(display_start_x, display_end_x)
                    max_x = max(display_start_x, display_end_x)
                    min_y = min(display_start_y, display_end_y)
                    max_y = max(display_start_y, display_end_y)
                    
                    if (max_x >= -tolerance and min_x <= final_pixmap.width() + tolerance and
                        max_y >= -tolerance and min_y <= final_pixmap.height() + tolerance):
                        painter.setRenderHint(QPainter.Antialiasing, True)
                        painter.drawLine(display_start_x, display_start_y, display_end_x, display_end_y)
                        painter.setRenderHint(QPainter.Antialiasing, False)
            else:
                # No rotation - original line drawing logic
                # Draw vertical lines
                for x in self.drawn_lines:
                    display_x = int(x * scale_x) + draw_x
                    if 0 <= display_x < final_pixmap.width():
                        painter.drawLine(display_x, 0, display_x, final_pixmap.height())
                
                # Draw horizontal lines
                for y in self.drawn_horizontal_lines:
                    display_y = int(y * scale_y) + draw_y
                    if 0 <= display_y < final_pixmap.height():
                        painter.drawLine(0, display_y, final_pixmap.width(), display_y)
                
                # Draw free lines (two-point lines)
                for line in self.drawn_free_lines:
                    start_x, start_y = line['start']
                    end_x, end_y = line['end']
                    
                    # No rotation - use original coordinates directly
                    display_start_x = int(start_x * scale_x) + draw_x
                    display_start_y = int(start_y * scale_y) + draw_y
                    display_end_x = int(end_x * scale_x) + draw_x
                    display_end_y = int(end_y * scale_y) + draw_y
                    
                    # Draw the line with more lenient bounds checking
                    # Allow lines to be drawn if any part might be visible (let QPainter handle clipping)
                    # Add some tolerance to prevent precision issues from hiding lines
                    tolerance = 10  # pixels
                    
                    # Check if the line potentially intersects the visible area
                    min_x = min(display_start_x, display_end_x)
                    max_x = max(display_start_x, display_end_x)
                    min_y = min(display_start_y, display_end_y)
                    max_y = max(display_start_y, display_end_y)
                    
                    # Draw if the line's bounding box intersects the pixmap (with tolerance)
                    if (max_x >= -tolerance and min_x <= final_pixmap.width() + tolerance and
                        max_y >= -tolerance and min_y <= final_pixmap.height() + tolerance):
                        painter.drawLine(display_start_x, display_start_y, display_end_x, display_end_y)
            
            painter.end()
            scaled_pixmap = final_pixmap
        
        # Display the final scaled pixmap
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setToolTip("")
        self.current_image = img_path

    def _scale_pixmap(self, pixmap, img_path):
        """Scale pixmap for display with zoom and pan support"""
        size = self.image_label.size()
        zoom_factor = self.image_label.zoom_factor
        pan_x = self.image_label.pan_offset_x
        pan_y = self.image_label.pan_offset_y
        
        # Create cache key including zoom and pan for proper caching
        scale_key = f"{img_path}_{size.width()}_{size.height()}_{zoom_factor}_{pan_x}_{pan_y}"
        
        # UNIFIED coordinate system for ALL zoom levels - no special case for 1.0
        # Always calculate the base scaled size first
        base_scaled = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Apply zoom factor to get the final zoomed size
        zoomed_width = int(base_scaled.width() * zoom_factor)
        zoomed_height = int(base_scaled.height() * zoom_factor)
        zoomed_size = QSize(zoomed_width, zoomed_height)
        
        # Scale the original pixmap to the zoomed size
        zoomed_pixmap = pixmap.scaled(zoomed_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Create a pixmap the size of the label
        final_pixmap = QPixmap(size)
        final_pixmap.fill(Qt.black)  # Fill with black background
        
        # Calculate the position to draw the zoomed image
        # Center the zoomed image in the label, then apply pan offset
        draw_x = (size.width() - zoomed_width) // 2 + int(pan_x)
        draw_y = (size.height() - zoomed_height) // 2 + int(pan_y)
        
        # Draw the zoomed image onto the final pixmap
        painter = QPainter(final_pixmap)
        painter.drawPixmap(draw_x, draw_y, zoomed_pixmap)
        painter.end()
        
        scaled = final_pixmap
        
        self.last_size = size
        return scaled

    def _manage_cache(self, cache_dict, key, value):
        """Manage cache size with LRU-like behavior"""
        if len(cache_dict) >= self.max_cache_size:
            # Remove oldest entries
            keys_to_remove = list(cache_dict.keys())[:-self.max_cache_size//2]
            for k in keys_to_remove:
                del cache_dict[k]
            # Force garbage collection periodically
            if len(cache_dict) % 10 == 0:
                gc.collect()
        cache_dict[key] = value

    def load_cube_lut(self, file_path):
        """Load a CUBE format LUT file with safety checks - OPTIMIZED VERSION"""
        try:
            # Check LUT cache first for instant loading
            if file_path in self.lut_cache:
                print(f"LUT loaded from cache: {os.path.basename(file_path)}")
                self.status.showMessage(f"LUT loaded from cache: {os.path.basename(file_path)}")
                return self.lut_cache[file_path]
            
            # Check file size to prevent loading extremely large LUTs
            file_size = os.path.getsize(file_path)
            max_file_size = 50 * 1024 * 1024  # 50MB limit
            
            if file_size > max_file_size:
                print(f"LUT file too large: {file_size / (1024*1024):.1f}MB > {max_file_size / (1024*1024):.1f}MB")
                self.status.showMessage(f"LUT file too large: {os.path.basename(file_path)}")
                return None
            
            # Show loading status
            self.status.showMessage(f"Loading LUT: {os.path.basename(file_path)}...")
            QApplication.processEvents()  # Allow UI to update
            
            # OPTIMIZATION 1: Read entire file at once (faster than readlines)
            with open(file_path, 'r', encoding='utf-8', buffering=8192) as f:
                content = f.read()
            
            # OPTIMIZATION 2: Split lines once and filter in one pass
            lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
            
            lut_size = 32  # Default size
            
            # OPTIMIZATION 3: Find LUT size quickly without parsing every line
            for line in lines:
                if line.startswith('LUT_3D_SIZE'):
                    lut_size = int(line.split()[-1])
                    # Safety check for LUT size
                    if lut_size > 256:
                        print(f"LUT size too large: {lut_size} > 256")
                        self.status.showMessage(f"LUT size too large: {lut_size}")
                        return None
                    break
            
            # OPTIMIZATION 4: Pre-allocate list for better performance
            expected_size = lut_size ** 3
            lut_data = []
            # Note: Python lists don't have reserve(), but we can hint the expected size
            
            # OPTIMIZATION 5: Batch process data lines only (skip metadata)
            data_lines = [line for line in lines 
                         if not line.startswith(('TITLE', 'LUT_3D_SIZE', 'DOMAIN_MIN', 'DOMAIN_MAX')) 
                         and ' ' in line]
            
            # OPTIMIZATION 6: Fast parsing with list comprehension and minimal error checking
            try:
                for line in data_lines:
                    parts = line.split()
                    if len(parts) >= 3:
                        # Direct float conversion - faster than try/except in loop
                        lut_data.append((float(parts[0]), float(parts[1]), float(parts[2])))
                        
                        # Early break when we have enough data
                        if len(lut_data) >= expected_size:
                            break
                            
            except (ValueError, IndexError) as e:
                print(f"Error parsing LUT data: {e}")
                self.status.showMessage(f"Error parsing LUT: {os.path.basename(file_path)}")
                return None
            
            # Verify we have the expected amount of data
            if len(lut_data) != expected_size:
                print(f"Warning: LUT size mismatch. Expected {expected_size}, got {len(lut_data)}")
                self.status.showMessage(f"Invalid LUT format: {os.path.basename(file_path)}")
                return None
            
            # OPTIMIZATION 7: Create optimized LUT structure
            lut_result = {
                'size': lut_size,
                'data': lut_data,
                'file_path': file_path,  # Store for cache identification
                'file_size': file_size   # Store for memory management
            }
            
            # OPTIMIZATION 8: Cache the loaded LUT for instant reuse
            self.lut_cache[file_path] = lut_result
            
            # OPTIMIZATION 9: Manage cache size to prevent memory issues
            if len(self.lut_cache) > 10:  # Keep max 10 LUTs cached
                # Remove oldest cache entries
                oldest_key = next(iter(self.lut_cache))
                del self.lut_cache[oldest_key]
                print(f"LUT cache: Removed {os.path.basename(oldest_key)} to free memory")
            
            print(f"LUT loaded successfully: {lut_size}³ ({len(lut_data)} entries)")
            self.status.showMessage(f"LUT loaded: {os.path.basename(file_path)} ({lut_size}³)")
            
            return lut_result
            
        except Exception as e:
            print(f"Error loading CUBE LUT {file_path}: {e}")
            self.status.showMessage(f"Error loading LUT: {os.path.basename(file_path)}")
            return None

    def apply_lut_to_image(self, pixmap, lut, strength=100):
        """Apply a 3D LUT to a pixmap with specified strength - SMART CACHING VERSION"""
        if not lut or not pixmap or pixmap.isNull():
            return pixmap
        
        try:
            # Create improved cache key that includes image dimensions for zoom awareness
            cache_key = f"lut_{id(pixmap)}_{pixmap.width()}x{pixmap.height()}_{lut['file_path']}_{strength}"
            
            # Check if we already processed this exact combination
            if hasattr(self, '_lut_process_cache') and cache_key in self._lut_process_cache:
                return self._lut_process_cache[cache_key]
            
            # Initialize LUT process cache if not exists
            if not hasattr(self, '_lut_process_cache'):
                self._lut_process_cache = {}
            
            # Adaptive processing based on image size
            image = pixmap.toImage()
            if image.isNull():
                return pixmap
            
            original_size = image.size()
            image_pixels = image.width() * image.height()
            
            # Dynamic max size based on image complexity
            if image_pixels > 4000000:  # Very large (>4MP)
                max_lut_size = 1200  # Aggressive scaling for huge images
            elif image_pixels > 2000000:  # Large (>2MP) 
                max_lut_size = 1600  # Moderate scaling
            else:
                max_lut_size = 2048  # Keep quality for smaller images
            
            # Only scale down very large images, keep more detail
            if image.width() > max_lut_size or image.height() > max_lut_size:
                scale_factor = min(max_lut_size / image.width(), max_lut_size / image.height())
                scaled_size = QSize(int(image.width() * scale_factor), int(image.height() * scale_factor))
                image = image.scaled(scaled_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                is_scaled = True
            else:
                is_scaled = False
            
            # Convert to RGB32 format for processing
            if image.format() != image.Format.Format_RGB32:
                image = image.convertToFormat(image.Format.Format_RGB32)
            
            width = image.width()
            height = image.height()
            lut_size = lut['size']
            lut_data = lut['data']
            strength_factor = strength / 100.0
            
            # GPU ACCELERATION: Try GPU processing first
            if self.gpu_processor.is_available():
                print(f"Applying LUT using GPU acceleration ({width}x{height}) - LUT size: {lut_size}³, strength: {strength_factor:.2f}")
                gpu_result = self.gpu_processor.apply_lut_gpu(image, lut_data, lut_size, strength_factor)
                if gpu_result is not None:
                    print("✓ GPU LUT processing successful - colors should now be correct")
                    # GPU processing successful
                    if is_scaled:
                        gpu_result = gpu_result.scaled(original_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    result_pixmap = QPixmap.fromImage(gpu_result)
                    
                    # Smart cache management
                    max_cache_size = 8 if image_pixels < 1000000 else 4
                    if len(self._lut_process_cache) > max_cache_size:
                        oldest_key = next(iter(self._lut_process_cache))
                        del self._lut_process_cache[oldest_key]
                    
                    self._lut_process_cache[cache_key] = result_pixmap
                    
                    # ZOOM OPTIMIZATION: Cache the final processed image for fast zoom
                    self._last_processed_image = gpu_result.copy()
                    self._last_processed_has_lut = True if (self.lut_enabled and self.current_lut and self.lut_strength>0) else False
                    
                    return result_pixmap
                else:
                    print("✗ GPU LUT processing failed, falling back to CPU")
                    print("GPU processing failed, falling back to CPU")
            
            # FALLBACK: CPU processing when GPU is not available or fails
            
            # Choose processing method based on scaled image size
            scaled_pixels = width * height
            if scaled_pixels > 1500000:  # Still large after scaling
                # Use optimized fast mode for very large images
                self._apply_lut_optimized(image, lut_data, lut_size, strength_factor)
            else:
                # Use high quality mode for moderate sized images
                self._apply_lut_with_interpolation(image, lut_data, lut_size, strength_factor)
            
            # If we scaled down, scale back up to original size with quality
            if is_scaled:
                image = image.scaled(original_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            result_pixmap = QPixmap.fromImage(image)
            
            # Smart cache management - keep more entries for smaller images
            max_cache_size = 8 if image_pixels < 1000000 else 4
            if len(self._lut_process_cache) > max_cache_size:
                # Remove oldest entries
                oldest_key = next(iter(self._lut_process_cache))
                del self._lut_process_cache[oldest_key]
            
            self._lut_process_cache[cache_key] = result_pixmap
            
            # ZOOM OPTIMIZATION: Cache the final processed image for fast zoom  
            self._last_processed_image = image.copy()
            self._last_processed_has_lut = True if (self.lut_enabled and self.current_lut and self.lut_strength>0) else False
            
            return result_pixmap
            
        except Exception as e:
            print(f"Error applying LUT: {e}")
            return pixmap

    def clear_lut_cache(self):
        """Clear LUT processing cache to free memory and force GPU recompilation"""
        if hasattr(self, '_lut_process_cache'):
            self._lut_process_cache.clear()
        
        # Clear zoom optimization cache
        if hasattr(self, '_last_processed_image'):
            self._last_processed_image = None
        self._last_processed_has_lut = False
        
        # Also clear enhancement and scaled caches to ensure fresh processing
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        
        # Force GPU processor to reinitialize on next use
        if hasattr(self, 'gpu_processor') and self.gpu_processor:
            self.gpu_processor._force_reinit = True
        
        print("All LUT and GPU caches cleared - next LUT application will use fixed GPU kernels")
            
    def _apply_lut_optimized(self, image, lut_data, lut_size, strength_factor):
        """Optimized LUT application - faster but still good quality with progress"""
        width = image.width()
        height = image.height()
        
        # Use larger chunks for better performance
        chunk_size = 32  # Larger chunks for speed
        total_chunks = (height + chunk_size - 1) // chunk_size
        processed_chunks = 0
        
        for y_start in range(0, height, chunk_size):
            y_end = min(y_start + chunk_size, height)
            
            for y in range(y_start, y_end):
                scan_line = image.scanLine(y)
                
                # Process every 2nd pixel for speed, then interpolate
                for x in range(0, width, 2):
                    offset = x * 4
                    
                    # Read pixel bytes (BGRA order in Qt)
                    b = scan_line[offset]
                    g = scan_line[offset + 1] 
                    r = scan_line[offset + 2]
                    a = scan_line[offset + 3]
                    
                    # Normalize to 0-1 range
                    r_norm = r / 255.0
                    g_norm = g / 255.0
                    b_norm = b / 255.0
                    
                    # Use faster interpolation
                    lut_result = self._interpolate_lut_fast(r_norm, g_norm, b_norm, lut_data, lut_size)
                    
                    # Blend with original using strength factor
                    final_r = r_norm * (1.0 - strength_factor) + lut_result[0] * strength_factor
                    final_g = g_norm * (1.0 - strength_factor) + lut_result[1] * strength_factor
                    final_b = b_norm * (1.0 - strength_factor) + lut_result[2] * strength_factor
                    
                    # Clamp and convert back to bytes
                    final_r = max(0, min(255, int(final_r * 255 + 0.5)))
                    final_g = max(0, min(255, int(final_g * 255 + 0.5)))
                    final_b = max(0, min(255, int(final_b * 255 + 0.5)))
                    
                    # Write back to image (BGRA order)
                    scan_line[offset] = final_b
                    scan_line[offset + 1] = final_g
                    scan_line[offset + 2] = final_r
                    scan_line[offset + 3] = a
                    
                    # Fill the next pixel with interpolated values for speed
                    if x + 1 < width:
                        next_offset = (x + 1) * 4
                        scan_line[next_offset] = final_b
                        scan_line[next_offset + 1] = final_g
                        scan_line[next_offset + 2] = final_r
                        scan_line[next_offset + 3] = scan_line[next_offset + 3]  # Keep original alpha
            
            # Progress callback every few chunks to keep UI responsive
            processed_chunks += 1
            if hasattr(self, '_lut_progress_callback') and self._lut_progress_callback:
                if processed_chunks % 3 == 0:  # Update every 3 chunks
                    self._lut_progress_callback()  # Allow UI updates

    def _apply_lut_with_interpolation(self, image, lut_data, lut_size, strength_factor):
        """High-quality LUT application with trilinear interpolation"""
        width = image.width()
        height = image.height()
        
        # Process in smaller chunks for better performance while maintaining quality
        chunk_size = 16  # Smaller chunks for better cache performance
        
        for y_start in range(0, height, chunk_size):
            y_end = min(y_start + chunk_size, height)
            
            for y in range(y_start, y_end):
                scan_line = image.scanLine(y)
                
                for x in range(width):
                    offset = x * 4
                    
                    # Read pixel bytes (BGRA order in Qt)
                    b = scan_line[offset]
                    g = scan_line[offset + 1] 
                    r = scan_line[offset + 2]
                    a = scan_line[offset + 3]  # Preserve alpha
                    
                    # Normalize to 0-1 range
                    r_norm = r / 255.0
                    g_norm = g / 255.0
                    b_norm = b / 255.0
                    
                    # Apply LUT with trilinear interpolation for quality
                    lut_result = self._interpolate_lut_quality(r_norm, g_norm, b_norm, lut_data, lut_size)
                    
                    # Blend with original using strength factor
                    final_r = r_norm * (1.0 - strength_factor) + lut_result[0] * strength_factor
                    final_g = g_norm * (1.0 - strength_factor) + lut_result[1] * strength_factor
                    final_b = b_norm * (1.0 - strength_factor) + lut_result[2] * strength_factor
                    
                    # Clamp and convert back to bytes
                    final_r = max(0, min(255, int(final_r * 255 + 0.5)))
                    final_g = max(0, min(255, int(final_g * 255 + 0.5)))
                    final_b = max(0, min(255, int(final_b * 255 + 0.5)))
                    
                    # Write back to image (BGRA order)
                    scan_line[offset] = final_b
                    scan_line[offset + 1] = final_g
                    scan_line[offset + 2] = final_r
                    scan_line[offset + 3] = a  # Preserve alpha
    
    def _interpolate_lut_quality(self, r, g, b, lut_data, lut_size):
        """High-quality trilinear interpolation in 3D LUT"""
        # Scale to LUT coordinate space
        r_scaled = r * (lut_size - 1)
        g_scaled = g * (lut_size - 1)
        b_scaled = b * (lut_size - 1)
        
        # Get integer coordinates with bounds checking
        r_low = max(0, min(int(r_scaled), lut_size - 1))
        g_low = max(0, min(int(g_scaled), lut_size - 1))
        b_low = max(0, min(int(b_scaled), lut_size - 1))
        
        r_high = min(r_low + 1, lut_size - 1)
        g_high = min(g_low + 1, lut_size - 1)
        b_high = min(b_low + 1, lut_size - 1)
        
        # Get fractional parts for smooth interpolation
        r_frac = r_scaled - r_low
        g_frac = g_scaled - g_low
        b_frac = b_scaled - b_low
        
        # Helper function to safely get LUT value
        def get_lut_value(ri, gi, bi):
            try:
                idx = ri + gi * lut_size + bi * lut_size * lut_size
                if 0 <= idx < len(lut_data):
                    return lut_data[idx]
                else:
                    return (r, g, b)  # Fallback to original
            except (IndexError, ValueError):
                return (r, g, b)  # Fallback to original
        
        # Get 8 corner values for trilinear interpolation
        c000 = get_lut_value(r_low, g_low, b_low)
        c001 = get_lut_value(r_low, g_low, b_high)
        c010 = get_lut_value(r_low, g_high, b_low)
        c011 = get_lut_value(r_low, g_high, b_high)
        c100 = get_lut_value(r_high, g_low, b_low)
        c101 = get_lut_value(r_high, g_low, b_high)
        c110 = get_lut_value(r_high, g_high, b_low)
        c111 = get_lut_value(r_high, g_high, b_high)
        
        # Linear interpolation helper
        def lerp(a, b, t):
            return (
                a[0] * (1.0 - t) + b[0] * t,
                a[1] * (1.0 - t) + b[1] * t,
                a[2] * (1.0 - t) + b[2] * t
            )
        
        # Trilinear interpolation
        # Interpolate along b axis
        c00 = lerp(c000, c001, b_frac)
        c01 = lerp(c010, c011, b_frac)
        c10 = lerp(c100, c101, b_frac)
        c11 = lerp(c110, c111, b_frac)
        
        # Interpolate along g axis
        c0 = lerp(c00, c01, g_frac)
        c1 = lerp(c10, c11, g_frac)
        
        # Final interpolation along r axis
        result = lerp(c0, c1, r_frac)
        
        return result
        """Ultra-fast LUT application using lookup tables and nearest neighbor"""
        width = image.width()
        height = image.height()
        
        # Pre-build lookup table for common colors to avoid repeated calculations
        # Process in chunks for better cache performance
        chunk_size = 32  # Process 32 rows at a time
        
        for y_start in range(0, height, chunk_size):
            y_end = min(y_start + chunk_size, height)
            
            for y in range(y_start, y_end):
                scan_line = image.scanLine(y)
                
                # Process pixels in groups of 8 for better performance
                for x in range(0, width, 8):
                    x_end = min(x + 8, width)
                    
                    for px in range(x, x_end):
                        offset = px * 4
                        
                        # Read pixel bytes (BGRA order in Qt)
                        b = scan_line[offset]
                        g = scan_line[offset + 1] 
                        r = scan_line[offset + 2]
                        
                        # Use nearest neighbor for speed (no interpolation)
                        # Quantize to LUT grid directly
                        lut_r = min(int((r / 255.0) * (lut_size - 1) + 0.5), lut_size - 1)
                        lut_g = min(int((g / 255.0) * (lut_size - 1) + 0.5), lut_size - 1)
                        lut_b = min(int((b / 255.0) * (lut_size - 1) + 0.5), lut_size - 1)
                        
                        # Direct lookup - no interpolation for speed
                        idx = lut_r + lut_g * lut_size + lut_b * lut_size * lut_size
                        if 0 <= idx < len(lut_data):
                            new_r, new_g, new_b = lut_data[idx]
                        else:
                            new_r, new_g, new_b = r / 255.0, g / 255.0, b / 255.0
                        
                        # Apply strength blending (simplified)
                        if strength_factor < 1.0:
                            orig_r, orig_g, orig_b = r / 255.0, g / 255.0, b / 255.0
                            new_r = orig_r + (new_r - orig_r) * strength_factor
                            new_g = orig_g + (new_g - orig_g) * strength_factor
                            new_b = orig_b + (new_b - orig_b) * strength_factor
                        
                        # Convert back and clamp
                        final_r = max(0, min(255, int(new_r * 255)))
                        final_g = max(0, min(255, int(new_g * 255)))
                        final_b = max(0, min(255, int(new_b * 255)))
                        
                        # Write back
                        scan_line[offset] = final_b
                        scan_line[offset + 1] = final_g
                        scan_line[offset + 2] = final_r

    def _apply_lut_reduced_sampling(self, image, lut_data, lut_size, strength_factor):
        """Apply LUT with reduced sampling for very large LUTs"""
        width = image.width()
        height = image.height()
        
        # For large LUTs, sample every other pixel to maintain speed
        sample_rate = 2 if lut_size > 64 else 1
        
        for y in range(0, height, sample_rate):
            scan_line = image.scanLine(y)
            
            for x in range(0, width, sample_rate):
                offset = x * 4
                
                # Read pixel bytes
                b = scan_line[offset]
                g = scan_line[offset + 1] 
                r = scan_line[offset + 2]
                
                # Simple nearest neighbor lookup
                lut_r = min(int((r / 255.0) * (lut_size - 1)), lut_size - 1)
                lut_g = min(int((g / 255.0) * (lut_size - 1)), lut_size - 1)
                lut_b = min(int((b / 255.0) * (lut_size - 1)), lut_size - 1)
                
                idx = lut_r + lut_g * lut_size + lut_b * lut_size * lut_size
                if 0 <= idx < len(lut_data):
                    new_r, new_g, new_b = lut_data[idx]
                    
                    # Apply strength
                    if strength_factor < 1.0:
                        orig_r, orig_g, orig_b = r / 255.0, g / 255.0, b / 255.0
                        new_r = orig_r + (new_r - orig_r) * strength_factor
                        new_g = orig_g + (new_g - orig_g) * strength_factor
                        new_b = orig_b + (new_b - orig_b) * strength_factor
                    
                    # Convert and write back
                    final_r = max(0, min(255, int(new_r * 255)))
                    final_g = max(0, min(255, int(new_g * 255)))
                    final_b = max(0, min(255, int(new_b * 255)))
                    
                    scan_line[offset] = final_b
                    scan_line[offset + 1] = final_g
                    scan_line[offset + 2] = final_r
                    
                    # Fill in skipped pixels if sampling
                    if sample_rate > 1:
                        # Copy to adjacent pixels for smoother result
                        for dx in range(1, min(sample_rate, width - x)):
                            next_offset = (x + dx) * 4
                            scan_line[next_offset] = final_b
                            scan_line[next_offset + 1] = final_g
                            scan_line[next_offset + 2] = final_r
            
            # Fill in skipped rows if sampling
            if sample_rate > 1 and y + 1 < height:
                next_scan_line = image.scanLine(y + 1)
                # Copy the processed row to the next row for smoother result
                for i in range(width * 4):
                    next_scan_line[i] = scan_line[i]

    def _interpolate_lut_fast(self, r, g, b, lut_data, lut_size):
        """Optimized trilinear interpolation in 3D LUT"""
        # Scale to LUT coordinate space
        r_scaled = r * (lut_size - 1)
        g_scaled = g * (lut_size - 1)
        b_scaled = b * (lut_size - 1)
        
        # Get integer coordinates with bounds checking
        r_low = max(0, min(int(r_scaled), lut_size - 1))
        g_low = max(0, min(int(g_scaled), lut_size - 1))
        b_low = max(0, min(int(b_scaled), lut_size - 1))
        
        r_high = min(r_low + 1, lut_size - 1)
        g_high = min(g_low + 1, lut_size - 1)
        b_high = min(b_low + 1, lut_size - 1)
        
        # Get fractional parts
        r_frac = r_scaled - r_low
        g_frac = g_scaled - g_low
        b_frac = b_scaled - b_low
        
        # Pre-calculate indices for better performance
        try:
            idx000 = r_low + g_low * lut_size + b_low * lut_size * lut_size
            idx001 = r_low + g_low * lut_size + b_high * lut_size * lut_size
            idx010 = r_low + g_high * lut_size + b_low * lut_size * lut_size
            idx011 = r_low + g_high * lut_size + b_high * lut_size * lut_size
            idx100 = r_high + g_low * lut_size + b_low * lut_size * lut_size
            idx101 = r_high + g_low * lut_size + b_high * lut_size * lut_size
            idx110 = r_high + g_high * lut_size + b_low * lut_size * lut_size
            idx111 = r_high + g_high * lut_size + b_high * lut_size * lut_size
            
            # Get 8 corner values with bounds checking
            c000 = lut_data[idx000] if 0 <= idx000 < len(lut_data) else (r, g, b)
            c001 = lut_data[idx001] if 0 <= idx001 < len(lut_data) else (r, g, b)
            c010 = lut_data[idx010] if 0 <= idx010 < len(lut_data) else (r, g, b)
            c011 = lut_data[idx011] if 0 <= idx011 < len(lut_data) else (r, g, b)
            c100 = lut_data[idx100] if 0 <= idx100 < len(lut_data) else (r, g, b)
            c101 = lut_data[idx101] if 0 <= idx101 < len(lut_data) else (r, g, b)
            c110 = lut_data[idx110] if 0 <= idx110 < len(lut_data) else (r, g, b)
            c111 = lut_data[idx111] if 0 <= idx111 < len(lut_data) else (r, g, b)
            
            # Trilinear interpolation - optimized calculations
            # Interpolate along b axis
            c00_r = c000[0] + (c001[0] - c000[0]) * b_frac
            c00_g = c000[1] + (c001[1] - c000[1]) * b_frac
            c00_b = c000[2] + (c001[2] - c000[2]) * b_frac
            
            c01_r = c010[0] + (c011[0] - c010[0]) * b_frac
            c01_g = c010[1] + (c011[1] - c010[1]) * b_frac
            c01_b = c010[2] + (c011[2] - c010[2]) * b_frac
            
            c10_r = c100[0] + (c101[0] - c100[0]) * b_frac
            c10_g = c100[1] + (c101[1] - c100[1]) * b_frac
            c10_b = c100[2] + (c101[2] - c100[2]) * b_frac
            
            c11_r = c110[0] + (c111[0] - c110[0]) * b_frac
            c11_g = c110[1] + (c111[1] - c110[1]) * b_frac
            c11_b = c110[2] + (c111[2] - c110[2]) * b_frac
            
            # Interpolate along g axis
            c0_r = c00_r + (c01_r - c00_r) * g_frac
            c0_g = c00_g + (c01_g - c00_g) * g_frac
            c0_b = c00_b + (c01_b - c00_b) * g_frac
            
            c1_r = c10_r + (c11_r - c10_r) * g_frac
            c1_g = c10_g + (c11_g - c10_g) * g_frac
            c1_b = c10_b + (c11_b - c10_b) * g_frac
            
            # Final interpolation along r axis
            result_r = c0_r + (c1_r - c0_r) * r_frac
            result_g = c0_g + (c1_g - c0_g) * r_frac
            result_b = c0_b + (c1_b - c0_b) * r_frac
            
            return (result_r, result_g, result_b)
            
        except (IndexError, ValueError):
            # Fallback to original values if interpolation fails
            return (r, g, b)

    def _interpolate_lut(self, r, g, b, lut_data, lut_size):
        """Trilinear interpolation in 3D LUT"""
        # Scale to LUT coordinate space
        r_scaled = r * (lut_size - 1)
        g_scaled = g * (lut_size - 1)
        b_scaled = b * (lut_size - 1)
        
        # Get integer coordinates
        r_low = int(r_scaled)
        g_low = int(g_scaled)
        b_low = int(b_scaled)
        
        r_high = min(r_low + 1, lut_size - 1)
        g_high = min(g_low + 1, lut_size - 1)
        b_high = min(b_low + 1, lut_size - 1)
        
        # Get fractional parts
        r_frac = r_scaled - r_low
        g_frac = g_scaled - g_low
        b_frac = b_scaled - b_low
        
        # Trilinear interpolation
        def get_lut_value(ri, gi, bi):
            index = ri + gi * lut_size + bi * lut_size * lut_size
            if 0 <= index < len(lut_data):
                return lut_data[index]
            return (r, g, b)  # Fallback to original
        
        # Get 8 corner values
        c000 = get_lut_value(r_low, g_low, b_low)
        c001 = get_lut_value(r_low, g_low, b_high)
        c010 = get_lut_value(r_low, g_high, b_low)
        c011 = get_lut_value(r_low, g_high, b_high)
        c100 = get_lut_value(r_high, g_low, b_low)
        c101 = get_lut_value(r_high, g_low, b_high)
        c110 = get_lut_value(r_high, g_high, b_low)
        c111 = get_lut_value(r_high, g_high, b_high)
        
        # Interpolate along each axis
        def lerp(a, b, t):
            return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
        
        # Interpolate along b axis
        c00 = lerp(c000, c001, b_frac)
        c01 = lerp(c010, c011, b_frac)
        c10 = lerp(c100, c101, b_frac)
        c11 = lerp(c110, c111, b_frac)
        
        # Interpolate along g axis
        c0 = lerp(c00, c01, g_frac)
        c1 = lerp(c10, c11, g_frac)
        
        # Final interpolation along r axis
        result = lerp(c0, c1, r_frac)
        
        return result

    def scan_lut_folder(self, folder_path):
        """Scan a folder and its subfolders for CUBE LUT files"""
        if not folder_path or not os.path.exists(folder_path):
            return []
        
        lut_files = []
        try:
            # Walk through all subdirectories to find .cube files
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.cube'):
                        full_path = os.path.join(root, file)
                        lut_files.append(full_path)
            
            # Sort: first by first-level folder (relative to root), then by filename
            def lut_sort_key(full_path):
                rel = os.path.relpath(full_path, folder_path)
                parts = rel.split(os.sep)
                if len(parts) == 1:
                    # File directly in root: group key empty so it appears before folder groups
                    return ("", parts[0].lower())
                first_folder = parts[0].lower()
                filename = parts[-1].lower()
                return (first_folder, filename)
            lut_files.sort(key=lut_sort_key)
            
            print(f"Found {len(lut_files)} CUBE LUT files in {folder_path} and subfolders")
            
        except Exception as e:
            print(f"Error scanning LUT folder: {e}")
        
        return lut_files

    def apply_fast_enhancements(self, pixmap):
        """Apply fast image enhancements using Qt's optimized color effects."""
        try:
            if not pixmap or pixmap.isNull():
                return pixmap
                
            # Fast grayscale conversion using Qt's built-in weighted average
            if self.grayscale_value > 0:
                # Create a grayscale version using Qt's optimized conversion
                image = pixmap.toImage()
                gray_image = image.convertToFormat(image.Format.Format_Grayscale8)
                gray_pixmap = QPixmap.fromImage(gray_image)
                
                if self.grayscale_value == 100:
                    pixmap = gray_pixmap
                else:
                    # Fast blend using Qt's composition modes
                    result = QPixmap(pixmap.size())
                    result.fill(Qt.transparent)
                    
                    painter = QPainter(result)
                    painter.setRenderHint(QPainter.Antialiasing)
                    
                    # Draw original image
                    painter.setOpacity(1.0 - (self.grayscale_value / 100.0))
                    painter.drawPixmap(0, 0, pixmap)
                    
                    # Draw grayscale overlay
                    painter.setOpacity(self.grayscale_value / 100.0)
                    painter.drawPixmap(0, 0, gray_pixmap)
                    
                    painter.end()
                    pixmap = result
            
            # Apply contrast and gamma using fast QPainter effects instead of pixel manipulation
            if self.contrast_value != 50 or self.gamma_value != 0:
                # Create enhanced version using QPainter composition
                enhanced = QPixmap(pixmap.size())
                enhanced.fill(Qt.transparent)
                
                painter = QPainter(enhanced)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Fast contrast approximation using opacity and blend modes
                if self.contrast_value != 50:
                    # Range: -130 to +200, where 50 is normal
                    contrast_offset = self.contrast_value - 50  # Convert to offset from normal
                    contrast_factor = contrast_offset / 50.0  # Normalize to reasonable range
                    
                    if contrast_factor > 0:
                        # Increase contrast using multiple overlay passes
                        painter.drawPixmap(0, 0, pixmap)
                        painter.setCompositionMode(QPainter.CompositionMode_Overlay)
                        
                        # Strong base effect for immediate visibility
                        base_opacity = min(1.0, abs(contrast_factor) * 0.8)
                        painter.setOpacity(base_opacity)
                        painter.drawPixmap(0, 0, pixmap)
                        
                        # Add multiple passes for stronger effect
                        num_passes = max(1, int(abs(contrast_factor) * 2))
                        for i in range(min(num_passes, 4)):  # Up to 4 passes
                            painter.setOpacity(min(0.7, abs(contrast_factor) * 0.3))
                            painter.drawPixmap(0, 0, pixmap)
                            
                        # For extreme values, add even more dramatic effects
                        if self.contrast_value > 150:
                            painter.setCompositionMode(QPainter.CompositionMode_HardLight)
                            painter.setOpacity(0.6)
                            painter.drawPixmap(0, 0, pixmap)
                    else:
                        # Decrease contrast - make image flat and gray
                        # Create a much more dramatic low-contrast effect
                        
                        # Start with original image
                        painter.drawPixmap(0, 0, pixmap)
                        
                        # Blend heavily with gray using multiple techniques for maximum effect
                        mid_gray = QPixmap(pixmap.size())
                        mid_gray.fill(QColor(128, 128, 128))  # 50% gray
                        
                        # Method 1: Direct overlay with gray using multiply mode for washing out
                        painter.setCompositionMode(QPainter.CompositionMode_Multiply)
                        gray_strength = abs(contrast_factor)  # 0 to 3.6 for range -130 to 50
                        
                        # Much stronger effect - make it very noticeable immediately
                        base_opacity = min(1.0, gray_strength * 0.7)  # Strong immediate effect
                        painter.setOpacity(base_opacity)
                        painter.drawPixmap(0, 0, mid_gray)
                        
                        # Method 2: Add screen blend to further wash out the image
                        painter.setCompositionMode(QPainter.CompositionMode_Screen)
                        painter.setOpacity(min(0.8, gray_strength * 0.5))
                        painter.drawPixmap(0, 0, mid_gray)
                        
                        # Method 3: For extreme negative values, add direct color burn for maximum flattening
                        if self.contrast_value < 0:  # For truly negative values
                            painter.setCompositionMode(QPainter.CompositionMode_ColorBurn)
                            painter.setOpacity(min(0.6, gray_strength * 0.3))
                            painter.drawPixmap(0, 0, mid_gray)
                            
                        # Method 4: Final soft light pass to complete the washed-out look
                        painter.setCompositionMode(QPainter.CompositionMode_SoftLight)
                        painter.setOpacity(min(0.9, gray_strength * 0.6))
                        painter.drawPixmap(0, 0, mid_gray)
                else:
                    painter.drawPixmap(0, 0, pixmap)
                
                # Fast gamma approximation using multiply blend
                if self.gamma_value != 0:
                    # Range: -200 to +500, where 0 is normal  
                    gamma_factor = self.gamma_value / 100.0  # -2 to +5
                    
                    if gamma_factor > 0:
                        # Brighten dramatically using multiple screen passes
                        painter.setCompositionMode(QPainter.CompositionMode_Screen)
                        
                        # Much stronger base brightening effect
                        base_opacity = min(1.0, abs(gamma_factor) * 0.7)  # Much stronger: 0.7 instead of 0.2
                        painter.setOpacity(base_opacity)
                        painter.drawPixmap(0, 0, pixmap)
                        
                        # Add multiple screen passes for dramatic brightening even at low values
                        num_passes = max(1, int(abs(gamma_factor) * 1.8))  # More passes
                        for i in range(min(num_passes, 4)):  # Up to 4 passes
                            painter.setOpacity(min(0.6, abs(gamma_factor) * 0.25))  # Much stronger passes
                            painter.drawPixmap(0, 0, pixmap)
                        
                        # For extreme brightness, add color dodge for blown-out effect
                        if self.gamma_value > 300:
                            painter.setCompositionMode(QPainter.CompositionMode_ColorDodge)
                            painter.setOpacity(0.4)
                            painter.drawPixmap(0, 0, pixmap)
                    else:
                        # Darken dramatically using multiply with very dark overlays
                        painter.setCompositionMode(QPainter.CompositionMode_Multiply)
                        
                        # Create much darker overlay for dramatic effect
                        dark_overlay = QPixmap(pixmap.size())
                        # Make it much darker: range from black to dark gray
                        darkness_level = max(5, int(60 + gamma_factor * 40))  # Much darker range
                        dark_overlay.fill(QColor(darkness_level, darkness_level, darkness_level))
                        
                        # Much stronger base darkening effect
                        base_opacity = min(1.0, abs(gamma_factor) * 0.8)  # Much stronger: 0.8 instead of 0.2
                        painter.setOpacity(base_opacity)
                        painter.drawPixmap(0, 0, dark_overlay)
                        
                        # Add multiple dark overlay passes for very dark effect
                        num_passes = max(1, int(abs(gamma_factor) * 1.5))
                        for i in range(min(num_passes, 3)):
                            # Use even darker overlay for additional passes
                            very_dark = QPixmap(pixmap.size())
                            very_dark.fill(QColor(20, 20, 20))  # Very dark overlay
                            painter.setOpacity(min(0.7, abs(gamma_factor) * 0.3))
                            painter.drawPixmap(0, 0, very_dark)
                
                painter.end()
                pixmap = enhanced
        
            # Apply LUT if one is loaded
            if self.current_lut and self.lut_strength > 0:
                pixmap = self.apply_lut_to_image(pixmap, self.current_lut, self.lut_strength)
        
            return pixmap
        
        except Exception as e:
            print(f"Error in apply_fast_enhancements: {e}")
            # Return original pixmap if enhancement fails
            import traceback
            traceback.print_exc()
            return pixmap

    def resizeEvent(self, event):
        # Simple debounced resize handling
        self.resize_timer.start(100)  # 100ms debounce
        super().resizeEvent(event)
        
    def _delayed_resize(self):
        """Handle resize events with a delay to improve performance"""
        # Check if we need to move sliders to second row
        current_width = self.width()
        should_use_two_rows = current_width < self.width_threshold
        
        # Only switch if the mode actually needs to change AND we have minimal hysteresis
        if should_use_two_rows != self.two_row_mode:
            # Reduced hysteresis to prevent rapid switching
            if should_use_two_rows and current_width < (self.width_threshold - 10):
                self._update_toolbar_layout(current_width)
            elif not should_use_two_rows and current_width > (self.width_threshold + 10):
                self._update_toolbar_layout(current_width)
        
        # Handle image display resize using smart caching system
        if self.current_image:
            # Use smart zoom display to preserve LUT caching during resize
            self._smart_zoom_display()

    def add_to_history(self, img_path):
        # If we've navigated back in history and now show a new random image,
        # remove all forward history.
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
            self.history_list.clear()
            for path in self.history:
                self._add_history_item(path)
        # Only add if not duplicating last
        if not self.history or (self.history and self.history[-1] != img_path):
            self.history.append(img_path)
            self._add_history_item(img_path)
        self.history_index = len(self.history) - 1

    def _add_history_item(self, img_path):
        item = QListWidgetItem(os.path.basename(img_path))
        
        # Only create thumbnails if history panel is visible to improve performance
        if self.show_history_checkbox.isChecked() and self.history_list.isVisible():
            try:
                # Use faster thumbnail loading for large collections
                reader = QImageReader(img_path)
                if reader.canRead():
                    # Scale down during read for much faster thumbnail creation
                    reader.setScaledSize(QSize(40, 40))
                    thumb_image = reader.read()
                    if not thumb_image.isNull():
                        thumb = QPixmap.fromImage(thumb_image)
                        item.setIcon(thumb)
            except Exception:
                # Skip thumbnail on error to avoid slowdown
                pass
        
        item.setToolTip(img_path)
        item.setData(Qt.UserRole, img_path)
        self.history_list.addItem(item)
        
        # Only scroll to bottom if history panel is visible
        if self.show_history_checkbox.isChecked() and self.history_list.isVisible():
            self.history_list.scrollToBottom()

    def on_history_clicked(self, item):
        img_path = item.data(Qt.UserRole)
        if img_path:
            # Update history_index to match clicked item
            try:
                idx = self.history.index(img_path)
                self.history_index = idx
            except ValueError:
                self.history_index = len(self.history) - 1
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()

    def toggle_history_panel(self, checked):
        self.history_list.setVisible(bool(checked))

    def update_timer_interval(self, value):
        self.timer_interval = value
        self.circle_timer.set_total_time(value)
        if self._auto_advance_active:
            self.timer_remaining = value
            self._update_ring()

    def toggle_timer(self, checked):
        self._auto_advance_active = bool(checked)
        self._reset_timer()

    def set_status_path(self, image_path):
        # For Windows, convert slashes and prepend file:///
        url = os.path.abspath(image_path)
        # Cross-platform file URL
        file_url = 'file:///' + url.replace("\\", "/") if os.name == "nt" else 'file://' + url
        display_name = os.path.basename(url)
        color = "#b7bcc1"
        self.path_label.setText(
            f'<a href="{file_url}" style="color: {color}; text-decoration: none;">{display_name}</a>'
        )
        self.path_label.setToolTip(url)
        self.path_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.path_label.setOpenExternalLinks(False)  # We'll handle clicks

    def open_in_explorer(self, file_url):
        path = file_url.replace('file:///', '') if os.name == "nt" else file_url.replace('file://', '')
        path = os.path.abspath(path)
        folder = os.path.dirname(path)
        if os.name == "nt":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:  # linux
            subprocess.Popen(["xdg-open", folder])

    def _reset_timer(self):
        if self._auto_advance_active and self.images:
            self.timer.stop()
            self.timer_remaining = self.timer_spin.value()
            self.circle_timer.set_total_time(self.timer_spin.value())
            self._update_ring()
            self.timer.start()
        else:
            self.timer.stop()
            self.circle_timer.set_remaining_time(0)

    def _on_timer_tick(self):
        if not self._auto_advance_active or not self.images:
            self.timer.stop()
            self.circle_timer.set_remaining_time(0)
            return
        
        # Don't decrease timer if paused
        if not self._timer_paused:
            self.timer_remaining -= 1
            if self.timer_remaining <= 0:
                # Use mode-aware navigation for auto-advance
                if self.random_mode:
                    self.show_random_image()
                else:
                    self._manual_next_image()
            else:
                self._update_ring()
        # If paused, just update the ring display
        else:
            self._update_ring()

    def toggle_timer_pause(self):
        """Toggle pause/resume state of the timer when it's active"""
        if self._auto_advance_active:
            self._timer_paused = not self._timer_paused
            self.circle_timer.set_paused(self._timer_paused)
            
            # Update tooltip to show current state
            if self._timer_paused:
                self.circle_timer.setToolTip("Timer Paused - Click to Resume")
            else:
                self.circle_timer.setToolTip("Timer Running - Click to Pause")

    def _update_ring(self):
        self.circle_timer.set_total_time(self.timer_spin.value())
        self.circle_timer.set_remaining_time(self.timer_remaining)

    def toggle_sort_order(self, checked):
        """Toggle between random and alphabetical image order."""
        self.random_mode = checked
        if self.random_mode:
            self.sort_order_button.setToolTip("Order: Random")
            self.status.showMessage("Image order set to Random")
        else:
            self.sort_order_button.setToolTip("Order: Alphabetical")
            self.status.showMessage("Image order set to Alphabetical")

    def toggle_toolbar_visibility(self, checked):
        """Toggle visibility of toolbars, status bar, and window decorations for immersive viewing."""
        if checked:
            # Show all UI elements
            self.main_toolbar.show()
            if self.two_row_mode:
                self.slider_toolbar.show()
            self.status.show()
            
            # Restore original window decorations
            if self.original_window_flags is not None:
                self.setWindowFlags(self.original_window_flags)
                self.show()  # Need to call show() after changing window flags
            
            self.status.showMessage("UI elements restored")
        else:
            # Hide all UI elements for immersive experience
            self.main_toolbar.hide()
            self.slider_toolbar.hide()
            
            # Remove window decorations (borderless window) 
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            self.show()  # Need to call show() after changing window flags
            
            # Show temporary message before hiding status bar
            self.status.showMessage("Immersive mode - Right-click to restore UI")
            QTimer.singleShot(2000, lambda: self.status.hide() if not self.main_toolbar.isVisible() else None)  # Hide status after 2 seconds

    def toggle_line_drawing(self, checked):
        self.line_drawing_mode = checked
        if checked:
            # Disable other line modes when this one is activated
            self.horizontal_line_drawing_mode = False
            self.free_line_drawing_mode = False
            self.current_line_start = None
            self.hline_tool_btn.setChecked(False)
            self.free_line_tool_btn.setChecked(False)
        # Don't clear lines when mode is deactivated - keep them visible
        self._update_cursor_and_status()

    def toggle_hline_drawing(self, checked):
        self.horizontal_line_drawing_mode = checked
        if checked:
            # Disable other line modes when this one is activated
            self.line_drawing_mode = False
            self.free_line_drawing_mode = False
            self.current_line_start = None
            self.line_tool_btn.setChecked(False)
            self.free_line_tool_btn.setChecked(False)
        # Don't clear lines when mode is deactivated - keep them visible
        self._update_cursor_and_status()

    def toggle_free_line_drawing(self, checked):
        self.free_line_drawing_mode = checked
        if checked:
            # Disable other line modes when this one is activated
            self.line_drawing_mode = False
            self.horizontal_line_drawing_mode = False
            self.line_tool_btn.setChecked(False)
            self.hline_tool_btn.setChecked(False)
        if not checked:
            # Reset current line start when mode is deactivated
            self.current_line_start = None
        self._update_cursor_and_status()

    def _update_cursor_and_status(self):
        """Update cursor and status message based on active drawing modes"""
        if self.free_line_drawing_mode:
            self.image_label.setCursor(Qt.CrossCursor)
            if self.current_line_start is None:
                self.status.showMessage("Free line drawing mode - Click first point to start line")
            else:
                self.status.showMessage("Free line drawing mode - Click second point to complete line")
        elif self.line_drawing_mode and self.horizontal_line_drawing_mode:
            self.image_label.setCursor(Qt.CrossCursor)
            self.status.showMessage("Drawing mode active - Click to draw both vertical and horizontal lines")
        elif self.line_drawing_mode:
            self.image_label.setCursor(Qt.CrossCursor)
            self.status.showMessage("Vertical line drawing mode active - Click on image to draw vertical lines")
        elif self.horizontal_line_drawing_mode:
            self.image_label.setCursor(Qt.CrossCursor)
            self.status.showMessage("Horizontal line drawing mode active - Click on image to draw horizontal lines")
        else:
            self.image_label.setCursor(Qt.ArrowCursor)
            self.status.showMessage("")

    def update_line_thickness(self, value):
        self.line_thickness = value
        # Clear LUT cache since line appearance changed
        if hasattr(self, '_lut_process_cache'):
            self._lut_process_cache.clear()
        # Clear enhancement cache to force full redraw with new thickness
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        if self.current_image and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
            # Force full display_image to ensure changes are visible
            self.display_image(self.current_image)

    def choose_line_color(self):
        """Open color picker dialog to choose line color"""
        color = QColorDialog.getColor(self.line_color, self, "Choose Line Color")
        if color.isValid():
            self.line_color = color
            # Update button background to show selected color
            self.line_color_btn.setStyleSheet(f"QToolButton {{ background-color: {self.line_color.name()}; border: 1px solid #666; }}")
            # Clear LUT cache since line appearance changed
            if hasattr(self, '_lut_process_cache'):
                self._lut_process_cache.clear()
            # Clear enhancement cache to force full redraw with new color
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            # Redraw current image with new color if there are lines
            if self.current_image and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
                # Force full display_image to ensure changes are visible
                self.display_image(self.current_image)

    def set_line_color(self, color_hex):
        """Set line color from hex string (used by preset color buttons)"""
        self.line_color = QColor(color_hex)
        # Update main color button background to show selected color
        self.line_color_btn.setStyleSheet(f"QToolButton {{ background-color: {self.line_color.name()}; border: 1px solid #666; }}")
        # Clear LUT cache since line appearance changed
        if hasattr(self, '_lut_process_cache'):
            self._lut_process_cache.clear()
        # Clear enhancement cache to force full redraw with new color
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        # Redraw current image with new color if there are lines
        if self.current_image and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
            # Force full display_image to ensure changes are visible
            self.display_image(self.current_image)

    def add_line(self, x_position):
        if x_position not in self.drawn_lines:
            self.drawn_lines.append(x_position)
            # Clear LUT cache since lines changed
            if hasattr(self, '_lut_process_cache'):
                self._lut_process_cache.clear()
            # Clear enhancement cache to force full redraw with lines
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            if self.current_image:
                # Use fast GPU-accelerated line update instead of full display_image
                self._fast_line_update()

    def add_hline(self, y_position):
        if y_position not in self.drawn_horizontal_lines:
            self.drawn_horizontal_lines.append(y_position)
            # Clear LUT cache since lines changed
            if hasattr(self, '_lut_process_cache'):
                self._lut_process_cache.clear()
            # Clear enhancement cache to force full redraw with lines
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            if self.current_image:
                # Use fast GPU-accelerated line update instead of full display_image
                self._fast_line_update()

    def add_free_line_point(self, x, y):
        """Handle clicks for free line drawing - first click sets start, second click completes line"""
        if self.current_line_start is None:
            # First click - set start point
            self.current_line_start = (x, y)
            self.status.showMessage(f"Line start set at ({x:.0f}, {y:.0f}) - Click second point to complete line")
        else:
            # Second click - complete the line
            start_x, start_y = self.current_line_start
            end_x, end_y = x, y
            
            # Add the completed line to our list
            line = {
                'start': (start_x, start_y),
                'end': (end_x, end_y)
            }
            self.drawn_free_lines.append(line)
            
            # Clear LUT cache since lines changed
            if hasattr(self, '_lut_process_cache'):
                self._lut_process_cache.clear()
            # Clear enhancement cache to force full redraw with lines
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            
            # Reset for next line
            self.current_line_start = None
            
            # Update display - use fast GPU-accelerated update instead of full display_image
            if self.current_image:
                # Use display_image for proper line rendering with GPU acceleration
                self.display_image(self.current_image)
            
            self.status.showMessage(f"Line drawn from ({start_x:.0f}, {start_y:.0f}) to ({end_x:.0f}, {end_y:.0f})")

    def clear_lines(self):
        self.drawn_lines.clear()
        self.drawn_horizontal_lines.clear()
        self.drawn_free_lines.clear()
        self.current_line_start = None
        # Clear LUT cache since lines changed
        if hasattr(self, '_lut_process_cache'):
            self._lut_process_cache.clear()
        # Clear enhancement cache to force full redraw
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        if self.current_image:
            # Force full display_image to ensure changes are visible
            self.display_image(self.current_image)

    def undo_last_line(self):
        """Remove the most recently added line (vertical, horizontal, or free line)"""
        removed_something = False
        
        # Prioritize free lines, then horizontal, then vertical
        if self.drawn_free_lines:
            # Remove the last free line
            self.drawn_free_lines.pop()
            removed_something = True
        elif self.drawn_horizontal_lines:
            # Remove the last horizontal line
            self.drawn_horizontal_lines.pop()
            removed_something = True
        elif self.drawn_lines:
            # Remove the last vertical line
            self.drawn_lines.pop()
            removed_something = True
        
        # Also reset current line start if we're in the middle of drawing a free line
        if self.current_line_start is not None:
            self.current_line_start = None
            removed_something = True
            self._update_cursor_and_status()  # Update status message
        
        if removed_something:
            # Clear LUT cache since lines changed
            if hasattr(self, '_lut_process_cache'):
                self._lut_process_cache.clear()
            # Clear enhancement cache to force full redraw
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            if self.current_image:
                # Force full display_image to ensure changes are visible
                self.display_image(self.current_image)
            self.status.showMessage("Removed last line")
        else:
            self.status.showMessage("No lines to remove")

    def toggle_line_visibility(self, checked):
        """Toggle visibility of all drawn lines"""
        self.lines_visible = checked
        # Update button appearance
        if hasattr(self, 'toggle_lines_btn'):
            self.toggle_lines_btn.setText("👁" if checked else "🙈")  # Eye open/closed
            self.toggle_lines_btn.setToolTip("Hide Lines" if checked else "Show Lines")
        
        # Clear LUT cache since line visibility changed
        if hasattr(self, '_lut_process_cache'):
            self._lut_process_cache.clear()
        # Clear enhancement cache to force full redraw
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        
        # Redraw current image to show/hide lines
        if self.current_image:
            # Force full display_image to ensure visibility changes are applied
            self.display_image(self.current_image)
    
    def save_current_view(self):
        """Save the currently displayed view to a file, including LUT/enhancements and visible lines."""
        # Create the final pixmap representing current view
        try:
            # If there is a currently displayed pixmap, use it (includes LUT/enhancements and possibly lines)
            if self.image_label and self.image_label.pixmap() and not self.image_label.pixmap().isNull():
                final_pixmap = self.image_label.pixmap().copy()
            else:
                # Fallback: render current image as display_image would
                if not self.current_image:
                    self.status.showMessage("No image loaded to save")
                    return
                # Force a full render into pixmap
                self.display_image(self.current_image)
                if not self.image_label.pixmap() or self.image_label.pixmap().isNull():
                    self.status.showMessage("Failed to render image for saving")
                    return
                final_pixmap = self.image_label.pixmap().copy()

            # Ask user for save location
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Current View", os.path.expanduser("~"), "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;All Files (*)", options=options)
            if not file_path:
                return

            # Determine format from extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            if ext in ('.jpg', '.jpeg'):
                fmt = 'JPEG'
            else:
                fmt = 'PNG'

            # Save using QPixmap save - this preserves pixel data including lines
            saved = final_pixmap.save(file_path, fmt)
            if saved:
                self.status.showMessage(f"Saved view to {os.path.basename(file_path)}")
            else:
                self.status.showMessage("Failed to save image")

        except Exception as e:
            print(f"Error saving current view: {e}")
            self.status.showMessage("Error saving current view")

    def toggle_always_on_top(self, checked):
        self.always_on_top = checked
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self._update_title()  # Update title to reflect always on top status
        self.show()  # Necessary to apply the window flag change immediately

    def toggle_fullscreen(self, checked=None):
        """Toggle fullscreen mode with enhanced error handling"""
        # If no parameter provided, toggle current state
        if checked is None:
            checked = not self.is_fullscreen
            
        print(f"toggle_fullscreen called with checked={checked}, current state={self.is_fullscreen}")
        
        try:
            if checked and not self.is_fullscreen:
                # Entering fullscreen
                print("Entering fullscreen mode...")
                self.normal_geometry = self.geometry()
                print(f"Stored geometry: {self.normal_geometry}")
                
                # Hide status bar in fullscreen
                self.statusBar().hide()
                
                # Use Qt's fullscreen method
                self.setWindowState(Qt.WindowFullScreen)
                self.showFullScreen()
                
                self.is_fullscreen = True
                self.activateWindow()
                self.raise_()
                self.setFocus()
                self.status.showMessage("FULLSCREEN MODE - Press Alt+F4 to exit, or Esc")
                
            elif not checked and self.is_fullscreen:
                # Exiting fullscreen
                print("Exiting fullscreen mode...")
                
                # Show status bar again
                self.statusBar().show()
                
                # Exit fullscreen using multiple methods
                self.setWindowState(Qt.WindowNoState)
                self.showNormal()
                
                if self.normal_geometry and self.normal_geometry.isValid():
                    print(f"Restoring geometry: {self.normal_geometry}")
                    self.setGeometry(self.normal_geometry)
                else:
                    print("Using default geometry")
                    self.resize(950, 650)
                    self.move(100, 100)
                
                self.is_fullscreen = False
                self.activateWindow()
                self.raise_()
                self.setFocus()
                self.status.showMessage("Fullscreen mode disabled")
            
            # Update button state
            if hasattr(self, 'fullscreen_btn'):
                self.fullscreen_btn.blockSignals(True)
                self.fullscreen_btn.setChecked(self.is_fullscreen)
                self.fullscreen_btn.blockSignals(False)
                
            print(f"Fullscreen toggle complete. New state: {self.is_fullscreen}")
            
        except Exception as e:
            print(f"Error in toggle_fullscreen: {e}")
            # Fallback: force exit
            self.force_exit_fullscreen()

    def exit_fullscreen(self):
        """Explicitly exit fullscreen mode"""
        print("exit_fullscreen called")
        if self.is_fullscreen:
            self.toggle_fullscreen(False)

    def force_exit_fullscreen(self):
        """Force exit fullscreen mode using multiple methods"""
        print("force_exit_fullscreen called - using all available methods")
        
        try:
            # Method 1: Set state and use showNormal
            self.is_fullscreen = False
            self.showNormal()
            
            # Method 2: Try setWindowState
            self.setWindowState(Qt.WindowNoState)
            
            # Method 3: Windows-specific API call (if available)
            if os.name == "nt" and ctypes:
                try:
                    # Get window handle
                    hwnd = int(self.winId())
                    # Force window to normal state using Windows API
                    ctypes.windll.user32.ShowWindow(hwnd, 1)  # SW_SHOWNORMAL = 1
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    print("Used Windows API to force normal window state")
                except Exception as e:
                    print(f"Windows API call failed: {e}")
            
            # Method 4: Show status bar
            self.statusBar().show()
            
            # Method 5: Restore geometry if available
            if self.normal_geometry and self.normal_geometry.isValid():
                print(f"Force restoring geometry: {self.normal_geometry}")
                self.setGeometry(self.normal_geometry)
            else:
                print("No stored geometry, using default size")
                self.resize(950, 650)
                self.move(100, 100)
            
            # Method 6: Force window focus and update
            self.activateWindow()
            self.raise_()
            self.setFocus()
            self.update()
            self.repaint()
            
            # Update button states
            if hasattr(self, 'fullscreen_btn'):
                self.fullscreen_btn.blockSignals(True)
                self.fullscreen_btn.setChecked(False)
                self.fullscreen_btn.blockSignals(False)
            
            self.status.showMessage("Fullscreen mode force exited")
            print(f"Force exit complete. Window state: {self.windowState()}")
            
        except Exception as e:
            print(f"Error in force_exit_fullscreen: {e}")
            # Last resort: try to close and restart
            print("Last resort: attempting emergency close...")
            self.close()

    def toggle_grayscale(self, checked):
        try:
            self.grayscale_value = 100 if checked else 0
            
            # Safely update slider value
            if hasattr(self, 'grayscale_slider') and self.grayscale_slider is not None:
                self.grayscale_slider.setValue(self.grayscale_value)
            
            # Update toggle button state (block signals to prevent infinite loop)
            if hasattr(self, 'grayscale_toggle_btn') and self.grayscale_toggle_btn is not None:
                self.grayscale_toggle_btn.blockSignals(True)
                self.grayscale_toggle_btn.setChecked(checked)
                self.grayscale_toggle_btn.blockSignals(False)
            
            # Clear caches and force immediate update
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            self._update_enhancement_menu_states()
            
            # Safely update image display
            if self.current_image:
                self.display_image(self.current_image)
                
        except Exception as e:
            print(f"Error in toggle_grayscale: {e}")
            # Don't let the error crash the app, just log it
            import traceback
            traceback.print_exc()

    def toggle_contrast(self, checked=None):
        """Toggle contrast between normal (50) and enhanced (100)"""
        try:
            if checked is None:
                # Toggle between current and normal
                self.contrast_value = 50 if self.contrast_value != 50 else 100
                checked = self.contrast_value != 50
            else:
                # Set based on checked state
                self.contrast_value = 100 if checked else 50
            
            # Safely update slider value
            if hasattr(self, 'contrast_slider') and self.contrast_slider is not None:
                self.contrast_slider.setValue(self.contrast_value)
            
            # Update toggle button state (block signals to prevent infinite loop)
            if hasattr(self, 'contrast_toggle_btn') and self.contrast_toggle_btn is not None:
                self.contrast_toggle_btn.blockSignals(True)
                self.contrast_toggle_btn.setChecked(checked)
                self.contrast_toggle_btn.blockSignals(False)
            
            # Clear caches and force immediate update
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            self._update_enhancement_menu_states()
            
            # Safely update image display
            if self.current_image:
                self.display_image(self.current_image)
                
        except Exception as e:
            print(f"Error in toggle_contrast: {e}")
            # Don't let the error crash the app, just log it
            import traceback
            traceback.print_exc()

    def toggle_gamma(self, checked=None):
        """Toggle gamma between normal (0) and enhanced (100)"""
        try:
            if checked is None:
                # Toggle between current and normal
                self.gamma_value = 0 if self.gamma_value != 0 else 100
                checked = self.gamma_value != 0
            else:
                # Set based on checked state
                self.gamma_value = 100 if checked else 0
            
            # Safely update slider value
            if hasattr(self, 'gamma_slider') and self.gamma_slider is not None:
                self.gamma_slider.setValue(self.gamma_value)
            
            # Update toggle button state (block signals to prevent infinite loop)
            if hasattr(self, 'gamma_toggle_btn') and self.gamma_toggle_btn is not None:
                self.gamma_toggle_btn.blockSignals(True)
                self.gamma_toggle_btn.setChecked(checked)
                self.gamma_toggle_btn.blockSignals(False)
            
            # Clear caches and force immediate update
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            self._update_enhancement_menu_states()
            
            # Safely update image display
            if self.current_image:
                self.display_image(self.current_image)
                
        except Exception as e:
            print(f"Error in toggle_gamma: {e}")
            # Don't let the error crash the app, just log it
            import traceback
            traceback.print_exc()

    def _update_enhancement_menu_states(self):
        """Update the checked state of enhancement menu actions"""
        if hasattr(self, 'grayscale_menu_action'):
            self.grayscale_menu_action.setChecked(self.grayscale_value > 0)
        if hasattr(self, 'contrast_menu_action'):
            self.contrast_menu_action.setChecked(self.contrast_value != 50)
        if hasattr(self, 'gamma_menu_action'):
            self.gamma_menu_action.setChecked(self.gamma_value != 0)

    def update_grayscale(self, value):
        self.grayscale_value = value
        # Update toggle button state (block signals to prevent loops)
        if hasattr(self, 'grayscale_toggle_btn') and self.grayscale_toggle_btn is not None:
            self.grayscale_toggle_btn.blockSignals(True)
            self.grayscale_toggle_btn.setChecked(value > 0)
            self.grayscale_toggle_btn.blockSignals(False)
        # Clear enhancement cache when settings change
        self.enhancement_cache.clear()
        self.scaled_cache.clear()  # Also clear scaled cache to force refresh
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def update_contrast(self, value):
        self.contrast_value = value
        # Update toggle button state (block signals to prevent loops)
        if hasattr(self, 'contrast_toggle_btn') and self.contrast_toggle_btn is not None:
            self.contrast_toggle_btn.blockSignals(True)
            self.contrast_toggle_btn.setChecked(value != 50)
            self.contrast_toggle_btn.blockSignals(False)
        # Clear enhancement cache when settings change
        self.enhancement_cache.clear()
        self.scaled_cache.clear()  # Also clear scaled cache to force refresh
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def update_gamma(self, value):
        self.gamma_value = value
        # Update toggle button state (block signals to prevent loops)
        if hasattr(self, 'gamma_toggle_btn') and self.gamma_toggle_btn is not None:
            self.gamma_toggle_btn.blockSignals(True)
            self.gamma_toggle_btn.setChecked(value != 0)  # Fixed: was checking != 50, should be != 0
            self.gamma_toggle_btn.blockSignals(False)
        # Clear enhancement cache when settings change
        self.enhancement_cache.clear()
        self.scaled_cache.clear()  # Also clear scaled cache to force refresh
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def reset_enhancements(self):
        # Block signals to prevent triggering toggle functions during reset
        if hasattr(self, 'grayscale_slider') and self.grayscale_slider is not None:
            self.grayscale_slider.blockSignals(True)
            self.grayscale_slider.setValue(0)
            self.grayscale_slider.blockSignals(False)
        
        if hasattr(self, 'contrast_slider') and self.contrast_slider is not None:
            self.contrast_slider.blockSignals(True)
            self.contrast_slider.setValue(50)
            self.contrast_slider.blockSignals(False)
        
        if hasattr(self, 'gamma_slider') and self.gamma_slider is not None:
            self.gamma_slider.blockSignals(True)
            self.gamma_slider.setValue(0)
            self.gamma_slider.blockSignals(False)
        
        if hasattr(self, 'lut_strength_slider') and self.lut_strength_slider is not None:
            self.lut_strength_slider.blockSignals(True)
            self.lut_strength_slider.setValue(100)
            self.lut_strength_slider.blockSignals(False)
        
        if hasattr(self, 'lut_combo') and self.lut_combo is not None:
            self.lut_combo.blockSignals(True)
            self.lut_combo.setCurrentText("None")
            self.lut_combo.blockSignals(False)
        
        self.grayscale_value = 0
        self.contrast_value = 50
        self.gamma_value = 0
        self.current_lut = None
        self.current_lut_name = "None"
        self.lut_strength = 100
        
        # Update toggle button states (block signals to prevent loops)
        if hasattr(self, 'grayscale_toggle_btn') and self.grayscale_toggle_btn is not None:
            self.grayscale_toggle_btn.blockSignals(True)
            self.grayscale_toggle_btn.setChecked(False)
            self.grayscale_toggle_btn.blockSignals(False)
        
        if hasattr(self, 'contrast_toggle_btn') and self.contrast_toggle_btn is not None:
            self.contrast_toggle_btn.blockSignals(True)
            self.contrast_toggle_btn.setChecked(False)
            self.contrast_toggle_btn.blockSignals(False)
        
        if hasattr(self, 'gamma_toggle_btn') and self.gamma_toggle_btn is not None:
            self.gamma_toggle_btn.blockSignals(True)
            self.gamma_toggle_btn.setChecked(False)
            self.gamma_toggle_btn.blockSignals(False)
        
        # Clear all caches when resetting
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        
        # CRITICAL: Clear zoom optimization cache when resetting enhancements
        if hasattr(self, '_lut_process_cache'):
            self._lut_process_cache.clear()
        if hasattr(self, '_last_processed_image'):
            self._last_processed_image = None
        self._last_processed_has_lut = False
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def choose_lut_folder(self):
        """Choose a folder containing CUBE LUT files"""
        # Prefer previously chosen LUT folder; else default LUT path; else ONLY then fall back to image folder
        if self.lut_folder and os.path.isdir(self.lut_folder):
            start_dir = self.lut_folder
        elif hasattr(self, 'default_lut_path') and self.default_lut_path and os.path.isdir(self.default_lut_path):
            start_dir = self.default_lut_path
        elif self.folder and os.path.isdir(self.folder):
            start_dir = self.folder  # final fallback
        else:
            start_dir = ""

        folder = QFileDialog.getExistingDirectory(self, "Select LUT Folder (will search subfolders)", start_dir)
        if folder:
            self.lut_folder = folder
            
            # Show scanning status
            self.status.showMessage(f"Scanning {os.path.basename(folder)} and subfolders for CUBE files...")
            QApplication.processEvents()  # Allow UI to update
            
            self.lut_files = self.scan_lut_folder(folder)
            self.update_lut_combo()
            
            # Count subfolders searched
            subfolder_count = 0
            try:
                for root, dirs, files in os.walk(folder):
                    if root != folder:  # Don't count the root folder itself
                        subfolder_count += 1
            except:
                subfolder_count = 0
            
            if subfolder_count > 0:
                self.status.showMessage(f"Found {len(self.lut_files)} LUT files in {os.path.basename(folder)} (+{subfolder_count} subfolders)")
            else:
                self.status.showMessage(f"Found {len(self.lut_files)} LUT files in {os.path.basename(folder)}")

    def update_lut_combo(self):
        """Update the LUT combo box with available LUT files"""
        if hasattr(self, 'lut_combo'):
            self.lut_combo.blockSignals(True)
            self.lut_combo.clear()
            self.lut_combo.addItem("None")
            
            for lut_file in self.lut_files:
                # Create a display name that shows subfolder structure
                relative_path = os.path.relpath(lut_file, self.lut_folder)
                
                # Remove the .cube extension and use forward slashes for consistency
                display_name = os.path.splitext(relative_path)[0].replace('\\', '/')
                
                # If it's just a filename (no subfolder), show only the name
                if '/' not in display_name:
                    display_name = os.path.basename(display_name)
                
                self.lut_combo.addItem(display_name)
            
            self.lut_combo.blockSignals(False)

    def apply_selected_lut(self, lut_name):
        """Apply the selected LUT from the combo box with fast preview"""
        if lut_name == "None" or not lut_name:
            self.current_lut = None
            self.current_lut_name = "None"
            self.lut_enabled = False  # Disable LUT when "None" is selected
            self.status.showMessage("LUT disabled")
            # Sync toggle button state
            if hasattr(self, 'lut_toggle_btn'):
                self.lut_toggle_btn.blockSignals(True)
                self.lut_toggle_btn.setChecked(False)
                self.lut_toggle_btn.blockSignals(False)
        else:
            # Show loading status immediately
            self.status.showMessage(f"Loading LUT: {lut_name}...")
            QApplication.processEvents()  # Allow UI to update
            
            # Find the full path for this LUT name (handling subfolder structure)
            lut_file_found = None
            for lut_file in self.lut_files:
                # Create the same display name format as in update_lut_combo
                relative_path = os.path.relpath(lut_file, self.lut_folder)
                display_name = os.path.splitext(relative_path)[0].replace('\\', '/')
                
                # If it's just a filename (no subfolder), show only the name
                if '/' not in display_name:
                    display_name = os.path.basename(display_name)
                
                if display_name == lut_name:
                    lut_file_found = lut_file
                    break
            
            if lut_file_found:
                # Check if LUT is already cached
                if hasattr(self, 'lut_cache') and lut_file_found in self.lut_cache:
                    self.current_lut = self.lut_cache[lut_file_found]
                    self.current_lut_name = lut_name
                    lut_size = self.current_lut['size']
                    self.status.showMessage(f"LUT loaded (cached): {lut_name} ({lut_size}³)")
                else:
                    # Load new LUT
                    self.current_lut = self.load_cube_lut(lut_file_found)
                    self.current_lut_name = lut_name
                    
                    # Cache the loaded LUT
                    if not hasattr(self, 'lut_cache'):
                        self.lut_cache = {}
                    if self.current_lut:
                        self.lut_cache[lut_file_found] = self.current_lut
                        lut_size = self.current_lut['size']
                        self.status.showMessage(f"LUT loaded: {lut_name} ({lut_size}³)")
                    else:
                        self.status.showMessage(f"Failed to load LUT: {lut_name}")
                        self.current_lut_name = "None"
                        self.lut_enabled = False  # Disable when LUT fails to load
                        # Reset combo box to "None" if loading failed
                        if hasattr(self, 'lut_combo'):
                            self.lut_combo.blockSignals(True)
                            self.lut_combo.setCurrentText("None")
                            self.lut_combo.blockSignals(False)
            else:
                self.status.showMessage(f"LUT file not found: {lut_name}")
                self.current_lut = None
                self.current_lut_name = "None"
                self.lut_enabled = False  # Disable when LUT file not found
            # Sync toggle button state when a LUT successfully loaded
            if self.current_lut_name != "None" and hasattr(self, 'lut_toggle_btn'):
                self.lut_toggle_btn.blockSignals(True)
                self.lut_toggle_btn.setChecked(True)
                self.lut_toggle_btn.blockSignals(False)
                # IMPORTANT: Also set the internal enabled flag when LUT is loaded
                self.lut_enabled = True
        
        # Clear caches and update display with progressive preview
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        if hasattr(self, '_lut_process_cache'):
            self._lut_process_cache.clear()  # Clear LUT cache when LUT changes
        
        # CRITICAL: Clear zoom optimization cache when LUT changes to prevent wrong LUT being applied during pan/zoom
        if hasattr(self, '_last_processed_image'):
            self._last_processed_image = None
        self._last_processed_has_lut = False
        
        if self.current_image:
            # Show immediate preview with fast processing for responsiveness
            if self.current_lut:
                self.status.showMessage(f"Applying {lut_name}... (instant preview)")
                QApplication.processEvents()
                
                # Create fast preview first (smaller image, low quality)
                self._create_fast_lut_preview()
            
            # Then apply full quality in background with progress
            QTimer.singleShot(10, self._apply_full_quality_lut)

    def toggle_lut_enabled(self, checked):
        """Toggle current LUT on/off without losing selection."""
        # If turning off, remember current selection (if any) and switch combo to None
        if not checked:
            self.lut_enabled = False
            if getattr(self, 'current_lut_name', 'None') != 'None':
                self._saved_lut_selection = self.current_lut_name
            if hasattr(self, 'lut_combo'):
                self.lut_combo.blockSignals(True)
                self.lut_combo.setCurrentText("None")
                self.lut_combo.blockSignals(False)
            self.apply_selected_lut("None")
            # Force immediate redraw WITHOUT LUT (previous enhanced cache may contain LUT-applied pixmaps)
            try:
                if hasattr(self, 'enhancement_cache'): self.enhancement_cache.clear()
                if hasattr(self, 'scaled_cache'): self.scaled_cache.clear()
                if hasattr(self, '_lut_process_cache'): self._lut_process_cache.clear()
                if hasattr(self, '_last_processed_image'): self._last_processed_image = None
                self._last_processed_has_lut = False
                # Do NOT clear base pixmap_cache so we avoid re-reading image from disk
                if self.current_image:
                    self.display_image(self.current_image)
            except Exception as e:
                print(f"toggle_lut_enabled redraw failure: {e}")
            return
        # Turning on: restore previously saved selection if available
        self.lut_enabled = True
        target = getattr(self, '_saved_lut_selection', None)
        if target and hasattr(self, 'lut_combo'):
            if self.lut_combo.findText(target) >= 0:
                self.lut_combo.blockSignals(True)
                self.lut_combo.setCurrentText(target)
                self.lut_combo.blockSignals(False)
                self.apply_selected_lut(target)
                return
        # If no saved selection, do nothing (button will remain on but no LUT)
        if hasattr(self, 'lut_toggle_btn') and self.current_lut_name == 'None':
            # No LUT to enable; uncheck to reflect reality
            self.lut_toggle_btn.blockSignals(True)
            self.lut_toggle_btn.setChecked(False)
            self.lut_toggle_btn.blockSignals(False)

    def _create_fast_lut_preview(self):
        """Create an instant high-quality preview optimized for display size"""
        if not self.current_image or not self.current_lut:
            print("DEBUG: No current image or LUT for preview")
            return
            
        try:
            # Load base image quickly
            if self.current_image in self.pixmap_cache:
                base_pixmap = self.pixmap_cache[self.current_image]
            else:
                base_pixmap, error = safe_load_pixmap(self.current_image)
                if error:
                    return
            
            # ENHANCED PREVIEW SIZING: When lines are present, maintain higher quality
            has_lines = (self.lines_visible and 
                        (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines))
            
            display_width = self.image_label.width()
            display_height = self.image_label.height()
            zoom_factor = getattr(self.image_label, 'zoom_factor', 1.0)
            
            # Calculate the effective display size considering zoom
            effective_width = int(display_width * zoom_factor)
            effective_height = int(display_height * zoom_factor)
            
            # IMPROVED QUALITY: Use higher resolution preview when lines are present
            if has_lines:
                # When lines are present, use higher quality to maintain line clarity
                if effective_width > 1200 or effective_height > 800:
                    # Very high quality for large displays with lines
                    preview_size = min(1600, 
                                     int(base_pixmap.width() * 0.8), 
                                     int(base_pixmap.height() * 0.8))
                elif effective_width > 800 or effective_height > 600:
                    # High quality for medium displays with lines
                    preview_size = min(1200, 
                                     int(base_pixmap.width() * 0.75), 
                                     int(base_pixmap.height() * 0.75))
                else:
                    # Medium quality for smaller displays with lines
                    preview_size = min(900, 
                                     int(base_pixmap.width() * 0.6), 
                                     int(base_pixmap.height() * 0.6))
                transform_quality = Qt.SmoothTransformation  # Always use smooth for lines
            else:
                # Standard quality sizing for no lines
                if effective_width > 1200 or effective_height > 800:
                    preview_size = min(1200, 
                                     int(base_pixmap.width() * 0.67), 
                                     int(base_pixmap.height() * 0.67))
                    transform_quality = Qt.SmoothTransformation
                elif effective_width > 800 or effective_height > 600:
                    preview_size = min(900, 
                                     base_pixmap.width() // 2, 
                                     base_pixmap.height() // 2)
                    transform_quality = Qt.SmoothTransformation
                else:
                    preview_size = min(600, 
                                     base_pixmap.width() // 3, 
                                     base_pixmap.height() // 3)
                    transform_quality = Qt.FastTransformation
            
            # Scale with appropriate quality
            fast_preview = base_pixmap.scaled(
                preview_size, preview_size,
                Qt.KeepAspectRatio, transform_quality
            )
            
            # IMPORTANT: Apply LUT using GPU acceleration when available
            lut_dict = {
                'data': self.current_lut['data'],
                'size': self.current_lut['size'],
                'file_path': getattr(self.current_lut, 'file_path', 'preview')
            }
            
            # Use GPU acceleration for preview if available - ENHANCED for lines
            if (self.gpu_processor.is_available() and 
                fast_preview.width() * fast_preview.height() > 150000) or \
               (has_lines and self.gpu_processor.is_available() and 
                fast_preview.width() * fast_preview.height() > 50000):
                
                # Force GPU for previews with lines (much lower threshold)
                print(f"Using GPU for fast LUT preview ({fast_preview.width()}x{fast_preview.height()}, lines: {has_lines})")
                
                # Convert pixmap to image for GPU processing
                preview_image = fast_preview.toImage()
                if preview_image.format() != preview_image.Format.Format_RGB32:
                    preview_image = preview_image.convertToFormat(preview_image.Format.Format_RGB32)
                
                # Apply LUT using GPU
                gpu_result = self.gpu_processor.apply_lut_gpu(
                    preview_image, 
                    lut_dict['data'], 
                    lut_dict['size'], 
                    self.lut_strength / 100.0
                )
                
                if gpu_result is not None:
                    fast_preview = QPixmap.fromImage(gpu_result)
                else:
                    # Fallback to CPU if GPU fails
                    print("GPU preview failed, falling back to CPU")
                    fast_preview = self.apply_lut_to_image(fast_preview, lut_dict, self.lut_strength)
            else:
                # Use CPU LUT processing for smaller previews
                fast_preview = self.apply_lut_to_image(fast_preview, lut_dict, self.lut_strength)
            
            # Apply basic transformations (rotation, flips) with appropriate quality
            fast_preview = self._apply_quick_transforms(fast_preview, transform_quality)
            
            # Scale to display size and show immediately
            final_preview = self._scale_pixmap(fast_preview, self.current_image)
            # Apply lines after LUT preview scaling if they should be visible
            if (self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines)):
                # Temporarily set pixmap then fast overlay
                self.image_label.setPixmap(final_preview)
                if hasattr(self, '_fast_line_update'):
                    self._fast_line_update()
                else:
                    final_preview = self._add_lines_to_pixmap(final_preview)
            else:
                self.image_label.setPixmap(final_preview)
            QApplication.processEvents()
            
        except Exception as e:
            print(f"Error creating fast preview: {e}")
            import traceback
            traceback.print_exc()

    def _apply_full_quality_lut(self):
        """Apply full quality LUT processing asynchronously to prevent freezing"""
        if not self.current_image or not self.current_lut:
            return
            
        try:
            # Update status to show full quality processing
            lut_name = self.current_lut_name if self.current_lut_name != "None" else "LUT"
            self.status.showMessage(f"Applying {lut_name}... (full quality)")
            QApplication.processEvents()
            
            # Start async chunked processing to prevent any freezing
            self._start_async_lut_processing()
            
        except Exception as e:
            print(f"Error in full quality LUT processing: {e}")
            self.status.showMessage("LUT processing error - using preview")

    def _start_async_lut_processing(self):
        """Start asynchronous LUT processing to prevent any UI freezing"""
        if not self.current_image or not self.current_lut:
            return
        
        # Check if we're already processing the same image/LUT combination
        current_cache_key = self._get_lut_cache_key()
        if (hasattr(self, '_async_processing_state') and 
            self._async_processing_state and 
            hasattr(self._async_processing_state, 'cache_key') and
            self._async_processing_state['cache_key'] == current_cache_key):
            # Already processing the same LUT combination - don't restart
            print("LUT processing already in progress for this image/LUT combination")
            return
        
        # Stop any existing processing for different image/LUT combination
        if hasattr(self, '_async_processing_state') and self._async_processing_state:
            if hasattr(self, '_async_processing_timer'):
                self._async_processing_timer.stop()
            self._async_processing_state = None
            
        try:
            # Load base image
            if self.current_image in self.pixmap_cache:
                base_pixmap = self.pixmap_cache[self.current_image]
            else:
                base_pixmap, error = safe_load_pixmap(self.current_image)
                if error:
                    self.status.showMessage("Error loading image for LUT processing")
                    return
                # Cache the loaded image
                self._manage_cache(self.pixmap_cache, self.current_image, base_pixmap)
            
            # Convert to image for processing
            image = base_pixmap.toImage()
            if image.format() != image.Format.Format_RGB32:
                image = image.convertToFormat(image.Format.Format_RGB32)
            
            # GPU ACCELERATION: Try GPU processing first - LOWER threshold for better performance
            # Use GPU for any image larger than 250k pixels (500x500) - especially important with lines
            gpu_threshold = 250000  # Reduced from 500,000 to ensure GPU is used more often
            
            # IMPORTANT: Use GPU processing even when lines are present
            has_lines = (self.lines_visible and 
                        (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines))
            
            # If lines are present, FORCE GPU processing for better performance (no freezing)
            if has_lines:
                gpu_threshold = 50000  # Very aggressive threshold when lines are present
                print(f"Lines detected - using very aggressive GPU processing (threshold: {gpu_threshold})")
            else:
                gpu_threshold = 150000  # Still lower than default for better performance
            
            if self.gpu_processor.is_available() and image.width() * image.height() > gpu_threshold:
                print(f"Using GPU for async LUT processing ({image.width()}x{image.height()}, lines: {has_lines})")
                
                # Use GPU processing
                lut_data = self.current_lut['data']
                lut_size = self.current_lut['size']
                strength_factor = self.lut_strength / 100.0
                
                try:
                    processed_image = self.gpu_processor.apply_lut_gpu(image, lut_data, lut_size, strength_factor)
                    if processed_image is not None:
                        # GPU processing successful - convert to pixmap and finalize immediately
                        processed_pixmap = QPixmap.fromImage(processed_image)
                        
                        # Store final processing state for finalization
                        self._final_processing_state = {
                            'pixmap': processed_pixmap,
                            'processing_time': 0.1  # GPU is very fast
                        }
                        
                        # Update status and finalize immediately
                        if has_lines:
                            self.status.showMessage("GPU LUT processing complete (with lines) - finalizing...")
                        else:
                            self.status.showMessage("GPU LUT processing complete - finalizing...")
                        QApplication.processEvents()
                        
                        # Call finalization directly - no delay needed for GPU
                        self._async_finalize_step()
                        return
                except Exception as e:
                    print(f"GPU async processing failed: {e}, falling back to CPU")
            else:
                # Debug: Show why GPU wasn't used
                if not self.gpu_processor.is_available():
                    print("GPU not available - using CPU processing")
                    print(f"GPU status: {self.gpu_processor.get_device_info()}")
                else:
                    print(f"Image too small for GPU processing: {image.width() * image.height()} pixels (threshold: {gpu_threshold}, lines: {has_lines})")
                    print(f"GPU device available: {self.gpu_processor.get_device_info()}")
            
            # FALLBACK: CPU async processing with enhanced chunking when lines are present
            print(f"Starting CPU async processing (lines present: {has_lines})")
            
            # When lines are present, use smaller chunks to prevent freezing
            chunk_size = 4 if has_lines else 8  # Smaller chunks when lines are present
            
            # Setup async processing state with cache key tracking
            self._async_processing_state = {
                'image': image,
                'width': image.width(),
                'height': image.height(),
                'current_row': 0,
                'total_rows': image.height(),
                'chunk_size': chunk_size,  # Use smaller chunks when lines are present
                'lut_data': self.current_lut['data'],
                'lut_size': self.current_lut['size'],
                'strength_factor': self.lut_strength / 100.0,
                'start_time': time.time(),
                'cache_key': current_cache_key  # Track what we're processing
            }
            
            # Start the async processing timer
            if not hasattr(self, '_async_processing_timer'):
                self._async_processing_timer = QTimer()
                self._async_processing_timer.timeout.connect(self._process_lut_chunk)
            
            # Process first chunk immediately, then continue with timer
            self._process_lut_chunk()
            self._async_processing_timer.start(1)  # 1ms interval for smooth processing
            
        except Exception as e:
            print(f"Error starting async LUT processing: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_lut_chunk(self):
        """Process a small chunk of the image asynchronously"""
        if not hasattr(self, '_async_processing_state') or not self._async_processing_state:
            if hasattr(self, '_async_processing_timer'):
                self._async_processing_timer.stop()
            return
            
        try:
            state = self._async_processing_state
            image = state['image']
            current_row = state['current_row']
            chunk_size = state['chunk_size']
            width = state['width']
            height = state['height']
            lut_data = state['lut_data']
            lut_size = state['lut_size']
            strength_factor = state['strength_factor']
            
            # Process chunk_size rows with yield points for responsiveness
            end_row = min(current_row + chunk_size, height)
            
            # Check if lines are present for more frequent yield points
            has_lines = (self.lines_visible and 
                        (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines))
            pixels_processed = 0
            yield_frequency = 2000 if has_lines else 5000  # More frequent yields with lines
            
            for y in range(current_row, end_row):
                scan_line = image.scanLine(y)
                
                for x in range(width):
                    offset = x * 4
                    
                    # Read pixel bytes (BGRA order in Qt)
                    b = scan_line[offset]
                    g = scan_line[offset + 1] 
                    r = scan_line[offset + 2]
                    a = scan_line[offset + 3]
                    
                    # Normalize to 0-1 range
                    r_norm = r / 255.0
                    g_norm = g / 255.0
                    b_norm = b / 255.0
                    
                    # Apply LUT with quality interpolation
                    lut_result = self._interpolate_lut_quality(r_norm, g_norm, b_norm, lut_data, lut_size)
                    
                    # Blend with original using strength factor
                    final_r = r_norm * (1.0 - strength_factor) + lut_result[0] * strength_factor
                    final_g = g_norm * (1.0 - strength_factor) + lut_result[1] * strength_factor
                    final_b = b_norm * (1.0 - strength_factor) + lut_result[2] * strength_factor
                    
                    # Clamp and convert back to bytes
                    final_r = max(0, min(255, int(final_r * 255 + 0.5)))
                    final_g = max(0, min(255, int(final_g * 255 + 0.5)))
                    final_b = max(0, min(255, int(final_b * 255 + 0.5)))
                    
                    # Write back to image (BGRA order)
                    scan_line[offset] = final_b
                    scan_line[offset + 1] = final_g
                    scan_line[offset + 2] = final_r
                    scan_line[offset + 3] = a
                    
                    # Yield control more frequently when lines are present
                    pixels_processed += 1
                    if pixels_processed >= yield_frequency:
                        # Allow Qt event processing to prevent freezing
                        QApplication.processEvents()
                        pixels_processed = 0
            
            # Update progress
            state['current_row'] = end_row
            progress = (end_row / height) * 100
            
            # Update status every few chunks
            if end_row % (chunk_size * 3) == 0 or end_row >= height:
                lut_name = self.current_lut_name if self.current_lut_name != "None" else "LUT"
                self.status.showMessage(f"Applying {lut_name}... {progress:.0f}%")
            
            # Check if processing is complete
            if end_row >= height:
                self._finish_async_lut_processing()
                
        except Exception as e:
            print(f"Error in LUT chunk processing: {e}")
            import traceback
            traceback.print_exc()
            # Stop processing on error
            if hasattr(self, '_async_processing_timer'):
                self._async_processing_timer.stop()
            self._async_processing_state = None
    
    def _finish_async_lut_processing(self):
        """Complete the async LUT processing and display the result - NOW FULLY ASYNC"""
        try:
            if hasattr(self, '_async_processing_timer'):
                self._async_processing_timer.stop()
            
            if not hasattr(self, '_async_processing_state') or not self._async_processing_state:
                return
                
            state = self._async_processing_state
            processed_image = state['image']
            
            # Convert back to pixmap
            processed_pixmap = QPixmap.fromImage(processed_image)
            
            # REMOVED: Don't cache here - cache at the END after lines are added
            # The cache will be updated in the final step with the complete image
            
            # INSTANT FINALIZATION: Complete synchronously for maximum speed
            self.status.showMessage("Finalizing LUT...")
            
            # Store final processing state
            self._final_processing_state = {
                'pixmap': processed_pixmap,
                'processing_time': time.time() - state['start_time']
            }
            
            # Clear the main processing state 
            self._async_processing_state = None
            
            # Call finalization immediately - NO delay for instant completion
            self._async_finalize_step()
            
        except Exception as e:
            print(f"Error finishing async LUT processing: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to current display
            self.status.showMessage("LUT processing completed with errors")
            self._async_processing_state = None
    
    def _async_finalize_step(self):
        """Process final LUT steps instantly - ZERO delay completion"""
        if not hasattr(self, '_final_processing_state') or not self._final_processing_state:
            return
            
        try:
            state = self._final_processing_state
            processed_pixmap = state['pixmap']
            
            # INSTANT FINALIZATION: Complete everything synchronously in one go
            self.status.showMessage("Finalizing LUT...")
            
            # Apply ALL transformations immediately
            if self.rotation_angle != 0:
                transform = QTransform()
                transform.rotate(self.rotation_angle)
                processed_pixmap = processed_pixmap.transformed(transform, Qt.SmoothTransformation)
            
            if self.flipped_h:
                processed_pixmap = processed_pixmap.transformed(QTransform().scale(-1, 1), Qt.SmoothTransformation)
            if self.flipped_v:
                processed_pixmap = processed_pixmap.transformed(QTransform().scale(1, -1), Qt.SmoothTransformation)
            
            if (self.grayscale_value != 0 or self.contrast_value != 50 or self.gamma_value != 0):
                processed_pixmap = self.apply_fast_enhancements(processed_pixmap)
            
            if (self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines)):
                processed_pixmap = self._add_lines_to_pixmap(processed_pixmap)
            
            # Scale, display and cache immediately - NO DELAYS
            final_pixmap = self._scale_pixmap(processed_pixmap, self.current_image)
            self.image_label.setPixmap(final_pixmap)
            # Reapply lines post-scale to avoid being lost by scaling
            if (self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines)) and hasattr(self, '_fast_line_update'):
                self._fast_line_update()
            
            # Update cache with complete processed image
            cache_key = self._get_lut_cache_key()
            if cache_key:
                if not hasattr(self, '_lut_process_cache'):
                    self._lut_process_cache = {}
                
                self._lut_process_cache[cache_key] = processed_pixmap.copy()
                
                # Manage cache size (keep max 3 processed images for memory)
                max_cache_size = 3
                if len(self._lut_process_cache) > max_cache_size:
                    oldest_key = next(iter(self._lut_process_cache))
                    del self._lut_process_cache[oldest_key]
            
            # Instant completion status
            processing_time = state['processing_time']
            final_msg = f"LUT applied: {self.current_lut_name} ({processing_time:.1f}s) - INSTANT completion!"
            self.status.showMessage(final_msg)
            
            # Clear finalization state immediately
            self._final_processing_state = None
                
        except Exception as e:
            print(f"Error in instant finalization: {e}")
            import traceback
            traceback.print_exc()
            self.status.showMessage("LUT finalization completed with errors")
            self._final_processing_state = None
    
    def _add_lines_to_pixmap(self, pixmap):
        """Add drawn lines to a pixmap with GPU acceleration when available"""
        if not pixmap or pixmap.isNull():
            return pixmap
            
        if not (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
            return pixmap
            
        try:
            # Try GPU acceleration first for better performance
            if (self.gpu_processor.is_available() and 
                pixmap.width() * pixmap.height() > 100000):  # Use GPU for images > 100k pixels
                
                print(f"Using GPU for line drawing ({pixmap.width()}x{pixmap.height()})")
                
                # Prepare line data with proper scaling
                scale_x = 1.0
                scale_y = 1.0
                
                if hasattr(self, 'original_pixmap') and self.original_pixmap:
                    original_size = self.original_pixmap.size()
                    current_size = pixmap.size()
                    scale_x = current_size.width() / original_size.width()
                    scale_y = current_size.height() / original_size.height()
                
                # Scale line coordinates for GPU
                scaled_vertical = [int(x * scale_x) for x in self.drawn_lines] if self.drawn_lines else []
                scaled_horizontal = [int(y * scale_y) for y in self.drawn_horizontal_lines] if self.drawn_horizontal_lines else []
                
                scaled_free_lines = []
                if self.drawn_free_lines:
                    for line in self.drawn_free_lines:
                        start_x, start_y = line['start']
                        end_x, end_y = line['end']
                        scaled_free_lines.append({
                            'start': (int(start_x * scale_x), int(start_y * scale_y)),
                            'end': (int(end_x * scale_x), int(end_y * scale_y))
                        })
                
                # Convert pixmap to image for GPU processing
                image = pixmap.toImage()
                if image.format() != image.Format.Format_RGBA8888:
                    image = image.convertToFormat(image.Format.Format_RGBA8888)
                
                # Try GPU line drawing
                gpu_result = self.gpu_processor.draw_lines_gpu(
                    image,
                    scaled_vertical,
                    scaled_horizontal, 
                    scaled_free_lines,
                    self.line_color,
                    self.line_thickness
                )
                
                if gpu_result is not None:
                    print("GPU line drawing successful")
                    return gpu_result
                else:
                    print("GPU line drawing failed, falling back to CPU")
            
            # Fallback to CPU line drawing
            print(f"Using CPU for line drawing ({pixmap.width()}x{pixmap.height()})")
            final_pixmap = pixmap.copy()
            painter = QPainter(final_pixmap)
            painter.setRenderHint(QPainter.Antialiasing, False)
            
            # Use user-selected color and thickness
            pen_color = self.line_color
            pen_thickness = self.line_thickness
            painter.setPen(QPen(pen_color, pen_thickness, Qt.SolidLine))
            
            # Get basic scale factors (simplified approach)
            if hasattr(self, 'original_pixmap') and self.original_pixmap:
                original_size = self.original_pixmap.size()
                current_size = pixmap.size()
                scale_x = current_size.width() / original_size.width()
                scale_y = current_size.height() / original_size.height()
            else:
                scale_x = 1.0
                scale_y = 1.0
            
            # Draw simple lines (basic version for async processing)
            for x in self.drawn_lines:
                display_x = int(x * scale_x)
                if 0 <= display_x < final_pixmap.width():
                    painter.drawLine(display_x, 0, display_x, final_pixmap.height())
            
            for y in self.drawn_horizontal_lines:
                display_y = int(y * scale_y)
                if 0 <= display_y < final_pixmap.height():
                    painter.drawLine(0, display_y, final_pixmap.width(), display_y)
            
            for line in self.drawn_free_lines:
                start_x, start_y = line['start']
                end_x, end_y = line['end']
                
                display_start_x = int(start_x * scale_x)
                display_start_y = int(start_y * scale_y)
                display_end_x = int(end_x * scale_x)
                display_end_y = int(end_y * scale_y)
                
                painter.drawLine(display_start_x, display_start_y, display_end_x, display_end_y)
            
            painter.end()
            return final_pixmap
            
        except Exception as e:
            print(f"Error adding lines to pixmap: {e}")
            return pixmap

    def _display_image_with_lut_preview(self, img_path):
        """Display image with smart LUT preview handling to prevent freezing"""
        if self.current_lut and self.lut_strength > 0:
            # If LUT is active, use instant preview system
            self.current_image = img_path  # Set this first
            
            # Show instant fast preview
            self.status.showMessage(f"Loading image with {self.current_lut_name}... (instant preview)")
            QApplication.processEvents()
            
            # Create fast preview first
            self._create_fast_image_lut_preview(img_path)
            
            # Then apply full quality in background  
            QTimer.singleShot(15, lambda: self._apply_full_quality_to_current_image())
        else:
            # No LUT active, use normal fast display
            self.display_image(img_path)

    def _create_fast_image_lut_preview(self, img_path):
        """Create instant preview for new image with LUT - Enhanced GPU quality"""
        try:
            # Load base image quickly
            if img_path in self.pixmap_cache:
                base_pixmap = self.pixmap_cache[img_path]
            else:
                base_pixmap, error = safe_load_pixmap(img_path)
                if error:
                    self.display_image(img_path)  # Fallback to normal display
                    return
                # Cache it for future use
                self._manage_cache(self.pixmap_cache, img_path, base_pixmap)
            
            # ENHANCED PREVIEW: Better quality when lines are present
            has_lines = (self.lines_visible and 
                        (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines))
            
            if has_lines:
                # Higher quality preview when lines are present
                preview_size = min(1000, base_pixmap.width() // 1.5, base_pixmap.height() // 1.5)
                transform_quality = Qt.SmoothTransformation
            else:
                # Standard quality for no lines
                preview_size = min(600, base_pixmap.width() // 2, base_pixmap.height() // 2)
                transform_quality = Qt.FastTransformation
            
            fast_preview = base_pixmap.scaled(
                preview_size, preview_size,
                Qt.KeepAspectRatio, transform_quality
            )
            
            # Apply LUT using GPU acceleration when available
            if self.current_lut:
                lut_dict = {
                    'data': self.current_lut['data'],
                    'size': self.current_lut['size'],
                    'file_path': getattr(self.current_lut, 'file_path', 'preview')
                }
                
                # Use GPU for better quality when available - ENHANCED for lines
                if (self.gpu_processor.is_available() and 
                    fast_preview.width() * fast_preview.height() > 100000) or \
                   (has_lines and self.gpu_processor.is_available() and 
                    fast_preview.width() * fast_preview.height() > 30000):
                    
                    # Very aggressive GPU usage when lines are present
                    print(f"Using GPU for fast image LUT preview ({fast_preview.width()}x{fast_preview.height()}, lines: {has_lines})")
                    
                    # Convert pixmap to image for GPU processing
                    preview_image = fast_preview.toImage()
                    if preview_image.format() != preview_image.Format.Format_RGB32:
                        preview_image = preview_image.convertToFormat(preview_image.Format.Format_RGB32)
                    
                    # Apply LUT using GPU
                    gpu_result = self.gpu_processor.apply_lut_gpu(
                        preview_image, 
                        lut_dict['data'], 
                        lut_dict['size'], 
                        self.lut_strength / 100.0
                    )
                    
                    if gpu_result is not None:
                        fast_preview = QPixmap.fromImage(gpu_result)
                    else:
                        # Fallback to CPU if GPU fails
                        print("GPU image preview failed, falling back to CPU")
                        fast_preview = self.apply_lut_to_image(fast_preview, lut_dict, self.lut_strength)
                else:
                    # Use CPU LUT processing for smaller previews
                    fast_preview = self.apply_lut_to_image(fast_preview, lut_dict, self.lut_strength)
            
            # Apply basic transformations (rotation, flips)
            fast_preview = self._apply_quick_transforms(fast_preview, transform_quality)
            
            # Scale to display size and show immediately
            final_preview = self._scale_pixmap(fast_preview, img_path)
            self.image_label.setPixmap(final_preview)
            QApplication.processEvents()
            
        except Exception as e:
            print(f"Error creating fast image preview: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to normal display
            self.display_image(img_path)

    def _apply_quick_transforms(self, pixmap, quality=Qt.FastTransformation):
        """Apply rotation and flips with specified quality for preview"""
        if not pixmap or pixmap.isNull():
            return pixmap
            
        # Apply rotation if needed
        if self.rotation_angle != 0:
            transform = QTransform()
            transform.rotate(self.rotation_angle)
            pixmap = pixmap.transformed(transform, quality)
        
        # Apply flips if needed
        if self.flipped_h:
            pixmap = pixmap.transformed(QTransform().scale(-1, 1), quality)
        if self.flipped_v:
            pixmap = pixmap.transformed(QTransform().scale(1, -1), quality)
            
        return pixmap

    def _apply_full_quality_to_current_image(self):
        """Apply full quality processing to the current image"""
        if self.current_image:
            self.display_image(self.current_image)

    def _apply_ultra_fast_lut(self, pixmap):
        """Ultra-fast LUT application for instant preview (sacrifices quality for speed)"""
        if not self.current_lut or not pixmap or pixmap.isNull():
            return pixmap
            
        try:
            image = pixmap.toImage()
            if image.isNull():
                return pixmap
                
            # Convert to fast format
            if image.format() != image.Format.Format_RGB32:
                image = image.convertToFormat(image.Format.Format_RGB32)
            
            width = image.width()
            height = image.height()
            lut_data = self.current_lut['data']
            lut_size = self.current_lut['size']
            strength_factor = self.lut_strength / 100.0
            
            # Ultra-fast processing: sample every 2nd pixel for better quality preview
            sample_rate = 2  # Reduced from 4 to 2 for better quality
            
            for y in range(0, height, sample_rate):
                scan_line = image.scanLine(y)
                
                for x in range(0, width, sample_rate):
                    offset = x * 4
                    
                    # Read pixel
                    b = scan_line[offset]
                    g = scan_line[offset + 1]
                    r = scan_line[offset + 2]
                    a = scan_line[offset + 3]
                    
                    # Normalize and apply nearest-neighbor LUT lookup
                    r_norm = r / 255.0
                    g_norm = g / 255.0
                    b_norm = b / 255.0
                    
                    # Fast nearest-neighbor lookup
                    lut_result = self._nearest_neighbor_lut(r_norm, g_norm, b_norm, lut_data, lut_size)
                    
                    # Blend and write back
                    final_r = int((r_norm * (1.0 - strength_factor) + lut_result[0] * strength_factor) * 255)
                    final_g = int((g_norm * (1.0 - strength_factor) + lut_result[1] * strength_factor) * 255)
                    final_b = int((b_norm * (1.0 - strength_factor) + lut_result[2] * strength_factor) * 255)
                    
                    # Clamp values
                    final_r = max(0, min(255, final_r))
                    final_g = max(0, min(255, final_g))
                    final_b = max(0, min(255, final_b))
                    
                    # Write to current pixel
                    scan_line[offset] = final_b
                    scan_line[offset + 1] = final_g
                    scan_line[offset + 2] = final_r
                    scan_line[offset + 3] = a
                    
                    # Fill adjacent pixel for smoother result (only horizontally)
                    if x + 1 < width:
                        next_offset = (x + 1) * 4
                        scan_line[next_offset] = final_b
                        scan_line[next_offset + 1] = final_g
                        scan_line[next_offset + 2] = final_r
                        scan_line[next_offset + 3] = scan_line[next_offset + 3]
                
                # Fill the next row with same data for smoother preview
                if y + 1 < height:
                    next_line = image.scanLine(y + 1)
                    # Copy current line to next line for smoother blocks
                    for x in range(0, width, sample_rate):
                        if x < width:
                            src_offset = x * 4
                            # Only copy processed pixels
                            next_line[src_offset] = scan_line[src_offset]
                            next_line[src_offset + 1] = scan_line[src_offset + 1]
                            next_line[src_offset + 2] = scan_line[src_offset + 2]
                            next_line[src_offset + 3] = scan_line[src_offset + 3]
                            
                            # Also copy the adjacent pixel if it exists
                            if x + 1 < width:
                                next_src_offset = (x + 1) * 4
                                next_line[next_src_offset] = scan_line[next_src_offset]
                                next_line[next_src_offset + 1] = scan_line[next_src_offset + 1]
                                next_line[next_src_offset + 2] = scan_line[next_src_offset + 2]
                                next_line[next_src_offset + 3] = scan_line[next_src_offset + 3]
            
            return QPixmap.fromImage(image)
            
        except Exception as e:
            print(f"Error in ultra-fast LUT: {e}")
            return pixmap

    def _nearest_neighbor_lut(self, r, g, b, lut_data, lut_size):
        """Fastest possible LUT lookup - pure nearest neighbor"""
        try:
            # Scale to LUT coordinates
            r_idx = max(0, min(lut_size - 1, int(r * (lut_size - 1) + 0.5)))
            g_idx = max(0, min(lut_size - 1, int(g * (lut_size - 1) + 0.5)))
            b_idx = max(0, min(lut_size - 1, int(b * (lut_size - 1) + 0.5)))
            
            # Direct lookup - no interpolation
            index = r_idx + g_idx * lut_size + b_idx * lut_size * lut_size
            if 0 <= index < len(lut_data):
                return lut_data[index]
            else:
                return (r, g, b)
        except:
            return (r, g, b)

    def _apply_basic_enhancements(self, pixmap):
        """Apply basic enhancements quickly for preview"""
        if not pixmap or pixmap.isNull():
            return pixmap
            
        # For fast preview, skip complex enhancements
        # Just return the LUT-processed pixmap
        return pixmap

    def update_lut_strength(self, value):
        """Update LUT application strength with fast preview and async full quality"""
        self.lut_strength = value
        
        # Clear caches for immediate update (including LUT process cache)
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        if hasattr(self, '_lut_process_cache'):
            self._lut_process_cache.clear()  # Clear LUT cache when strength changes
        
        # CRITICAL: Clear zoom optimization cache when LUT strength changes
        if hasattr(self, '_last_processed_image'):
            self._last_processed_image = None
        self._last_processed_has_lut = False
        
        # Show immediate update without heavy processing
        if self.lut_enabled and self.current_image and self.current_lut:
            if value > 0:
                # Show fast preview first
                self.status.showMessage(f"LUT strength: {value}% (instant preview)")
                QApplication.processEvents()
                self._create_fast_lut_preview()
                
                # Then apply full quality asynchronously
                QTimer.singleShot(10, self._apply_full_quality_lut)
            else:
                # No LUT strength, use normal display
                self.display_image(self.current_image)
                self.status.showMessage("LUT disabled (strength: 0%)")
        elif self.current_image:
            # No LUT active, just update normally
            self.display_image(self.current_image)
            if value == 0:
                self.status.showMessage("LUT disabled (strength: 0%)")
            else:
                self.status.showMessage(f"LUT strength: {value}% (no LUT selected)")

    def reset_zoom(self):
        """Reset image zoom and pan to 100% with smart LUT caching"""
        if self.image_label:
            self.image_label.reset_zoom()
            if self.current_image:
                self._smart_zoom_display()
            
            # Update status with processing awareness
            if (self.lut_enabled and hasattr(self, '_async_processing_state') and 
                self._async_processing_state and self.current_lut):
                progress = (self._async_processing_state['current_row'] / 
                          self._async_processing_state['total_rows']) * 100
                lut_name = self.current_lut_name if self.current_lut_name != "None" else "LUT"
                self.status.showMessage(f"Zoom reset to 100% - {lut_name} processing... {progress:.0f}%")
            else:
                self.status.showMessage("Zoom reset to 100%")

    def zoom_in(self):
        """Zoom in by 15% with smart LUT caching"""
        if self.image_label:
            current_zoom = getattr(self.image_label, 'zoom_factor', 1.0)
            new_zoom = min(current_zoom * 1.15, 8.0)
            self.image_label.zoom_factor = new_zoom
            if self.current_image:
                self._smart_zoom_display()
                # Reapply lines quickly after zoom
                if (self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines)
                    and hasattr(self, '_fast_line_update')):
                    self._fast_line_update()
            
            # Update status with processing awareness
            if (self.lut_enabled and hasattr(self, '_async_processing_state') and 
                self._async_processing_state and self.current_lut):
                progress = (self._async_processing_state['current_row'] / 
                          self._async_processing_state['total_rows']) * 100
                lut_name = self.current_lut_name if self.current_lut_name != "None" else "LUT"
                self.status.showMessage(f"Zoom: {new_zoom:.1f}x - {lut_name} processing... {progress:.0f}%")
            else:
                self.status.showMessage(f"Zoom: {new_zoom:.1f}x")

    def zoom_out(self):
        """Zoom out by 15% with smart LUT caching"""
        if self.image_label:
            current_zoom = getattr(self.image_label, 'zoom_factor', 1.0)
            new_zoom = max(current_zoom / 1.15, 0.1)
            self.image_label.zoom_factor = new_zoom
            if self.current_image:
                self._smart_zoom_display()
                if (self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines)
                    and hasattr(self, '_fast_line_update')):
                    self._fast_line_update()
            
            # Update status with processing awareness
            if (self.lut_enabled and hasattr(self, '_async_processing_state') and 
                self._async_processing_state and self.current_lut):
                progress = (self._async_processing_state['current_row'] / 
                          self._async_processing_state['total_rows']) * 100
                lut_name = self.current_lut_name if self.current_lut_name != "None" else "LUT"
                self.status.showMessage(f"Zoom: {new_zoom:.1f}x - {lut_name} processing... {progress:.0f}%")
            else:
                self.status.showMessage(f"Zoom: {new_zoom:.1f}x")
    
    def _smart_zoom_display(self):
        """OPTIMIZED zoom display - avoids GPU reprocessing during interactive zoom"""
        if not self.current_image:
            return
            
        try:
            # CRITICAL OPTIMIZATION: During zoom, use the last processed image to avoid GPU calls
            # This prevents freezing during interactive zoom operations
            
            # If we have a recently processed image cached, use it for zoom
            if (hasattr(self, '_last_processed_image') and 
                self._last_processed_image and
                not self._last_processed_image.isNull() and
                (self.lut_enabled or not self._last_processed_has_lut)):
                
                # Use the cached processed image for zoom operations
                processed_pixmap = QPixmap.fromImage(self._last_processed_image)
                
                # Apply transforms if needed (these are fast)
                if self.rotation_angle != 0 or self.flipped_h or self.flipped_v:
                    processed_pixmap = self._apply_cached_transforms(processed_pixmap)
                
                # Scale and display - FAST operation, no GPU processing
                final_pixmap = self._scale_pixmap(processed_pixmap, self.current_image)
                self.image_label.setPixmap(final_pixmap)
                # Reapply lines if present
                if (self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines)
                    and hasattr(self, '_fast_line_update')):
                    self._fast_line_update()
                
                # Show zoom status
                zoom = getattr(self.image_label, 'zoom_factor', 1.0)
                self.status.showMessage(f"Zoom: {zoom:.1f}x (GPU cached)")
                return
            
            # If no cached processed image, check LUT cache
            if self.lut_enabled and self.current_lut and self.lut_strength > 0:
                cache_key = self._get_lut_cache_key()
                
                # Check if we have cached LUT result
                if (hasattr(self, '_lut_process_cache') and 
                    cache_key in self._lut_process_cache):
                    
                    cached_pixmap = self._lut_process_cache[cache_key]
                    
                    # Apply transforms if needed
                    if self.rotation_angle != 0 or self.flipped_h or self.flipped_v:
                        processed_pixmap = self._apply_cached_transforms(cached_pixmap)
                    else:
                        processed_pixmap = cached_pixmap
                    
                    # Scale and display
                    final_pixmap = self._scale_pixmap(processed_pixmap, self.current_image)
                    self.image_label.setPixmap(final_pixmap)
                    if (self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines)
                        and hasattr(self, '_fast_line_update')):
                        self._fast_line_update()
                    
                    zoom = getattr(self.image_label, 'zoom_factor', 1.0)
                    self.status.showMessage(f"Zoom: {zoom:.1f}x (LUT cached)")
                    return
            
            # Last resort: use original image without LUT processing during zoom
            # This prevents freezing when no cache is available, but respect current LUT strength
            base_pixmap = None
            if self.current_image in self.pixmap_cache:
                base_pixmap = self.pixmap_cache[self.current_image]
            else:
                base_pixmap, error = safe_load_pixmap(self.current_image)
                if error or (not base_pixmap) or base_pixmap.isNull():
                    return
            # Apply fast enhancements first (grayscale/contrast/gamma)
            preview_pixmap = self.apply_fast_enhancements(base_pixmap.copy()) if (self.grayscale_value!=0 or self.contrast_value!=50 or self.gamma_value!=0) else base_pixmap
            # Apply lightweight LUT preview at current strength (no caching write to avoid thrash)
            if self.lut_enabled and self.current_lut and self.lut_strength>0:
                try:
                    preview_pixmap = self.apply_lut_to_image(preview_pixmap, self.current_lut, self.lut_strength)
                except Exception as _e:
                    pass
            # Apply transforms
            if self.rotation_angle != 0 or self.flipped_h or self.flipped_v:
                preview_pixmap = self._apply_cached_transforms(preview_pixmap)
            final_pixmap = self._scale_pixmap(preview_pixmap, self.current_image)
            self.image_label.setPixmap(final_pixmap)
            if (self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines) and hasattr(self, '_fast_line_update')):
                self._fast_line_update()
            zoom = getattr(self.image_label, 'zoom_factor', 1.0)
            # Show more specific status based on whether LUT was applied
            if self.lut_enabled and self.current_lut and self.lut_strength > 0:
                lut_name = self.current_lut_name if self.current_lut_name != "None" else "LUT"
                self.status.showMessage(f"Zoom: {zoom:.1f}x (live {lut_name} preview)")
            else:
                self.status.showMessage(f"Zoom: {zoom:.1f}x (no LUT)")
            
        except Exception as e:
            print(f"Error in smart zoom display: {e}")
            # Emergency fallback - show original image
            try:
                if self.current_image in self.pixmap_cache:
                    original_pixmap = self.pixmap_cache[self.current_image]
                else:
                    original_pixmap, error = safe_load_pixmap(self.current_image)
                    if error or original_pixmap.isNull():
                        return
                final_pixmap = self._scale_pixmap(original_pixmap, self.current_image)
                self.image_label.setPixmap(final_pixmap)
            except Exception as fallback_e:
                print(f"Fallback also failed: {fallback_e}")
                pass
    
    def _get_lut_cache_key(self):
        """Generate cache key for LUT processing - includes lines and enhancements"""
        if not self.lut_enabled or not self.current_lut or not self.current_image:
            return None
            
        # Create comprehensive cache key including all visual modifications
        lut_file_path = getattr(self.current_lut, 'file_path', 'unknown')
        
        # Include line information in cache key
        lines_key = ""
        if self.lines_visible and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
            # Create a compact representation of all lines
            vlines = f"v{len(self.drawn_lines)}" if self.drawn_lines else ""
            hlines = f"h{len(self.drawn_horizontal_lines)}" if self.drawn_horizontal_lines else ""
            flines = f"f{len(self.drawn_free_lines)}" if self.drawn_free_lines else ""
            color_key = self.line_color.name()
            thickness_key = str(self.line_thickness)
            lines_key = f"_lines_{vlines}{hlines}{flines}_{color_key}_{thickness_key}"
        
        # Include enhancement settings in cache key
        enhancements_key = ""
        if (self.grayscale_value != 0 or self.contrast_value != 50 or self.gamma_value != 0):
            enhancements_key = f"_enh_{self.grayscale_value}_{self.contrast_value}_{self.gamma_value}"
        
        return f"{self.current_image}_{lut_file_path}_{self.lut_strength}{lines_key}{enhancements_key}"
    
    def _apply_cached_transforms(self, pixmap):
        """Apply rotation and flips to cached pixmap"""
        if not pixmap or pixmap.isNull():
            return pixmap
            
        # Apply rotation if needed
        if self.rotation_angle != 0:
            transform = QTransform()
            transform.rotate(self.rotation_angle)
            pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
        
        # Apply flips if needed
        if self.flipped_h:
            pixmap = pixmap.transformed(QTransform().scale(-1, 1), Qt.SmoothTransformation)
        if self.flipped_v:
            pixmap = pixmap.transformed(QTransform().scale(1, -1), Qt.SmoothTransformation)
            
        return pixmap

    def flip_horizontal(self):
        """Flip the current image horizontally"""
        if self.current_image:
            self.flipped_h = not self.flipped_h
            # Update button appearance to show state
            if hasattr(self, 'flip_h_btn'):
                self.flip_h_btn.setChecked(self.flipped_h)
            # Clear caches since flip changes the image
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            self.display_image(self.current_image)
            self.status.showMessage(f"Horizontal flip: {'ON' if self.flipped_h else 'OFF'}")
            # Disable/enable line tools when flip/rotation state changes
            try:
                self._sync_line_tools_state()
            except Exception:
                pass

    def flip_vertical(self):
        """Flip the current image vertically"""
        if self.current_image:
            self.flipped_v = not self.flipped_v
            # Update button appearance to show state
            if hasattr(self, 'flip_v_btn'):
                self.flip_v_btn.setChecked(self.flipped_v)
            # Clear caches since flip changes the image
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            self.display_image(self.current_image)
            self.status.showMessage(f"Vertical flip: {'ON' if self.flipped_v else 'OFF'}")
            # Disable/enable line tools when flip/rotation state changes
            try:
                self._sync_line_tools_state()
            except Exception:
                pass

    def rotate_image_90(self):
        """Rotate the current image by 90 degrees"""
        if self.current_image:
            self.rotation_angle = (self.rotation_angle + 90) % 360
            # Clear caches since rotation changes the image
            self.enhancement_cache.clear()
            self.scaled_cache.clear()
            # Redisplay the image with new rotation
            self.display_image(self.current_image)
            self.status.showMessage(f"Rotated to {self.rotation_angle}°")
            # Disable/enable line tools when flip/rotation state changes
            try:
                self._sync_line_tools_state()
            except Exception:
                pass

    def _sync_line_tools_state(self):
        """Enable or disable line tool buttons depending on rotation/flip state.
        When image is rotated or flipped we disable line drawing tools because
        coordinate math for drawing over rotated/flipped images is disabled.
        """
        # If any transform is active, disable line tools
        transforms_active = (getattr(self, 'rotation_angle', 0) != 0) or getattr(self, 'flipped_h', False) or getattr(self, 'flipped_v', False)

        # Buttons may not exist yet during startup; guard with hasattr
        for btn_name in ('line_tool_btn', 'hline_tool_btn', 'free_line_tool_btn'):
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                try:
                    btn.setEnabled(not transforms_active)
                    # When disabling, also uncheck and cancel drawing modes
                    if transforms_active:
                        if hasattr(btn, 'setChecked'):
                            try:
                                btn.setChecked(False)
                            except Exception:
                                pass
                except Exception:
                    # ignore failures to set UI state
                    pass

        # Clear any active drawing modes when transforms are active
        if transforms_active:
            self.line_drawing_mode = False
            self.horizontal_line_drawing_mode = False
            self.free_line_drawing_mode = False
            # Ensure the toolbar buttons reflect that
            if hasattr(self, 'line_tool_btn'):
                try: self.line_tool_btn.setChecked(False)
                except Exception: pass
            if hasattr(self, 'hline_tool_btn'):
                try: self.hline_tool_btn.setChecked(False)
                except Exception: pass
            if hasattr(self, 'free_line_tool_btn'):
                try: self.free_line_tool_btn.setChecked(False)
                except Exception: pass


    def copy_to_clipboard(self):
        """Copy the current displayed image (with all enhancements and lines) to clipboard"""
        if not self.current_image or not self.image_label.pixmap():
            self.status.showMessage("No image to copy")
            return
        
        try:
            # Get the currently displayed pixmap (this includes all enhancements and lines)
            current_pixmap = self.image_label.pixmap()
            
            if current_pixmap and not current_pixmap.isNull():
                # Copy to clipboard
                clipboard = QApplication.clipboard()
                clipboard.setPixmap(current_pixmap)
                
                # Show confirmation message
                filename = os.path.basename(self.current_image)
                self.status.showMessage(f"Copied {filename} to clipboard (with enhancements and lines)")
            else:
                self.status.showMessage("No image available to copy")
                
        except Exception as e:
            self.status.showMessage(f"Error copying to clipboard: {str(e)}")

    def keyPressEvent(self, event):
        """Handle key press events with robust fullscreen exit"""
        # Debug print to help troubleshoot
        print(f"Key pressed: {event.key()}, Fullscreen: {self.is_fullscreen}")
        
        if event.key() == Qt.Key_Left:
            self.show_previous_image()
        elif event.key() == Qt.Key_Right:
            self.show_next_image()
        elif event.key() == Qt.Key_F11:
            # Toggle fullscreen mode
            print("F11 pressed - toggling fullscreen")
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_Escape:
            # Priority 1: Exit fullscreen if in fullscreen mode
            if self.is_fullscreen:
                print("Escape pressed - exiting fullscreen")
                if event.modifiers() & Qt.ControlModifier:
                    print("Ctrl+Esc pressed - force exiting fullscreen")
                    self.force_exit_fullscreen()
                else:
                    self.exit_fullscreen()
            # Priority 2: Show UI if in minimal mode (UI hidden)
            elif not self.main_toolbar.isVisible():
                print("Escape pressed - restoring UI from minimal mode")
                self.toggle_toolbar_visibility(True)  # Show UI
            else:
                super().keyPressEvent(event)
        elif event.modifiers() & Qt.ControlModifier:
            if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
                self.zoom_in()
            elif event.key() == Qt.Key_Minus:
                self.zoom_out()
            elif event.key() == Qt.Key_0:
                self.reset_zoom()
            elif event.key() == Qt.Key_H:
                self.flip_horizontal()
            elif event.key() == Qt.Key_V:
                self.flip_vertical()
            elif event.key() == Qt.Key_R:
                # Reset all enhancements
                self.reset_enhancements()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double-click events - exit fullscreen if in fullscreen mode"""
        if self.is_fullscreen:
            print("Double-click detected - exiting fullscreen")
            self.exit_fullscreen()
        else:
            super().mouseDoubleClickEvent(event)

    def closeEvent(self, event):
        """Handle window close event"""
        super().closeEvent(event)

    def showEvent(self, event):
        """Override showEvent to ensure dark title bar is applied"""
        super().showEvent(event)
        
        # Apply dark title bar when window is shown for the first time
        if not hasattr(self, '_dark_title_applied'):
            self._dark_title_applied = True
            if is_windows_dark_mode():
                print("DEBUG: Ensuring dark title bar in showEvent")
                # Single clean attempt to apply dark mode
                success = enable_windows_dark_title_bar(self)
                if not success:
                    # If first attempt failed, try once more after a brief delay
                    QTimer.singleShot(100, lambda: enable_windows_dark_title_bar(self))

    def show_previous_image(self):
        if self.history_index > 0:
            self.history_index -= 1
            img_path = self.history[self.history_index]
            self._display_image_with_lut_preview(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()

    def show_next_image(self):
        """Shows the next image, respecting the random or sequential mode."""
        if not self.images:
            return

        if self.random_mode:
            # In random mode, if at end of history show new random image
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                img_path = self.history[self.history_index]
                self._display_image_with_lut_preview(img_path)
                self.current_image = img_path
                self.update_image_info(img_path)
                self.set_status_path(img_path)
                if self._auto_advance_active:
                    self.timer_remaining = self.timer_spin.value()
                    self._update_ring()
            else:
                self.show_random_image()
        else:
            # Sequential mode - navigate alphabetically through images
            if self.current_image and self.current_image in self.images:
                try:
                    current_list_index = self.images.index(self.current_image)
                    next_index = (current_list_index + 1) % len(self.images)
                except ValueError:
                    next_index = 0
            else:
                next_index = 0
            
            img_path = self.images[next_index]
            self._display_image_with_lut_preview(img_path)
            self.add_to_history(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()

    def choose_folder(self):
        # Set default folder if it exists
        default_folder = r"Y:\_REFERENCES_MAIN"
        start_dir = default_folder if os.path.exists(default_folder) else ""
        
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder", start_dir)
        if folder:
            self.folder = folder
            self.images = get_images_in_folder(folder)
            self.history.clear()
            self.history_list.clear()
            self.history_list.repaint()
            self.current_image = None
            self.history_index = -1  # Reset history navigation
            self.update_image_info()
            self._update_title()
            if self.images:
                # Use mode-aware navigation when opening folder
                if self.random_mode:
                    self.show_random_image()
                else:
                    # In alphabetical mode, start with the first image
                    first_image = self.images[0]
                    self._display_image_with_lut_preview(first_image)
                    self.add_to_history(first_image)
                    self.current_image = first_image
                    self.update_image_info(first_image)
                    self.set_status_path(first_image)
                    if self._auto_advance_active:
                        self.timer_remaining = self.timer_spin.value()
                        self._update_ring()
            else:
                self.image_label.setText("No images found in selected folder or its subfolders.")
            self._reset_timer()

    def mousePressEvent(self, event):
        """Handle mouse press for window dragging and resizing in frameless mode."""
        # Only handle dragging/resizing when UI is hidden (frameless mode)
        if self.main_toolbar.isVisible() or not (self.windowFlags() & Qt.FramelessWindowHint):
            super().mousePressEvent(event)
            return

        if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
            self.drag_start_position = event.globalPosition().toPoint()
            
            # Check if we're near an edge for resizing (only for left-click)
            pos = event.position().toPoint()
            window_rect = self.rect()
            margin = self.resize_margin
            
            # Determine resize edge with proper corner detection
            resize_edge = ""
            at_left = pos.x() <= margin
            at_right = pos.x() >= window_rect.width() - margin
            at_top = pos.y() <= margin
            at_bottom = pos.y() >= window_rect.height() - margin
            
            # Handle corners first (combination of edges)
            if at_top and at_left:
                resize_edge = "topleft"
            elif at_top and at_right:
                resize_edge = "topright"
            elif at_bottom and at_left:
                resize_edge = "bottomleft"
            elif at_bottom and at_right:
                resize_edge = "bottomright"
            # Then handle single edges
            elif at_top:
                resize_edge = "top"
            elif at_bottom:
                resize_edge = "bottom"
            elif at_left:
                resize_edge = "left"
            elif at_right:
                resize_edge = "right"
            
            # Left-click: resize if on edge, otherwise drag
            # Right-click: always drag (even on edges)
            if event.button() == Qt.LeftButton and resize_edge:
                self.resizing = True
                self.resize_edge = resize_edge
                self.setCursor(self._get_resize_cursor(resize_edge))
            else:
                self.dragging = True
                self.setCursor(Qt.ClosedHandCursor)
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging and resizing in frameless mode."""
        # Only handle dragging/resizing when UI is hidden (frameless mode)
        if self.main_toolbar.isVisible() or not (self.windowFlags() & Qt.FramelessWindowHint):
            super().mouseMoveEvent(event)
            return

        if event.buttons() & (Qt.LeftButton | Qt.RightButton):
            if self.dragging and self.drag_start_position:
                # Move window (works with both left and right mouse buttons)
                diff = event.globalPosition().toPoint() - self.drag_start_position
                self.move(self.pos() + diff)
                self.drag_start_position = event.globalPosition().toPoint()
            
            elif self.resizing and self.resize_edge and self.drag_start_position:
                # Resize window (only works with left mouse button)
                current_pos = event.globalPosition().toPoint()
                diff = current_pos - self.drag_start_position
                
                geometry = self.geometry()
                min_size = self.minimumSize()
                
                if "left" in self.resize_edge:
                    new_width = geometry.width() - diff.x()
                    if new_width >= min_size.width():
                        geometry.setLeft(geometry.left() + diff.x())
                        geometry.setWidth(new_width)
                
                if "right" in self.resize_edge:
                    new_width = geometry.width() + diff.x()
                    if new_width >= min_size.width():
                        geometry.setWidth(new_width)
                
                if "top" in self.resize_edge:
                    new_height = geometry.height() - diff.y()
                    if new_height >= min_size.height():
                        geometry.setTop(geometry.top() + diff.y())
                        geometry.setHeight(new_height)
                
                if "bottom" in self.resize_edge:
                    new_height = geometry.height() + diff.y()
                    if new_height >= min_size.height():
                        geometry.setHeight(new_height)
                
                self.setGeometry(geometry)
                self.drag_start_position = current_pos
        else:
            # Update cursor when hovering near edges
            pos = event.position().toPoint()
            window_rect = self.rect()
            margin = self.resize_margin
            
            resize_edge = ""
            at_left = pos.x() <= margin
            at_right = pos.x() >= window_rect.width() - margin
            at_top = pos.y() <= margin
            at_bottom = pos.y() >= window_rect.height() - margin
            
            # Handle corners first (combination of edges)
            if at_top and at_left:
                resize_edge = "topleft"
            elif at_top and at_right:
                resize_edge = "topright"
            elif at_bottom and at_left:
                resize_edge = "bottomleft"
            elif at_bottom and at_right:
                resize_edge = "bottomright"
            # Then handle single edges
            elif at_top:
                resize_edge = "top"
            elif at_bottom:
                resize_edge = "bottom"
            elif at_left:
                resize_edge = "left"
            elif at_right:
                resize_edge = "right"
            
            if resize_edge:
                self.setCursor(self._get_resize_cursor(resize_edge))
            else:
                self.setCursor(Qt.ArrowCursor)
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to end dragging/resizing."""
        if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
            self.dragging = False
            self.resizing = False
            self.resize_edge = None
            self.drag_start_position = None
            self.setCursor(Qt.ArrowCursor)
        
        super().mouseReleaseEvent(event)

    def _get_resize_cursor(self, edge):
        """Get appropriate cursor for resize edge - matches standard window resize cursors."""
        if edge == "top" or edge == "bottom":
            return Qt.SizeVerCursor  # Vertical resize (↕)
        elif edge == "left" or edge == "right":
            return Qt.SizeHorCursor  # Horizontal resize (↔)
        elif edge == "topleft" or edge == "bottomright":
            return Qt.SizeFDiagCursor  # Diagonal resize (\)
        elif edge == "topright" or edge == "bottomleft":
            return Qt.SizeBDiagCursor  # Diagonal resize (/)
        else:
            return Qt.ArrowCursor

    def dragEnterEvent(self, event):
        """Handle drag enter events - accept folder drops."""
        if event.mimeData().hasUrls():
            # Check if any of the dragged items are directories
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if os.path.isdir(file_path):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle drop events - open dropped folders."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if os.path.isdir(file_path):
                        print(f"Folder dropped: {file_path}")
                        self.folder = file_path
                        self.images = get_images_in_folder(file_path)
                        self.history.clear()
                        self.history_list.clear()
                        self.history_list.repaint()
                        self.current_image = None
                        self.history_index = -1  # Reset history navigation
                        self.update_image_info()
                        self._update_title()
                        
                        if self.images:
                            # Use mode-aware navigation when opening dropped folder
                            if self.random_mode:
                                self.show_random_image()
                            else:
                                # In alphabetical mode, start with the first image
                                first_image = self.images[0]
                                self._display_image_with_lut_preview(first_image)
                                self.add_to_history(first_image)
                                self.current_image = first_image
                                self.update_image_info(first_image)
                                self.set_status_path(first_image)
                                if self._auto_advance_active:
                                    self.timer_remaining = self.timer_spin.value()
                                    self._update_ring()
                        else:
                            self.image_label.setText("No images found in dropped folder or its subfolders.")
                        
                        self._reset_timer()
                        self.status.showMessage(f"Loaded folder: {os.path.basename(file_path)} ({len(self.images)} images)")
                        event.acceptProposedAction()
                        return
            
            event.ignore()
        else:
            event.ignore()

if __name__ == "__main__":
    # Defer Qt allocations until after QApplication is created
    app = QApplication(sys.argv)
    setup_image_allocation_limit()  # Increase image allocation limit at startup
    app.setStyleSheet(get_adaptive_stylesheet())  # Use OS-adaptive theme
    viewer = RandomImageViewer()
    
    # Clear caches to ensure GPU color fixes take effect
    viewer.clear_lut_cache()
    print("INFO: GPU LUT color processing has been fixed - BGRA format now handled correctly")
    
    # Apply dark title bar BEFORE showing the window for professional appearance
    if is_windows_dark_mode():
        print("DEBUG: Applying dark title bar before window show")
        # Apply immediately after window creation but before show
        QTimer.singleShot(0, lambda: enable_windows_dark_title_bar(viewer))
    
    viewer.show()
    
    sys.exit(app.exec())
