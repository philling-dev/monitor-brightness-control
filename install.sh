#!/bin/bash

# Monitor Brightness Control - Installation Script
# This script installs dependencies and sets up the monitor control system

set -e

echo "🖥️  Monitor Brightness Control - Installation Script"
echo "=================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Run as regular user."
   exit 1
fi

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    print_error "Cannot detect Linux distribution"
    exit 1
fi

print_status "Detected distribution: $DISTRO"

# Install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."
    
    case $DISTRO in
        "ubuntu"|"debian")
            sudo apt update
            sudo apt install -y ddcutil i2c-tools python3-pip python3-venv libxcb-cursor0 python3-pyqt6
            ;;
        "fedora")
            sudo dnf install -y ddcutil python3-pip python3-virtualenv python3-qt6 xcb-util-cursor
            ;;
        "arch"|"manjaro")
            sudo pacman -S --noconfirm ddcutil python-pip python-pyqt6 xcb-util-cursor
            ;;
        "opensuse"|"opensuse-leap"|"opensuse-tumbleweed")
            sudo zypper install -y ddcutil python3-pip python3-qt6 libxcb-cursor0
            ;;
        *)
            print_warning "Distribution not explicitly supported. Trying generic installation..."
            print_status "Please install ddcutil and python3-pip manually if this fails"
            ;;
    esac
    
    print_success "System dependencies installed"
}

# Setup I2C permissions
setup_i2c() {
    print_status "Setting up I2C permissions..."
    
    # Add user to i2c group
    if getent group i2c > /dev/null 2>&1; then
        sudo usermod -a -G i2c $USER
        print_success "Added $USER to i2c group"
    else
        print_warning "i2c group not found, creating it..."
        sudo groupadd i2c
        sudo usermod -a -G i2c $USER
        print_success "Created i2c group and added $USER"
    fi
    
    # Load i2c-dev module
    if ! lsmod | grep -q i2c_dev; then
        sudo modprobe i2c-dev
        print_success "Loaded i2c-dev module"
    fi
    
    # Make i2c-dev load on boot
    if [ ! -f /etc/modules-load.d/i2c.conf ]; then
        echo 'i2c-dev' | sudo tee /etc/modules-load.d/i2c.conf > /dev/null
        print_success "Configured i2c-dev to load on boot"
    fi
    
    # Setup udev rules for i2c devices
    UDEV_RULE='/etc/udev/rules.d/45-ddcutil-i2c.rules'
    if [ ! -f "$UDEV_RULE" ]; then
        sudo tee "$UDEV_RULE" > /dev/null << 'EOF'
# Allow access to I2C devices for ddcutil
KERNEL=="i2c-[0-9]*", GROUP="i2c", MODE="0660"
EOF
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        print_success "Setup udev rules for I2C devices"
    fi
}

# Test ddcutil
test_ddcutil() {
    print_status "Testing ddcutil installation..."
    
    if command -v ddcutil &> /dev/null; then
        print_success "ddcutil is installed"
        
        # Test detection (might fail due to permissions before reboot)
        print_status "Testing monitor detection..."
        if ddcutil detect &> /dev/null; then
            MONITOR_COUNT=$(ddcutil detect | grep -c "Display" || true)
            if [ "$MONITOR_COUNT" -gt 0 ]; then
                print_success "Detected $MONITOR_COUNT monitor(s)"
            else
                print_warning "No monitors detected. This might be due to permissions or hardware."
            fi
        else
            print_warning "Monitor detection failed. You may need to reboot for permissions to take effect."
        fi
    else
        print_error "ddcutil installation failed"
        exit 1
    fi
}

