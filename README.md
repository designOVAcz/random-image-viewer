# Random Image Viewer

A simple, modern, **cross-platform** desktop app to view random images from any folder (including subfolders). Great for artists, inspiration, or just browsing your photo collection!

---

## Features

- 📁 **Open Any Folder:** Load images from a folder and its subfolders.
- 🎲 **Random Image:** Instantly show a random image, avoiding repeats until all are seen.
- ⏮️ ⏭️ **History Navigation:** Go back and forward through viewed images.
- 🕒 **Auto-Advance Timer:** Automatically switch to a new random image at set intervals, with a circular countdown overlay.
- 🔍 **Zoom:** Zoom in/out/reset with mouse wheel, keyboard, or context menu.
- �️ **Fullscreen Mode:** Toggle fullscreen with F11 key or toolbar button for immersive viewing.
- �🖱️ **Smart Context Menu:** Right-click for actions (auto-hides when zoomed to avoid pan interference).
- 🎨 **OS-Adaptive Theme:** Automatically detects Windows dark/light mode preferences.
- ⌨️ **Full Keyboard Support:** Complete shortcut system for all operations.
- 🔄 **Image Transformations:** Flip horizontal/vertical with visual state indicators.
- 📐 **Professional Line Drawing:** Three-mode annotation system with free line tool.
- 🖥️ **Cross-platform:** Works on Windows, macOS, and Linux.

---

## 🆕 **Latest Enhancements (January 2025)**

### �️ **Fullscreen Mode**
- **Immersive Viewing**: `⛶` toolbar button and `F11` shortcut for fullscreen
- **Easy Exit**: Press `Esc` or `F11` to return to windowed mode
- **State Preservation**: Automatically restores window size and position
- **Context Menu Integration**: Fullscreen toggle accessible via right-click
- **Visual Feedback**: Button state indicates current fullscreen status

### �🔄 **Image Flip Operations**
- **Horizontal Flip**: `⟷` button and `Ctrl+H` shortcut
- **Vertical Flip**: `↕` button and `Ctrl+V` shortcut  
- **Visual State Indicators**: Checkable buttons show current flip status
- **Context Menu Integration**: Flip options accessible via right-click
- **Smart Reset**: Flips automatically reset when navigating to new images

### 🎨 **OS-Adaptive Theme System**
- **Windows Dark Mode Detection**: Automatically reads Windows registry settings
- **Dual Theme Support**: 
  - Professional dark theme for dark mode users
  - Clean light theme matching Windows 11 aesthetics
- **Automatic Selection**: Seamlessly adapts to user's OS preferences
- **Cross-Platform Fallback**: Defaults to dark theme on non-Windows systems

### 🖱️ **Enhanced Context Menu**
- **Smart Behavior**: Automatically hides when zoomed in to avoid panning interference
- **Comprehensive Options**: 
  - Navigation (Previous/Next, Open folder)
  - Zoom controls with displayed keyboard shortcuts
  - Image transformations (Flip operations)
  - Quick settings access
- **Professional Layout**: Well-organized menu structure with separators

