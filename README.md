# Random Image Viewer

A simple, modern, cross-platform desktop app to view random images from any folder (including subfolders). Great for artists, inspiration, or just browsing your photo collection!

- Edited and tested for Windows OS
---

## Features

- 📁 **Open Any Folder:** Load images from a folder and its subfolders.
- 🎲 **Smart Navigation:** Random image viewing with alphabetical sorting toggle.
- 🔀 **Sorting Toggle:** Switch between random and alphabetical order with one click.
- ⏮️ ⏭️ **History Navigation:** Go back and forward through viewed images.
- 🕒 **Auto-Advance Timer:** Automatically switch to a new random image at set intervals, with a circular countdown overlay.
- 🔍 **Zoom:** Zoom in/out/reset with mouse wheel, keyboard, or context menu.
- 🖥️ **Fullscreen Mode:** Toggle fullscreen with F11 key or toolbar button for immersive viewing.
- 👁️ **Minimal Mode:** Hide all UI elements (toolbars, status bar, window decorations) for distraction-free viewing.
- 🖱️ **Smart Context Menu:** Right-click for actions (auto-hides when zoomed to avoid pan interference).
- 🎨 **OS-Adaptive Theme:** Automatically detects Windows dark/light mode preferences.
- ⌨️ **Full Keyboard Support:** Complete shortcut system for all operations.
- 🔄 **Image Transformations:** Flip horizontal/vertical with visual state indicators.
- 📐 **Professional Line Drawing:** Three-mode annotation system with free line tool.
- 🖥️ **Cross-platform:** Works on Windows, macOS, and Linux.

---

## 🆕 **Latest Enhancements**

### 🔀 **Smart Navigation System (NEW)**

Perfect for both random discovery and systematic browsing of image collections.

#### **🎲 Random Mode (Default)**
- **Intelligent Selection**: Shows random images while avoiding repeats until all are seen
- **Fresh Discovery**: Great for inspiration and exploring large collections
- **History Integration**: Previously viewed images excluded from random selection
- **Auto-Reset**: When all images viewed, history clears and cycle repeats

#### **🔤 Alphabetical Mode** 
- **Systematic Browsing**: Navigate through images in alphabetical order by filename
- **Predictable Navigation**: Perfect for organized collections and systematic review  
- **Sequential Flow**: Next/Previous buttons follow alphabetical sort order
- **Folder Integration**: Sorts across all subfolders in one unified sequence

#### **🔀 Toggle Control**
- **One-Click Switching**: `🔀` toolbar button toggles between modes instantly
- **Visual Feedback**: Button tooltip shows current mode ("Order: Random" or "Order: Alphabetical")
- **Status Messages**: Clear indication when switching modes
- **Mode Persistence**: Remembers your preferred mode across sessions

#### **🕒 Timer Integration**
- **Auto-Advance Respect**: Timer-based navigation follows selected mode
- **Seamless Operation**: Both modes work identically with auto-advance timer
- **Consistent Behavior**: Same navigation logic for manual and automatic progression

#### **⌨️ Keyboard Navigation**
- **Arrow Keys**: Left/Right arrows respect current sorting mode
- **History Navigation**: Back button always works regardless of mode
- **Context Menu**: Right-click "Next Image" follows current mode setting

#### **📁 Folder Opening Behavior**
- **Random Mode**: Opens with random image as before
- **Alphabetical Mode**: Opens with first image in alphabetical order
- **Instant Feedback**: Shows selected mode immediately upon folder opening

---

### 👁️ **Minimal Mode - Distraction-Free Viewing (NEW)**

Complete UI hiding system for immersive image viewing, perfect for presentations and clean screenshots.

#### **🎯 Features Hidden**
- **All Toolbars**: Main toolbar and enhancement controls completely hidden
- **Status Bar**: Bottom information bar removed
- **Window Decorations**: Title bar, borders, and window controls (minimize/maximize/close) removed
- **Clean Interface**: Pure image viewing experience with zero distractions

#### **🖱️ Window Control in Minimal Mode**
Advanced window manipulation when UI is hidden:

**Window Moving:**
- **Right-Click Drag**: Drag window from anywhere, including edges
- **No Context Menu Conflict**: Right-click drag overrides context menu
- **Smooth Movement**: Professional window dragging experience

**Window Resizing:**  
- **Edge Detection**: Move mouse to window edges to see resize cursors
- **Corner Resizing**: All 8 resize directions supported (↔, ↕, ↗, ↖, ↙, ↘)
- **Visual Feedback**: Standard Windows resize cursors for clear indication
- **Precise Control**: 10-pixel detection margin for easy targeting
- **Left-Click Resize**: Standard resize behavior on edges/corners

**Smart Interaction:**
- **Left-Click**: Resize on edges, drag elsewhere
- **Right-Click**: Always drag (even on edges) for easy window movement
- **Professional Feel**: Matches standard Windows application behavior

