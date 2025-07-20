# 🖥️ Monitor Brightness Control

<div align="center">

![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Linux-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-green.svg)
![DDC/CI](https://img.shields.io/badge/DDC%2FCI-Compatible-orange.svg)

**A user-friendly controller for adjusting brightness, contrast, and input source of external monitors via DDC/CI on Linux**

[📥 Installation](#-installation) • [📚 Usage](#-usage) • [⚙️ Configuration](#%EF%B8%8F-configuration) • [🤝 Contributing](#-contributing)

</div>

---

## ✨ Features

🎛️ **Multiple Interfaces**  
- Command-line interface with intuitive commands  
- Modern GUI with real-time sliders and system tray integration  
- Background service for global hotkeys and automation  

📋 **Profile Management**  
- Pre-configured profiles: Day (bright), Night (dim), Gaming (max brightness)  
- Custom profile creation from current monitor settings  
- Automatic profile application on system startup  

⌨️ **Global Hotkeys**  
- `Ctrl + Alt + 1/2/3`: Switch between profiles instantly  
- `Ctrl + Alt + ↑/↓`: Quick brightness adjustment (+/-10%)  
- Fully customizable key combinations  

🖥️ **Multi-Monitor Support**  
- Automatic detection of DDC/CI compatible monitors  
- Individual control per monitor via bus addressing  
- Batch operations across all connected displays  

🚀 **Quick Presets**  
- One-click presets in GUI: Day, Night, Gaming modes  
- Percentage-based controls (0-100%) for easy adjustment  
- Real-time feedback and error handling  

---

## 📋 Prerequisites

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ddcutil i2c-tools
```

**Arch Linux:**
```bash
sudo pacman -S ddcutil
```

**Fedora:**
```bash
sudo dnf install ddcutil
```

### Hardware Requirements
- Monitor with DDC/CI support (most modern displays)
- DisplayPort or HDMI connection (recommended)
- I2C communication capability

### Permission Setup
```bash
# Add user to i2c group
sudo usermod -a -G i2c $USER

# Load i2c-dev module
sudo modprobe i2c-dev
echo 'i2c-dev' | sudo tee /etc/modules-load.d/i2c.conf

# Reboot or re-login to apply changes
```

---

## 🚀 Installation

### Option 1: Automated Installation (Recommended)
```bash
# Clone and run the installation script
git clone https://github.com/philling-dev/monitor-brightness-control.git
cd monitor-brightness-control
chmod +x install.sh
./install.sh
```

The script automatically:
- ✅ Installs system dependencies
- ✅ Sets up I2C permissions and udev rules
- ✅ Installs the Python package
- ✅ Creates desktop entries
- ✅ Configures systemd service (optional)

### Option 2: Manual Installation
```bash
# Install via pip
pip install monitor-brightness-control

# Or install from source
git clone https://github.com/philling-dev/monitor-brightness-control.git
cd monitor-brightness-control
pip install -e .
```

---

## 📖 Usage

### Command Line Interface

**Monitor Detection:**
```bash
# Detect available monitors
monitor-control detect

# Show detailed monitor information
monitor-control info
```

**Brightness Control:**
```bash
# Get current brightness
monitor-control brightness

# Set brightness to 80%
monitor-control brightness --value 80

# Control specific monitor (use bus number from detect)
monitor-control brightness --bus 4 --value 60
```

**Contrast Control:**
```bash
# Get current contrast
monitor-control contrast

# Set contrast to 75%
monitor-control contrast --value 75
```

### Graphical Interface

**Launch GUI:**
```bash
monitor-gui
```

**GUI Features:**
- 🎛️ Real-time brightness and contrast sliders
- 🎯 Quick preset buttons (Day/Night/Gaming)
- 🔔 System tray integration with minimize-to-tray
- 🔄 Automatic monitor detection and refresh
- ⚡ Instant feedback and error notifications

### Background Service & Hotkeys

**Start Background Service:**
```bash
# Start service manually
python -m monitor_control.service start

# Check service status
python -m monitor_control.service status
```

**Default Hotkeys:**
| Combination | Action |
|-------------|--------|
| `Ctrl + Alt + 1` | Apply Day profile (80% brightness) |
| `Ctrl + Alt + 2` | Apply Night profile (20% brightness) |
| `Ctrl + Alt + 3` | Apply Gaming profile (100% brightness) |
| `Ctrl + Alt + ↑` | Increase brightness (+10%) |
| `Ctrl + Alt + ↓` | Decrease brightness (-10%) |

---

## ⚙️ Configuration

Configuration files are stored in `~/.config/monitor-control/`:

### settings.json
```json
{
  "auto_apply_on_startup": true,
  "default_profile": "day",
  "hotkeys_enabled": true,
  "hotkeys": {
    "day_profile": ["ctrl", "alt", "1"],
    "night_profile": ["ctrl", "alt", "2"],
    "gaming_profile": ["ctrl", "alt", "3"],
    "brightness_up": ["ctrl", "alt", "up"],
    "brightness_down": ["ctrl", "alt", "down"]
  }
}
```

### profiles.json
Contains saved profiles with brightness and contrast settings for each monitor. Profiles are automatically created and can be customized through the GUI or CLI.

---

## 🖥️ Compatibility

### Supported Hardware
| Connection Type | Compatibility | Notes |
|----------------|---------------|--------|
| ✅ DisplayPort | Full Support | Recommended for best compatibility |
| ✅ HDMI | Full Support | Modern displays work well |
| ⚠️ DVI-D | Limited Support | Digital DVI may work |
| ❌ VGA | Not Supported | Analog connections don't support DDC/CI |

### Tested Distributions
- ✅ Ubuntu 20.04+ / Linux Mint 20+
- ✅ Debian 11+
- ✅ Fedora 35+
- ✅ Arch Linux / Manjaro
- ✅ openSUSE Leap/Tumbleweed
- 🧪 Other distributions (community tested)

---

## 🔧 Troubleshooting

### "ddcutil not found"
```bash
# Install ddcutil package
sudo apt install ddcutil  # Ubuntu/Debian
sudo pacman -S ddcutil     # Arch Linux
sudo dnf install ddcutil   # Fedora
```

### "No monitors detected"
```bash
# Test ddcutil directly
ddcutil detect

# Check I2C permissions
ls -la /dev/i2c-*
groups $USER  # Should include 'i2c'

# Reload I2C module
sudo modprobe -r i2c_dev && sudo modprobe i2c_dev
```

### "Permission denied"
```bash
# Add user to i2c group and reboot
sudo usermod -a -G i2c $USER
sudo reboot
```

### Monitor Not Responding
- ✅ Enable DDC/CI in monitor's OSD menu
- ✅ Switch monitor to "PC" mode (not "Console" mode)
- ✅ Try DisplayPort cable instead of HDMI/DVI
- ✅ Update monitor firmware if available

---

## 🚀 System Integration

### Autostart Service (systemd)
```bash
# Enable user service
systemctl --user enable monitor-control.service
systemctl --user start monitor-control.service

# Check status
systemctl --user status monitor-control.service
```

### Desktop Entry
A desktop entry is automatically created at:
`~/.local/share/applications/monitor-control.desktop`

This adds "Monitor Control" to your application menu.

---

## 🏗️ Project Architecture

```
src/monitor_control/
├── __init__.py          # Package initialization
├── ddc.py              # DDC/CI interface with ddcutil
├── cli.py              # Command-line interface
├── gui.py              # PyQt6 graphical interface
├── profiles.py         # Profile management and hotkeys
└── service.py          # Background service
```

### Core Components
- **DDCController**: Low-level ddcutil wrapper with error handling
- **ProfileManager**: Saves/loads monitor configurations and settings
- **HotkeyManager**: Global keyboard shortcut handling
- **MonitorControlService**: Background daemon for automation

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **🍴 Fork** the repository
2. **🌟 Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **💻 Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **📤 Push** to the branch (`git push origin feature/amazing-feature`)
5. **🔄 Open** a Pull Request

### Development Setup
```bash
git clone https://github.com/philling-dev/monitor-brightness-control.git
cd monitor-brightness-control
python -m venv venv
source venv/bin/activate
pip install -e .
pytest  # Run tests
```

---

## 💖 Support the Project

If this project was helpful to you, please consider supporting its development:

### ☕ Buy me a coffee
- **[coff.ee/philling](https://coff.ee/philling)**

### 🪙 Bitcoin
To donate, copy the address below:
```
1Lyy8GJignLbTUoTkR1HKSe8VTkzAvBMLm
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 💖 Acknowledgments

- 🙏 [ddcutil](https://github.com/rockowitz/ddcutil) - The foundation tool for DDC/CI communication
- 🐧 The Linux community for making advanced monitor control possible
- 🧪 Contributors and testers who help improve compatibility

---

## 🔮 Roadmap

- [ ] 🔌 Monitor input source switching
- [ ] 🕐 Time-based automatic profiles
- [ ] 🌅 Ambient light sensor integration
- [ ] 🌐 Web interface for remote control
- [ ] 🍎 Limited macOS support exploration
- [ ] 📱 Application-specific profiles
- [ ] 🔗 REST API for automation

---

<div align="center">

**Star ⭐ this repository if it helped you!**

[Report Bug](https://github.com/philling-dev/monitor-brightness-control/issues) • [Request Feature](https://github.com/philling-dev/monitor-brightness-control/issues) • [Documentation](https://github.com/philling-dev/monitor-brightness-control/wiki)

</div>