### ⌨️ **Extended Keyboard Shortcuts**
| Shortcut | Action |
|----------|--------|
| `←` / `→` | Navigate image history |
| `F11` | Toggle fullscreen mode |
| `Esc` | Exit fullscreen mode |
| `Ctrl++` / `Ctrl+=` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+0` | Reset zoom to 100% |
| `Ctrl+H` | Flip horizontal |
| `Ctrl+V` | Flip vertical |

### 🛡️ **Improved Stability**
- **Enhanced Error Handling**: Better graceful degradation for corrupted files
- **Memory Management**: Optimized cache clearing for transformation operations
- **Performance Tuning**: Improved bounds checking prevents line rendering issues

---

## Complete Feature Summary - Enhanced Random Image Viewer

### 🎯 **New Feature: Free Line Drawing Tool**
- **Two-click line creation**: Draw straight lines between any two points
- **UI Integration**: New `╱` toolbar button with mutually exclusive mode behavior
- **Full rotation support**: Correct coordinate transformation for all rotation angles
- **Enhanced line management**: Unified undo/clear system for all line types
- **Robust rendering**: Improved bounds checking to prevent lines disappearing at certain zoom levels

### 🚀 **Performance & Memory Optimizations**

#### **Enhanced Caching System**
- **Dual-layer caching**: Separate caches for base pixmaps and enhanced versions
- **LRU-like behavior**: Automatic cache management with configurable size limits
- **Smart cache keys**: Include enhancement settings, rotation, zoom, and pan in cache keys
- **Garbage collection**: Periodic memory cleanup to prevent memory leaks
- **Cache invalidation**: Intelligent clearing when settings change

#### **Optimized Image Loading**
- **Safe loading system**: Error handling for corrupted or unsupported image files
- **Lazy thumbnail generation**: Only create thumbnails when history panel is visible
- **Scaled reading**: Direct thumbnail scaling during file read for faster performance
- **Large file handling**: Special handling and size display for files >10MB

#### **Debounced Resize Handling**
- **Resize timer**: 100ms debounce to prevent excessive recalculations during window resizing
- **Delayed processing**: `_delayed_resize()` method to batch resize operations
- **Performance monitoring**: Size tracking to optimize resize behavior

### 🖥️ **Enhanced UI & Layout System**

#### **Responsive Toolbar Layout**
- **Dynamic two-row mode**: Automatically moves enhancement controls to second toolbar row when window width < 900px
- **Intelligent switching**: Hysteresis prevents rapid mode switching
- **State preservation**: Maintains slider values and settings during layout changes
- **Visual feedback**: Debug logging and smooth transitions

#### **Advanced Enhancement Controls**
- **Extended ranges**: 
  - Contrast: 0-200 (was more limited)
  - Gamma: 0-200 with extreme values support
  - Grayscale: 0-100 with smooth blending
- **Fast rendering**: QPainter-based effects instead of pixel manipulation
- **Multiple effect passes**: Additional overlay/multiply passes for extreme values
- **Clickable sliders**: Enhanced slider interaction

### 🔄 **Image Processing Improvements**

#### **Unified Coordinate System**
- **Consistent zoom handling**: Same logic for ALL zoom levels (no special cases)
- **Accurate transformations**: Precise coordinate mapping for rotation and scaling
- **Pan integration**: Proper offset handling in all drawing operations
- **Bounds tolerance**: 10-pixel tolerance to prevent precision-related rendering issues

#### **Enhanced Image Display**
- **Rotation caching**: Cache rotated versions to improve performance
- **Quality preservation**: High-quality scaling with Qt.SmoothTransformation
- **Memory efficient**: Optimized pixmap creation and management
- **Background filling**: Proper black background for images smaller than viewport

### 📐 **Advanced Line Drawing System**

#### **Three-Mode System**
- **Vertical lines**: Original functionality preserved
- **Horizontal lines**: Original functionality preserved  
- **Free lines**: New two-point line drawing capability
- **Mutual exclusion**: Only one mode active at a time
- **State management**: Proper mode switching and cursor updates

#### **Comprehensive Line Management**
- **Smart undo**: Prioritized removal (free → horizontal → vertical)
- **Unified clearing**: Single button clears all line types
- **Thickness control**: 1-10px configurable thickness for all line types
- **Persistence**: Lines cleared automatically on new image navigation
- **Copy integration**: All lines included in clipboard copy operations

### 🎨 **Visual & UX Enhancements**

#### **Status Bar Improvements**
- **Real-time feedback**: Clear status messages for all drawing operations
- **Coordinate display**: Shows click coordinates during line creation
- **Operation guidance**: Step-by-step instructions for complex operations
- **File information**: Enhanced file size and dimension display

#### **Cursor Management**
- **Context-aware cursors**: Different cursors for different drawing modes
- **Visual feedback**: Cross cursor for line drawing, arrow for navigation
- **Mode indication**: Cursor changes reflect current tool state

### 🛠️ **System Integration**

#### **Enhanced History System**
- **Improved navigation**: Better forward/backward history management
- **Thumbnail optimization**: Conditional thumbnail creation for performance
- **Memory efficient**: Lazy loading and cleanup of history items
- **Visual indicators**: Better history panel integration

#### **Cross-Platform Compatibility**
- **File URL handling**: Proper Windows/Unix file path handling
- **Explorer integration**: Platform-specific folder opening
- **Path display**: Cross-platform file path presentation

### 🔧 **Technical Infrastructure**

#### **Error Handling**
- **Safe image loading**: Graceful handling of corrupted files
- **Exception management**: Try-catch blocks for critical operations
- **User feedback**: Clear error messages in status bar
- **Fallback behaviors**: Graceful degradation when operations fail

#### **Memory Management**
- **Cache size limits**: Configurable maximum cache sizes
- **Automatic cleanup**: Periodic garbage collection
- **Memory monitoring**: Cache hit/miss optimization
- **Resource cleanup**: Proper painter and resource disposal

This represents a significant evolution from a basic random image viewer to a professional-grade image analysis and annotation tool with enterprise-level performance optimizations and memory management.

---

## Installation

1. **Clone this repo:**
   ```sh
   git clone https://github.com/YOUR_USERNAME/random-image-viewer.git
   cd random-image-viewer
   ```

2. **Install [uv](https://github.com/astral-sh/uv) (if you don't have it):**
   ```sh
   pip install uv
   ```

3. **Install dependencies:**
   ```sh
   uv pip install -r pyproject.toml
   # or just
   uv pip install pyside6
   ```

### 🎨 **Theme Detection (Windows)**
On Windows systems, the application automatically detects your OS dark/light mode preference from the registry. No additional setup required - it just works!

---

## How to Run

- **With uv:**
  ```sh
  uv run main.py
  ```
- **Or with Python:**
  ```sh
  python main.py
  ```

---

## Usage

1. **Open a Folder:**
   - Right-click the image area and select "Open Folder".
2. **Show Random Image:**
   - Right-click and choose "Next Random Image", or press the **Right Arrow** key.
3. **Navigate History:**
   - Use **Left/Right Arrow** keys, or the context menu.
   - Enable the history panel from the context menu to click through viewed images.
4. **Auto-Advance:**
   - Enable from the context menu ("Enable Timer").
   - Adjust interval in the context menu.
   - A circular timer appears as an overlay.
5. **Zoom:**
   - Use mouse wheel over the image, keyboard shortcuts, or context menu.
6. **Other Actions:**
   - Flip image, toggle grayscale, change background, and more—all from the context menu.

---

## Keyboard Shortcuts & Context Menu Actions

### ⌨️ **Keyboard Shortcuts**
- **Left Arrow:** Previous image
- **Right Arrow:** Next image (random if at end)
- **F11:** Toggle fullscreen mode *(NEW)*
- **Esc:** Exit fullscreen mode *(NEW)*
- **Ctrl + +:** Zoom in
- **Ctrl + -:** Zoom out
- **Ctrl + 0:** Reset zoom
- **Ctrl + H:** Flip image horizontally *(NEW)*
- **Ctrl + V:** Flip image vertically *(NEW)*

### 🖱️ **Smart Context Menu (right-click)**
*Automatically hides when zoomed to avoid panning interference*
- **Navigation:**
  - Open Folder
  - Previous/Next Random Image
- **Zoom Controls:**
  - Zoom In (`Ctrl++`)
  - Zoom Out (`Ctrl+-`)
  - Reset Zoom (`Ctrl+0`)
- **View Options:** *(NEW)*
  - Fullscreen (`F11`)
- **Image Transformations:** *(NEW)*
  - Flip Horizontal (`Ctrl+H`)
  - Flip Vertical (`Ctrl+V`)
- **Settings:**
  - Grayscale Toggle

### 🎯 **Quick Usage Guide**

#### Image Viewing & Navigation
1. **Fullscreen Mode**: Press `F11` or click `⛶` for immersive viewing experience
   - Press `Esc` or `F11` again to exit fullscreen
   - All features work in fullscreen mode
2. **Zoom & Pan**: Use mouse wheel to zoom, right-click drag to pan when zoomed

#### Image Transformation Workflow
1. **Flip Operations**: Use toolbar buttons `⟷` `↕` or keyboard shortcuts `Ctrl+H` `Ctrl+V`
   - Buttons show current state (highlighted when active)
   - Flips automatically reset when navigating to new images
2. **Rotation + Flip**: Combine rotation (`↻` button) with flips for complete control
3. **Line Drawing**: All transformation work seamlessly with line annotation tools
  - Zoom In/Out/Reset
  - Enable Timer & set interval
  - Show History Panel
  - Grayscale, Flip, Background color, etc.

---

## Screenshots

![Main Window](screenshots/main_window.png)
*Main window with random image loaded*

![History Panel](screenshots/history_panel.png)
*History panel enabled and showing viewed images*

![Pie Timer and Toolbar](screenshots/timer_toolbar.png)
*Pie timer overlay and auto-advance controls*

---

## Compiling to a Standalone Binary

You can compile this app to a standalone executable for Windows, Linux, or Mac using [PyInstaller](https://pyinstaller.org/).

1. **Install PyInstaller:**
   ```sh
   uv pip install pyinstaller
   ```
2. **Build the Executable:**
   ```sh
   pyinstaller --noconfirm --onefile --windowed main.py
   ```
   - The binary will be in the `dist/` folder.
   - For cross-compiling, build on the target OS or use a cross-compilation toolchain.

---

## Requirements

- Python 3.8+
- [PySide6](https://pypi.org/project/PySide6/)

---

## License

MIT License.

---


**Enjoy browsing your images!**