#### **🔄 Easy Restoration**
- **Right-Click Menu**: Simple right-click without dragging shows context menu
- **"Show/Hide UI Elements"**: Toggle menu item with checkbox state indicator
- **Temporary Message**: 2-second status message before complete UI hiding
- **One-Click Return**: Instantly restore all UI elements

#### **⚙️ Technical Implementation**
- **Frameless Window**: Uses Qt FramelessWindowHint for clean appearance
- **State Preservation**: Stores original window flags for proper restoration
- **Memory Efficient**: Minimal overhead when UI is hidden
- **Cross-Platform**: Works on Windows, macOS, and Linux

#### **🎯 Use Cases**
- **Presentations**: Clean image display without UI clutter
- **Photography Review**: Distraction-free image evaluation
- **Screenshot Capture**: Clean images for documentation
- **Fullscreen Enhancement**: Even cleaner than standard fullscreen mode
- **Artistic Display**: Gallery-style image presentation

#### **📱 Mobile-Style Experience**
- **Touch-Friendly**: Large drag areas for easy manipulation
- **Gesture-Like**: Intuitive right-click drag for movement
- **Professional Polish**: Smooth animations and visual feedback

---(including subfolders). Great for artists, inspiration, or just browsing your photo collection!

---

### CUBE LUT Support

**New Features Added:**

#### 🎨 **LUT Controls (in Enhancement Toolbar)**
- **📁 LUT Folder Button**: Select folder containing .cube LUT files
- **LUT Dropdown**: Choose from available LUTs (shows "None" + all found LUT names)
- **LUT Strength Slider**: Control LUT intensity (0-100%)

#### 🔧 **LUT Processing Engine**
- **CUBE File Parser**: Reads industry-standard .cube LUT files
- **3D Trilinear Interpolation**: Accurate color transformation
- **Strength Control**: Blend between original and LUT-processed image
- **Performance Optimized**: Cached processing for smooth real-time application

#### 🎛️ **Integration Features**
- **Cache System**: LUT settings included in image cache keys
- **Reset Support**: LUTs reset when using "Reset Enhancements"
- **Status Feedback**: Shows LUT loading status and current strength
- **Enhancement Pipeline**: LUTs applied after contrast/gamma/grayscale

#### 📁 **Usage Workflow**
1. **Click LUT folder button** 📁 to select folder with .cube files
2. **Choose LUT** from dropdown (e.g., "Cinematic", "Vintage", "Cold")
3. **Adjust strength** with slider (0% = off, 100% = full effect)
4. **See instant results** applied to current image

#### 🎯 **Technical Features**
- **Support for standard CUBE format** (industry standard for color grading)
- **Variable LUT sizes** (supports 16x16x16, 32x32x32, 64x64x64, etc.)
- **Real-time application** with caching for performance
- **Non-destructive editing** - original image unchanged

### 🚀 GPU-Accelerated 3D LUT Processing (NEW)

Full LUT pipeline now runs on the GPU (OpenCL) for large images with seamless CPU fallback.

#### ✨ Highlights
* Automatic GPU detection (OpenCL) – uses fastest available GPU; falls back to CPU transparently.
* Real-time strength blending and trilinear LUT sampling.
* Zero-copy style upload of image + LUT for minimal overhead.
* Smart preview system: instant low-cost preview + async full-quality finalize.
* Lines (vertical / horizontal / free) now persist through LUT, zoom, and pan.

#### 🧠 Implementation Notes
* Host image memory (Qt `QImage::Format_RGB32`) is BGRA in memory; kernel reads as `uchar4` (x=B, y=G, z=R, w=A).
* 3D LUT stored as a flat `float` array (r,g,b) — NOT `float3`. (Important: OpenCL often pads `float3` to 16 bytes; using `float3*` caused psychedelic colors until replaced with flat `__global const float*`.)
* Indexing formula: `index = r + g*size + b*size*size` using integer truncation to mirror CPU path.
* Strength blending: `final = original*(1-strength) + lut*strength` executed per channel.
* Kernel caching avoids repeated build & retrieval overhead.

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
  - **UI Visibility Control**: Show/Hide UI Elements for minimal mode *(NEW)*
  - **Fullscreen Toggle**: Enter/Exit fullscreen mode *(NEW)*
  - Quick settings access
- **Professional Layout**: Well-organized menu structure with separators
- **Context Awareness**: Different options based on current state (fullscreen, UI visibility)