# Install Python package
install_python_package() {
    print_status "Installing Python package..."
    
    # Check for PEP 668 externally-managed environment
    PEP668_ERROR=false
    
    # Try pipx first if available
    if command -v pipx &> /dev/null; then
        print_status "Using pipx for installation..."
        if [ -f "pyproject.toml" ] && [ -d "src/monitor_control" ]; then
            pipx install -e .
        else
            pipx install monitor-brightness-control
        fi
        print_success "Python package installed via pipx"
        return
    fi
    
    # Check if we're in the source directory
    if [ -f "pyproject.toml" ] && [ -d "src/monitor_control" ]; then
        print_status "Installing from source directory..."
        if ! pip install --user -e . 2>/tmp/pip_error.log; then
            if grep -q "externally-managed-environment" /tmp/pip_error.log; then
                PEP668_ERROR=true
            else
                print_error "Installation failed. Check /tmp/pip_error.log"
                exit 1
            fi
        fi
    else
        print_status "Installing from PyPI..."
        if ! pip install --user monitor-brightness-control 2>/tmp/pip_error.log; then
            if grep -q "externally-managed-environment" /tmp/pip_error.log; then
                PEP668_ERROR=true
            else
                print_error "Installation failed. Check /tmp/pip_error.log"
                exit 1
            fi
        fi
    fi
    
    # Handle PEP 668 error by creating a virtual environment
    if [ "$PEP668_ERROR" = true ]; then
        print_warning "PEP 668 externally-managed-environment detected"
        print_status "Creating virtual environment for installation..."
        
        VENV_DIR="$HOME/.local/share/monitor-control-venv"
        python3 -m venv "$VENV_DIR"
        
        # Install PyQt6 in virtual environment first
        print_status "Installing PyQt6 in virtual environment..."
        "$VENV_DIR/bin/pip" install PyQt6
        
        if [ -f "pyproject.toml" ] && [ -d "src/monitor_control" ]; then
            print_status "Installing from source in virtual environment..."
            "$VENV_DIR/bin/pip" install -e .
        else
            print_status "Installing from PyPI in virtual environment..."
            "$VENV_DIR/bin/pip" install monitor-brightness-control
        fi
        
        # Create wrapper scripts in ~/.local/bin
        mkdir -p "$HOME/.local/bin"
        
        cat > "$HOME/.local/bin/monitor-control" << EOF
#!/bin/bash
exec "$VENV_DIR/bin/python" -m monitor_control.cli "\$@"
EOF
        
        # Detect Python version in venv
        PYTHON_VER=$(ls "$VENV_DIR/lib/" | grep "python" | head -n1)
        
        cat > "$HOME/.local/bin/monitor-gui" << EOF
#!/bin/bash
VENV_DIR="$VENV_DIR"
PYTHON_VER="$PYTHON_VER"

# Set Qt environment variables with correct paths
export QT_QPA_PLATFORM_PLUGIN_PATH="\$VENV_DIR/lib/\$PYTHON_VER/site-packages/PyQt6/Qt6/plugins"
export LD_LIBRARY_PATH="\$VENV_DIR/lib/\$PYTHON_VER/site-packages/PyQt6/Qt6/lib:\$LD_LIBRARY_PATH"

# Fallback to system Qt if virtual env Qt fails
if [ ! -d "\$QT_QPA_PLATFORM_PLUGIN_PATH" ]; then
    unset QT_QPA_PLATFORM_PLUGIN_PATH
    unset LD_LIBRARY_PATH
fi

exec "\$VENV_DIR/bin/python" -m monitor_control.gui "\$@"
EOF
        
        chmod +x "$HOME/.local/bin/monitor-control"
        chmod +x "$HOME/.local/bin/monitor-gui"
        
        print_success "Installed in virtual environment with wrapper scripts"
    fi
    
    # Make sure ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        print_warning "~/.local/bin is not in your PATH"
        print_status "Adding to ~/.bashrc..."
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        print_success "Added ~/.local/bin to PATH in ~/.bashrc"
    fi
    
    print_success "Python package installed"
}

# Create desktop entry
create_desktop_entry() {
    print_status "Creating desktop entry..."
    
    DESKTOP_DIR="$HOME/.local/share/applications"
    mkdir -p "$DESKTOP_DIR"
    
    cat > "$DESKTOP_DIR/monitor-control.desktop" << EOF
[Desktop Entry]
Name=Monitor Control
Comment=Control external monitor brightness and contrast via DDC/CI
Exec=$HOME/.local/bin/monitor-gui
Icon=preferences-desktop-display
Type=Application
Categories=Settings;HardwareSettings;
Keywords=monitor;brightness;contrast;display;
EOF
    
    print_success "Desktop entry created"
}

# Setup systemd service (optional)
setup_systemd_service() {
    read -p "Do you want to enable the background service for hotkeys and profiles? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Setting up systemd user service..."
        
        SERVICE_DIR="$HOME/.config/systemd/user"
        mkdir -p "$SERVICE_DIR"
        
        # Determine the correct Python path
        PYTHON_PATH="$HOME/.local/bin/python"
        VENV_DIR="$HOME/.local/share/monitor-control-venv"
        if [ -d "$VENV_DIR" ]; then
            PYTHON_PATH="$VENV_DIR/bin/python"
        fi
        
        cat > "$SERVICE_DIR/monitor-control.service" << EOF
[Unit]
Description=Monitor Brightness Control Service
After=graphical-session.target

[Service]
Type=simple
ExecStart=$PYTHON_PATH -m monitor_control.service start
Restart=on-failure
Environment="DISPLAY=:0"

[Install]
WantedBy=default.target
EOF
        
        # Enable and start service
        systemctl --user daemon-reload
        systemctl --user enable monitor-control.service
        
        print_success "Systemd service created and enabled"
        print_status "The service will start automatically on next login"
        print_status "To start now: systemctl --user start monitor-control.service"
    fi
}

# Main installation process
main() {
    echo
    print_status "Starting installation process..."
    echo
    
    # Install system dependencies
    install_system_deps
    echo
    
    # Setup I2C permissions
    setup_i2c
    echo
    
    # Test ddcutil
    test_ddcutil
    echo
    
    # Install Python package
    install_python_package
    echo
    
    # Create desktop entry
    create_desktop_entry
    echo
    
    # Setup systemd service
    setup_systemd_service
    echo
    
    print_success "Installation completed!"
    echo
    print_status "Next steps:"
    echo "  1. Reboot your system or log out and back in for group changes to take effect"
    echo "  2. Test with: monitor-control detect"
    echo "  3. Launch GUI with: monitor-gui"
    echo "  4. Check README.md for usage instructions"
    echo
    print_warning "If monitors are not detected, check:"
    echo "  - DDC/CI is enabled in monitor settings"
    echo "  - Using DisplayPort or HDMI cable (not VGA/DVI)"
    echo "  - Monitor is in 'PC' mode, not 'Console' mode"
    echo
}

# Run main function
main "$@"