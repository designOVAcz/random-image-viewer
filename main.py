import sys
import os
import random
import time
import subprocess
import gc
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
    QStyle, QStyleOptionSlider, QGridLayout, QMenu, QColorDialog
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QIcon, QColorTransform, QMouseEvent, QImageReader, QTransform, QAction, QShortcut
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
        for f in files:
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                image_paths.append(os.path.join(root, f))
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
QPushButton:checked, QToolButton:checked { background: #3b7dd8; color: #fff; }
QListWidget::item:selected { background: #354e6e; color: #fff; }
QCheckBox:checked { color: #3b7dd8; }
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
    background: #3b7dd8;
}
QSpinBox {
    background: #35383b;
    border: 1px solid #4a4d50;
    border-radius: 3px;
    padding: 2px;
    selection-background-color: #3b7dd8;
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
    background: #3b7dd8;
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
                
                # Trigger image redisplay with new zoom
                self.parent_viewer.display_image(self.parent_viewer.current_image)
                
                # Update status to show zoom level
                zoom_percent = int(self.zoom_factor * 100)
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
                # Convert to display coordinate space using same scale factors as display
                scale_x = zoomed_width / display_reference_size.width()
                scale_y = zoomed_height / display_reference_size.height()
                
                # Convert to display coordinates (relative to the rotated image)
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
                    # Undo 90° clockwise rotation
                    unrotated_x = display_y
                    unrotated_y = display_reference_size.width() - display_x
                elif rotation == 180:
                    # Undo 180° rotation
                    unrotated_x = display_reference_size.width() - display_x
                    unrotated_y = display_reference_size.height() - display_y
                elif rotation == 270:
                    # Undo 270° clockwise rotation
                    unrotated_x = display_reference_size.height() - display_y
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
            
            # Refresh the display
            if self.parent_viewer and self.parent_viewer.current_image:
                self.parent_viewer.display_image(self.parent_viewer.current_image)
            
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
        
        next_action = QAction("Next Random Image", self)
        next_action.triggered.connect(self.parent_viewer.show_random_image)
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
        
        # Handle image display resize
        if self.current_image:
            self.display_image(self.current_image)

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

class RandomImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle("Random Image Viewer")
        self.setGeometry(100, 100, 950, 650)
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
        self.line_thickness = 1
        self.line_color = QColor("#ffffff")  # Default white color for lines

        # Always on top functionality
        self.always_on_top = False

        # Fullscreen functionality
        self.is_fullscreen = False
        self.normal_geometry = None  # Store window geometry before fullscreen

        # Image enhancement parameters
        self.grayscale_value = 0  # 0 = color, 100 = full grayscale
        self.contrast_value = 50  # 50 = normal, 0-200 range
        self.gamma_value = 0     # 0 = normal, -200 to +500 range
        self.rotation_angle = 0   # Rotation angle in degrees
        self.flipped_h = False    # Horizontal flip state
        self.flipped_v = False    # Vertical flip state
        self.original_pixmap = None  # Cache original image for fast processing
        self.enhancement_cache = {}  # Cache enhanced versions

        self.timer_interval = 60  # seconds
        self.timer_remaining = 0
        self._auto_advance_active = False
        self._timer_paused = False  # NEW: Timer pause state

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_timer_tick)

        self.init_ui()

    def init_ui(self):
        # Create menu bar with essential shortcuts
        self.create_menu_bar()
        
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

    def create_menu_bar(self):
        """Create menu bar with essential shortcuts"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('&File')
        
        # Open folder
        open_action = QAction('&Open Folder...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.choose_folder)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Alt+F4')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('&View')
        
        # Fullscreen toggle
        self.fullscreen_action = QAction('&Fullscreen', self)
        self.fullscreen_action.setShortcut('F11')
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.triggered.connect(self.menu_toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)
        
        # Force exit fullscreen
        force_exit_action = QAction('Force Exit Fullscreen', self)
        force_exit_action.setShortcut('Ctrl+Esc')
        force_exit_action.triggered.connect(self.force_exit_fullscreen)
        view_menu.addAction(force_exit_action)
        
        view_menu.addSeparator()
        
        # Zoom actions
        zoom_in_action = QAction('Zoom &In', self)
        zoom_in_action.setShortcut('Ctrl++')
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('Zoom &Out', self)
        zoom_out_action.setShortcut('Ctrl+-')
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction('&Reset Zoom', self)
        reset_zoom_action.setShortcut('Ctrl+0')
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
        # Enhancement menu
        enhancement_menu = menubar.addMenu('&Enhancement')
        
        # Grayscale toggle
        self.grayscale_menu_action = QAction('&Grayscale', self)
        self.grayscale_menu_action.setCheckable(True)
        self.grayscale_menu_action.triggered.connect(lambda: self.toggle_grayscale(self.grayscale_value == 0))
        enhancement_menu.addAction(self.grayscale_menu_action)
        
        # Contrast toggle
        self.contrast_menu_action = QAction('Enhanced &Contrast', self)
        self.contrast_menu_action.setCheckable(True)
        self.contrast_menu_action.triggered.connect(self.toggle_contrast)
        enhancement_menu.addAction(self.contrast_menu_action)
        
        # Gamma toggle
        self.gamma_menu_action = QAction('Enhanced Brigh&tness', self)
        self.gamma_menu_action.setCheckable(True)
        self.gamma_menu_action.triggered.connect(self.toggle_gamma)
        enhancement_menu.addAction(self.gamma_menu_action)
        
        enhancement_menu.addSeparator()
        
        # Reset enhancements
        reset_enhancements_action = QAction('&Reset All Enhancements', self)
        reset_enhancements_action.setShortcut('Ctrl+R')
        reset_enhancements_action.triggered.connect(self.reset_enhancements)
        enhancement_menu.addAction(reset_enhancements_action)

    def menu_toggle_fullscreen(self):
        """Toggle fullscreen from menu (no parameters)"""
        print("Menu fullscreen toggle triggered")
        self.toggle_fullscreen()
        # Update menu action state
        self.fullscreen_action.setChecked(self.is_fullscreen)

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
        
        print("Global shortcuts set up successfully")

    def emergency_exit_fullscreen(self):
        """Emergency exit from fullscreen"""
        print("EMERGENCY: Escape shortcut activated")
        if self.is_fullscreen:
            self.force_exit_fullscreen()

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

        open_btn = QToolButton()
        open_btn.setText("📁")
        open_btn.setToolTip("Open Folder")
        open_btn.setFixedSize(24, 24)
        open_btn.clicked.connect(self.choose_folder)
        toolbar.addWidget(open_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Line drawing tool button
        self.line_tool_btn = QToolButton()
        self.line_tool_btn.setText("📏")
        self.line_tool_btn.setToolTip("Draw Vertical Lines")
        self.line_tool_btn.setCheckable(True)
        self.line_tool_btn.setFixedSize(24, 24)
        self.line_tool_btn.toggled.connect(self.toggle_line_drawing)
        toolbar.addWidget(self.line_tool_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Horizontal line drawing tool button
        self.hline_tool_btn = QToolButton()
        self.hline_tool_btn.setText("━")
        self.hline_tool_btn.setToolTip("Draw Horizontal Lines")
        self.hline_tool_btn.setCheckable(True)
        self.hline_tool_btn.setFixedSize(24, 24)
        self.hline_tool_btn.toggled.connect(self.toggle_hline_drawing)
        toolbar.addWidget(self.hline_tool_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Free line drawing tool button
        self.free_line_tool_btn = QToolButton()
        self.free_line_tool_btn.setText("╱")
        self.free_line_tool_btn.setToolTip("Draw Free Lines (2 clicks per line)")
        self.free_line_tool_btn.setCheckable(True)
        self.free_line_tool_btn.setFixedSize(24, 24)
        self.free_line_tool_btn.toggled.connect(self.toggle_free_line_drawing)
        toolbar.addWidget(self.free_line_tool_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Undo last line button
        self.undo_line_btn = QToolButton()
        self.undo_line_btn.setText("↶")
        self.undo_line_btn.setToolTip("Undo Last Line (Remove most recently added line)")
        self.undo_line_btn.setFixedSize(24, 24)
        self.undo_line_btn.clicked.connect(self.undo_last_line)
        toolbar.addWidget(self.undo_line_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Line thickness spinbox
        self.line_thickness_spin = QSpinBox()
        self.line_thickness_spin.setRange(1, 10)
        self.line_thickness_spin.setValue(self.line_thickness)
        self.line_thickness_spin.setSuffix("px")
        self.line_thickness_spin.setFixedHeight(24)
        self.line_thickness_spin.setFixedWidth(50)
        self.line_thickness_spin.setToolTip("Line Thickness")
        self.line_thickness_spin.valueChanged.connect(self.update_line_thickness)
        toolbar.addWidget(self.line_thickness_spin)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Line color picker button
        self.line_color_btn = QToolButton()
        self.line_color_btn.setText("🎨")
        self.line_color_btn.setToolTip("Choose Line Color")
        self.line_color_btn.setFixedSize(24, 24)
        self.line_color_btn.clicked.connect(self.choose_line_color)
        # Set initial background color to show current color
        self.line_color_btn.setStyleSheet(f"QToolButton {{ background-color: {self.line_color.name()}; border: 1px solid #666; }}")
        toolbar.addWidget(self.line_color_btn)

        # Quick color preset buttons
        colors = [
            ("#ffffff", "White", "⚪"),
            ("#000000", "Black", "⚫"),
            ("#808080", "Grey", "⚪"),
        ]
        
        for color_hex, color_name, emoji in colors:
            color_btn = QToolButton()
            color_btn.setText(emoji)
            color_btn.setToolTip(f"Set Line Color to {color_name}")
            color_btn.setFixedSize(18, 24)  # Slightly smaller for presets
            color_btn.clicked.connect(lambda checked, c=color_hex: self.set_line_color(c))
            color_btn.setStyleSheet(f"QToolButton {{ border: 1px solid #444; margin: 1px; }}")
            toolbar.addWidget(color_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Clear lines button
        clear_lines_btn = QToolButton()
        clear_lines_btn.setText("🗑")
        clear_lines_btn.setToolTip("Clear All Lines")
        clear_lines_btn.setFixedSize(24, 24)
        clear_lines_btn.clicked.connect(self.clear_lines)
        toolbar.addWidget(clear_lines_btn)

        spacer = QWidget()
        spacer.setFixedWidth(8)
        toolbar.addWidget(spacer)

        # Enhancement toggle buttons
        # Grayscale toggle button
        self.grayscale_toggle_btn = QToolButton()
        self.grayscale_toggle_btn.setText("🌑")  # Moon icon for grayscale
        self.grayscale_toggle_btn.setToolTip("Toggle Grayscale On/Off")
        self.grayscale_toggle_btn.setCheckable(True)
        self.grayscale_toggle_btn.setFixedSize(24, 24)
        self.grayscale_toggle_btn.toggled.connect(self.toggle_grayscale)
        toolbar.addWidget(self.grayscale_toggle_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Contrast toggle button  
        self.contrast_toggle_btn = QToolButton()
        self.contrast_toggle_btn.setText("🔆")  # Sun with rays for contrast
        self.contrast_toggle_btn.setToolTip("Toggle Enhanced Contrast On/Off")
        self.contrast_toggle_btn.setCheckable(True)
        self.contrast_toggle_btn.setFixedSize(24, 24)
        self.contrast_toggle_btn.toggled.connect(self.toggle_contrast)
        toolbar.addWidget(self.contrast_toggle_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        # Gamma/brightness toggle button
        self.gamma_toggle_btn = QToolButton()
        self.gamma_toggle_btn.setText("💡")  # Light bulb for brightness/gamma
        self.gamma_toggle_btn.setToolTip("Toggle Enhanced Brightness On/Off")
        self.gamma_toggle_btn.setCheckable(True)
        self.gamma_toggle_btn.setFixedSize(24, 24)
        self.gamma_toggle_btn.toggled.connect(self.toggle_gamma)
        toolbar.addWidget(self.gamma_toggle_btn)

        spacer = QWidget()
        spacer.setFixedWidth(8)
        toolbar.addWidget(spacer)

        # Previous image button (undo image)
        prev_btn = QToolButton()
        prev_btn.setText("⬅")
        prev_btn.setToolTip("Previous Image (Go Back in History)")
        prev_btn.setFixedSize(24, 24)
        prev_btn.clicked.connect(self.show_previous_image)
        toolbar.addWidget(prev_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        next_btn = QToolButton()
        next_btn.setText("🎲")
        next_btn.setToolTip("Show Next Random Image")
        next_btn.setFixedSize(24, 24)
        next_btn.clicked.connect(self._manual_next_image)
        toolbar.addWidget(next_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        self.timer_button = QToolButton()
        self.timer_button.setCheckable(True)
        self.timer_button.setText("⚡")
        self.timer_button.setToolTip("Toggle Auto Advance")
        self.timer_button.setFixedSize(24, 24)
        self.timer_button.toggled.connect(self.toggle_timer)
        toolbar.addWidget(self.timer_button)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        self.timer_spin = QSpinBox()
        self.timer_spin.setRange(1, 3600)
        self.timer_spin.setValue(self.timer_interval)
        self.timer_spin.setSuffix(" s")
        self.timer_spin.setFixedHeight(24)
        self.timer_spin.setFixedWidth(60)
        self.timer_spin.valueChanged.connect(self.update_timer_interval)
        toolbar.addWidget(self.timer_spin)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        self.circle_timer = CircularCountdown(self.timer_spin.value())
        self.circle_timer.set_parent_viewer(self)
        toolbar.addWidget(self.circle_timer)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

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
        self.contrast_slider.setRange(-500, 500)
        self.contrast_slider.setValue(self.contrast_value)
        self.contrast_slider.setFixedWidth(70)  # Increased width for easier clicking
        self.contrast_slider.setFixedHeight(24)  # Increased height for easier clicking
        self.contrast_slider.setStyleSheet("QSlider { margin: 2px 4px; }")  # Add margins around slider
        self.contrast_slider.setToolTip("Contrast: 0=Normal, -500=Flat, +500=Extreme")
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

        # Small spacer before reset button
        spacer3 = QWidget()
        spacer3.setFixedWidth(6)
        toolbar.addWidget(spacer3)

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
        # Reset button states
        if hasattr(self, 'flip_h_btn'):
            self.flip_h_btn.setChecked(False)
        if hasattr(self, 'flip_v_btn'):
            self.flip_v_btn.setChecked(False)
        available = [img for img in self.images if img not in self.history]
        if not available:
            self.history.clear()
            self.history_list.clear()
            available = self.images[:]
        img_path = random.choice(available)
        self.display_image(img_path)
        self.add_to_history(img_path)
        self.current_image = img_path
        self.update_image_info(img_path)
        self.set_status_path(img_path)
        if self._auto_advance_active:
            self.timer_remaining = self.timer_spin.value()
            self._update_ring()

    def _manual_next_image(self):
        self.show_random_image()

    def display_image(self, img_path):
        # Create cache key including enhancement settings, rotation, and flips
        cache_key = f"{img_path}_{self.grayscale_value}_{self.contrast_value}_{self.gamma_value}_{self.rotation_angle}_{self.flipped_h}_{self.flipped_v}"
        
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
            
            # Apply enhancements only if needed
            if self.grayscale_value > 0 or self.contrast_value != 50 or self.gamma_value != 0:
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
        
        # Draw lines on the scaled pixmap if any exist
        if self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines:
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
                        painter.drawLine(display_start_x, display_start_y, display_end_x, display_end_y)
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

    def apply_fast_enhancements(self, pixmap):
        """Apply fast image enhancements using Qt's optimized color effects."""
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
        if self.contrast_value != 0 or self.gamma_value != 0:
            # Create enhanced version using QPainter composition
            enhanced = QPixmap(pixmap.size())
            enhanced.fill(Qt.transparent)
            
            painter = QPainter(enhanced)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Fast contrast approximation using opacity and blend modes
            if self.contrast_value != 0:
                # Extended range: -500 to +500, where 0 is normal
                contrast_factor = self.contrast_value / 100.0  # -5 to +5
                
                if contrast_factor > 0:
                    # Increase contrast dramatically using multiple overlay passes
                    painter.drawPixmap(0, 0, pixmap)
                    painter.setCompositionMode(QPainter.CompositionMode_Overlay)
                    
                    # Much stronger base effect - make it immediately noticeable
                    base_opacity = min(1.0, abs(contrast_factor) * 0.8)  # Much stronger: 0.8 instead of 0.2
                    painter.setOpacity(base_opacity)
                    painter.drawPixmap(0, 0, pixmap)
                    
                    # Add multiple passes for stronger effect even at low values
                    num_passes = max(1, int(abs(contrast_factor) * 2))  # More passes for stronger effect
                    for i in range(min(num_passes, 4)):  # Up to 4 passes
                        painter.setOpacity(min(0.7, abs(contrast_factor) * 0.3))  # Much stronger passes
                        painter.drawPixmap(0, 0, pixmap)
                        
                    # For extreme values, add even more dramatic effects
                    if self.contrast_value > 300:
                        painter.setCompositionMode(QPainter.CompositionMode_HardLight)
                        painter.setOpacity(0.6)
                        painter.drawPixmap(0, 0, pixmap)
                else:
                    # Decrease contrast much more dramatically
                    mid_gray = QPixmap(pixmap.size())
                    mid_gray.fill(QColor(128, 128, 128))  # 50% gray
                    
                    painter.drawPixmap(0, 0, pixmap)
                    painter.setCompositionMode(QPainter.CompositionMode_SoftLight)
                    
                    # Much stronger low contrast effect
                    base_opacity = min(1.0, abs(contrast_factor) * 0.9)  # Much stronger: 0.9 instead of 0.2
                    painter.setOpacity(base_opacity)
                    painter.drawPixmap(0, 0, mid_gray)
                    
                    # Add multiple gray overlay passes for very flat look
                    num_passes = max(1, int(abs(contrast_factor) * 1.5))
                    for i in range(min(num_passes, 3)):
                        painter.setOpacity(min(0.8, abs(contrast_factor) * 0.4))
                        painter.drawPixmap(0, 0, mid_gray)
            else:
                painter.drawPixmap(0, 0, pixmap)
            
            # Fast gamma approximation using multiply blend
            if self.gamma_value != 0:
                # Extended range: -500 to +500, where 0 is normal  
                gamma_factor = self.gamma_value / 100.0  # -5 to +5
                
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
        
        # Handle image display resize
        if self.current_image:
            self.display_image(self.current_image)

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
                self.show_random_image()
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
        if self.current_image and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
            self.display_image(self.current_image)

    def choose_line_color(self):
        """Open color picker dialog to choose line color"""
        color = QColorDialog.getColor(self.line_color, self, "Choose Line Color")
        if color.isValid():
            self.line_color = color
            # Update button background to show selected color
            self.line_color_btn.setStyleSheet(f"QToolButton {{ background-color: {self.line_color.name()}; border: 1px solid #666; }}")
            # Redraw current image with new color if there are lines
            if self.current_image and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
                self.display_image(self.current_image)

    def set_line_color(self, color_hex):
        """Set line color from hex string (used by preset color buttons)"""
        self.line_color = QColor(color_hex)
        # Update main color button background to show selected color
        self.line_color_btn.setStyleSheet(f"QToolButton {{ background-color: {self.line_color.name()}; border: 1px solid #666; }}")
        # Redraw current image with new color if there are lines
        if self.current_image and (self.drawn_lines or self.drawn_horizontal_lines or self.drawn_free_lines):
            self.display_image(self.current_image)

    def add_line(self, x_position):
        if x_position not in self.drawn_lines:
            self.drawn_lines.append(x_position)
            if self.current_image:
                self.display_image(self.current_image)

    def add_hline(self, y_position):
        if y_position not in self.drawn_horizontal_lines:
            self.drawn_horizontal_lines.append(y_position)
            if self.current_image:
                self.display_image(self.current_image)

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
            
            # Reset for next line
            self.current_line_start = None
            
            # Update display
            if self.current_image:
                self.display_image(self.current_image)
            
            self.status.showMessage(f"Line drawn from ({start_x:.0f}, {start_y:.0f}) to ({end_x:.0f}, {end_y:.0f})")

    def clear_lines(self):
        self.drawn_lines.clear()
        self.drawn_horizontal_lines.clear()
        self.drawn_free_lines.clear()
        self.current_line_start = None
        if self.current_image:
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
            if self.current_image:
                self.display_image(self.current_image)
            self.status.showMessage("Removed last line")
        else:
            self.status.showMessage("No lines to remove")

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
                
                # Hide menu bar and status bar in fullscreen
                if hasattr(self, 'menuBar'):
                    self.menuBar().hide()
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
                
                # Show menu bar and status bar again
                if hasattr(self, 'menuBar'):
                    self.menuBar().show()
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
            
            # Method 4: Show menu bar and status bar
            if hasattr(self, 'menuBar'):
                self.menuBar().show()
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
                
            if hasattr(self, 'fullscreen_action'):
                self.fullscreen_action.setChecked(False)
            
            self.status.showMessage("Fullscreen mode force exited")
            print(f"Force exit complete. Window state: {self.windowState()}")
            
        except Exception as e:
            print(f"Error in force_exit_fullscreen: {e}")
            # Last resort: try to close and restart
            print("Last resort: attempting emergency close...")
            self.close()

    def toggle_grayscale(self, checked):
        self.grayscale_value = 100 if checked else 0
        self.grayscale_slider.setValue(self.grayscale_value)
        # Update toggle button state
        if hasattr(self, 'grayscale_toggle_btn'):
            self.grayscale_toggle_btn.setChecked(checked)
        # Clear caches and force immediate update
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def toggle_contrast(self, checked=None):
        """Toggle contrast between normal (50) and enhanced (100)"""
        if checked is None:
            # Toggle between current and normal
            self.contrast_value = 50 if self.contrast_value != 50 else 100
            checked = self.contrast_value != 50
        else:
            # Set based on checked state
            self.contrast_value = 100 if checked else 50
        self.contrast_slider.setValue(self.contrast_value)
        # Update toggle button state
        if hasattr(self, 'contrast_toggle_btn'):
            self.contrast_toggle_btn.setChecked(checked)
        # Clear caches and force immediate update
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def toggle_gamma(self, checked=None):
        """Toggle gamma between normal (0) and enhanced (100)"""
        if checked is None:
            # Toggle between current and normal
            self.gamma_value = 0 if self.gamma_value != 0 else 100
            checked = self.gamma_value != 0
        else:
            # Set based on checked state
            self.gamma_value = 100 if checked else 0
        self.gamma_slider.setValue(self.gamma_value)
        # Update toggle button state
        if hasattr(self, 'gamma_toggle_btn'):
            self.gamma_toggle_btn.setChecked(checked)
        # Clear caches and force immediate update
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

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
        # Update toggle button state
        if hasattr(self, 'grayscale_toggle_btn'):
            self.grayscale_toggle_btn.setChecked(value > 0)
        # Clear enhancement cache when settings change
        self.enhancement_cache.clear()
        self.scaled_cache.clear()  # Also clear scaled cache to force refresh
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def update_contrast(self, value):
        self.contrast_value = value
        # Update toggle button state
        if hasattr(self, 'contrast_toggle_btn'):
            self.contrast_toggle_btn.setChecked(value != 50)
        # Clear enhancement cache when settings change
        self.enhancement_cache.clear()
        self.scaled_cache.clear()  # Also clear scaled cache to force refresh
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def update_gamma(self, value):
        self.gamma_value = value
        # Update toggle button state
        if hasattr(self, 'gamma_toggle_btn'):
            self.gamma_toggle_btn.setChecked(value != 50)
        # Clear enhancement cache when settings change
        self.enhancement_cache.clear()
        self.scaled_cache.clear()  # Also clear scaled cache to force refresh
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def reset_enhancements(self):
        self.grayscale_slider.setValue(0)
        self.contrast_slider.setValue(50)
        self.gamma_slider.setValue(0)
        self.grayscale_value = 0
        self.contrast_value = 50
        self.gamma_value = 0
        # Update toggle button states
        if hasattr(self, 'grayscale_toggle_btn'):
            self.grayscale_toggle_btn.setChecked(False)
        if hasattr(self, 'contrast_toggle_btn'):
            self.contrast_toggle_btn.setChecked(False)
        if hasattr(self, 'gamma_toggle_btn'):
            self.gamma_toggle_btn.setChecked(False)
        # Clear all caches when resetting
        self.enhancement_cache.clear()
        self.scaled_cache.clear()
        self._update_enhancement_menu_states()
        if self.current_image:
            self.display_image(self.current_image)

    def reset_zoom(self):
        """Reset image zoom and pan to 100%"""
        if self.image_label:
            self.image_label.reset_zoom()
            if self.current_image:
                self.display_image(self.current_image)
            self.status.showMessage("Zoom reset to 100%")

    def zoom_in(self):
        """Zoom in by 15%"""
        if self.image_label:
            current_zoom = getattr(self.image_label, 'zoom_factor', 1.0)
            new_zoom = min(current_zoom * 1.15, 8.0)
            self.image_label.zoom_factor = new_zoom
            if self.current_image:
                self.display_image(self.current_image)
            self.status.showMessage(f"Zoom: {new_zoom:.1f}x")

    def zoom_out(self):
        """Zoom out by 15%"""
        if self.image_label:
            current_zoom = getattr(self.image_label, 'zoom_factor', 1.0)
            new_zoom = max(current_zoom / 1.15, 0.1)
            self.image_label.zoom_factor = new_zoom
            if self.current_image:
                self.display_image(self.current_image)
            self.status.showMessage(f"Zoom: {new_zoom:.1f}x")

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
            # Always try to exit fullscreen on Escape
            if self.is_fullscreen:
                print("Escape pressed - exiting fullscreen")
                if event.modifiers() & Qt.ControlModifier:
                    print("Ctrl+Esc pressed - force exiting fullscreen")
                    self.force_exit_fullscreen()
                else:
                    self.exit_fullscreen()
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
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()

    def show_next_image(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            img_path = self.history[self.history_index]
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()
        else:
            self.show_random_image()

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
                self.show_random_image()
            else:
                self.image_label.setText("No images found in selected folder or its subfolders.")
            self._reset_timer()

if __name__ == "__main__":
    setup_image_allocation_limit()  # Increase image allocation limit at startup
    app = QApplication(sys.argv)
    app.setStyleSheet(get_adaptive_stylesheet())  # Use OS-adaptive theme
    viewer = RandomImageViewer()
    
    # Apply dark title bar BEFORE showing the window for professional appearance
    if is_windows_dark_mode():
        print("DEBUG: Applying dark title bar before window show")
        # Apply immediately after window creation but before show
        QTimer.singleShot(0, lambda: enable_windows_dark_title_bar(viewer))
    
    viewer.show()
    
    sys.exit(app.exec())