### ⌨️ **Extended Keyboard Shortcuts**
| Shortcut | Action |
|----------|--------|
| `←` / `→` | Navigate image history (respects Random/Alphabetical mode) |
| `F11` | Toggle fullscreen mode |
| `Esc` | Exit fullscreen mode |
| `Ctrl++` / `Ctrl+=` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+0` | Reset zoom to 100% |
| `Ctrl+H` | Flip horizontal |
| `Ctrl+V` | Flip vertical |

**Navigation Behavior:**
- **Random Mode**: Arrow keys navigate through viewed history, then show new random images
- **Alphabetical Mode**: Arrow keys follow strict alphabetical order through entire collection
- **Mode Toggle**: Use `🔀` toolbar button to switch between navigation modes

### 🛡️ **Improved Stability**
- **Enhanced Error Handling**: Better graceful degradation for corrupted files
- **Memory Management**: Optimized cache clearing for transformation operations
- **Performance Tuning**: Improved bounds checking prevents line rendering issues

---

This represents a significant evolution from a basic random image viewer to a professional-grade image analysis and annotation tool with enterprise-level performance optimizations and memory management.

---

## Installation

1. **Clone this repo:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/random-image-viewer.git
    cd random-image-viewer
    ```

2. **Install dependencies:**

    ```bash
    pip install PySide6
    ```

---

## How to Run

### Windows/macOS/Linux

- Open a terminal in the project folder.
- Run:
    ```bash
    python main.py
    ```

> **Note:** On some systems, you may need to use `python` instead of `python3` depending on how Python is installed.

---

## Usage

1. **Open a Folder:**
   - Right-click the image area and select "Open Folder", or click the 📁 toolbar button.

2. **Navigation Modes:**
   - **Random Mode (Default)**: Click 🎲 button or right-click "Next Image" for random selection
   - **Alphabetical Mode**: Toggle with 🔀 button to browse images in alphabetical order
   - **Mode Switching**: Click the 🔀 button to switch between Random and Alphabetical modes

3. **Navigate Images:**
   - Use **Left/Right Arrow** keys (follows current mode)
   - Use toolbar navigation buttons
   - Enable history panel to click through previously viewed images

4. **Viewing Modes:**
   - **Standard**: Full UI with all controls visible
   - **Fullscreen**: Press F11 or click ⛶ button for immersive viewing
   - **Minimal Mode**: Right-click → "Show/Hide UI Elements" for distraction-free viewing
     - Right-click and drag to move window in minimal mode
     - Hover edges to resize with standard cursors

5. **Auto-Advance:**
   - Enable with ⚡ toolbar button or from context menu
   - Adjust interval with timer spinner control
   - Works with both Random and Alphabetical modes
   - Circular timer overlay shows remaining time

6. **Zoom & Pan:**
   - Use mouse wheel over image, keyboard shortcuts, or context menu
   - Right-click drag to pan when zoomed in

7. **Image Enhancement:**
   - Use toolbar sliders for grayscale, contrast, and gamma adjustments
   - Apply LUTs for professional color grading
   - Toggle effects on/off with dedicated buttons

8. **Line Drawing & Annotation:**
   - Use 📏 (vertical), ━ (horizontal), or ╱ (free) line tools
   - Adjust line thickness and color
   - Lines persist through zoom, pan, and image effects

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
  - Previous/Next Image (follows current Random/Alphabetical mode)
- **Zoom Controls:**
  - Zoom In (`Ctrl++`)
  - Zoom Out (`Ctrl+-`)
  - Reset Zoom (`Ctrl+0`)
- **View Options:** *(ENHANCED)*
  - Fullscreen (`F11`) / Exit Fullscreen (`Esc`)
  - **Show/Hide UI Elements** - Toggle minimal mode *(NEW)*
- **Image Transformations:**
  - Flip Horizontal (`Ctrl+H`)
  - Flip Vertical (`Ctrl+V`)
- **Settings:**
  - Grayscale Toggle
  - Enhanced contrast and other image adjustments

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

## Screenshot

![Main Window](screenshots/main_window.png)

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

#### 🛠️ **Troubleshooting**
| Symptom | Cause | Fix |
|---------|-------|-----|
| Wild / wrong (psychedelic) colors | Old kernel using `float3*` (alignment/padding) | Update to version using flat float LUT buffer |
| All black output | GPU kernel compiling but LUT strength 0 or invalid LUT size | Check LUT strength slider & ensure .cube loaded |
| Blue tint after drawing lines | Format mismatch (RGBA vs RGB32) | Ensure image converted to `Format_RGB32` before GPU line kernel |
| GPU not used | No OpenCL platform or image below threshold | Install drivers / PyOpenCL or enlarge image |

Enable verbose console to confirm messages like:
```
Using GPU for async LUT processing (WIDTHxHEIGHT, lines: True)
GPU LUT processing complete - finalizing...
```

#### 🧪 Validation Tip
To verify GPU vs CPU parity: apply a neutral LUT (identity) – output must match original (apart from minor rounding < 1 level).

#### 🔄 Free Line & Zoom Behavior
Lines are reapplied after each LUT preview/final pass and after zoom/pan via a fast overlay path (`_fast_line_update`). If you still lose free lines, ensure you didn't rotate + disable lines; rotation fallback will trigger a full redraw including lines.

#### 📈 Performance
Typical speed-up on large 32MP images: multi-second CPU → sub-second GPU (device dependent).

---

## License

MIT License.

---


**Enjoy browsing your images!**











