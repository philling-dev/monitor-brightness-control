"""Graphical user interface for monitor control."""

import sys
from typing import List, Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QSlider, QPushButton, QComboBox, QGroupBox, QGridLayout,
    QMessageBox, QSystemTrayIcon, QMenu, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QAction

from .ddc import DDCController, DDCError, Monitor, DDCFeature


class MonitorDetectionWorker(QThread):
    """Worker thread for monitor detection."""
    monitors_detected = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def run(self):
        try:
            controller = DDCController()
            monitors = controller.detect_monitors()
            self.monitors_detected.emit(monitors)
        except DDCError as e:
            self.error_occurred.emit(str(e))


class MonitorControlWidget(QWidget):
    """Widget for controlling a single monitor."""
    
    def __init__(self, monitor: Monitor, controller: DDCController):
        super().__init__()
        self.monitor = monitor
        self.controller = controller
        self.updating = False
        self.init_ui()
        self.load_current_values()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Monitor info
        info_label = QLabel(f"{self.monitor.name} (Bus: {self.monitor.bus})")
        info_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(info_label)
        
        # Brightness control
        brightness_group = QGroupBox("Brightness")
        brightness_layout = QGridLayout()
        
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(50)
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)
        
        self.brightness_label = QLabel("50%")
        self.brightness_label.setMinimumWidth(40)
        
        brightness_layout.addWidget(QLabel("Brightness:"), 0, 0)
        brightness_layout.addWidget(self.brightness_slider, 0, 1)
        brightness_layout.addWidget(self.brightness_label, 0, 2)
        
        brightness_group.setLayout(brightness_layout)
        layout.addWidget(brightness_group)
        
        # Contrast control
        contrast_group = QGroupBox("Contrast")
        contrast_layout = QGridLayout()
        
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(0, 100)
        self.contrast_slider.setValue(50)
        self.contrast_slider.valueChanged.connect(self.on_contrast_changed)
        
        self.contrast_label = QLabel("50%")
        self.contrast_label.setMinimumWidth(40)
        
        contrast_layout.addWidget(QLabel("Contrast:"), 0, 0)
        contrast_layout.addWidget(self.contrast_slider, 0, 1)
        contrast_layout.addWidget(self.contrast_label, 0, 2)
        
        contrast_group.setLayout(contrast_layout)
        layout.addWidget(contrast_group)
        
        # Quick preset buttons
        presets_group = QGroupBox("Quick Presets")
        presets_layout = QHBoxLayout()
        
        day_btn = QPushButton("Day (80%)")
        day_btn.clicked.connect(lambda: self.set_preset(80, 75))
        
        night_btn = QPushButton("Night (20%)")
        night_btn.clicked.connect(lambda: self.set_preset(20, 60))
        
        gaming_btn = QPushButton("Gaming (100%)")
        gaming_btn.clicked.connect(lambda: self.set_preset(100, 90))
        
        presets_layout.addWidget(day_btn)
        presets_layout.addWidget(night_btn)
        presets_layout.addWidget(gaming_btn)
        
        presets_group.setLayout(presets_layout)
        layout.addWidget(presets_group)
        
        self.setLayout(layout)
    
    def load_current_values(self):
        """Load current brightness and contrast values from monitor."""
        self.updating = True
        
        try:
            # Get brightness
            current, maximum = self.controller.get_brightness(self.monitor)
            percentage = round((current / maximum) * 100) if maximum > 0 else 50
            self.brightness_slider.setValue(percentage)
            self.brightness_label.setText(f"{percentage}%")
        except DDCError:
            self.brightness_slider.setValue(50)
            self.brightness_label.setText("50%")
        
        try:
            # Get contrast
            current, maximum = self.controller.get_contrast(self.monitor)
            percentage = round((current / maximum) * 100) if maximum > 0 else 50
            self.contrast_slider.setValue(percentage)
            self.contrast_label.setText(f"{percentage}%")
        except DDCError:
            self.contrast_slider.setValue(50)
            self.contrast_label.setText("50%")
        
        self.updating = False
    
    def on_brightness_changed(self, value: int):
        """Handle brightness slider change."""
        if self.updating:
            return
        
        self.brightness_label.setText(f"{value}%")
        
        try:
            self.controller.set_brightness(self.monitor, value)
        except DDCError as e:
            QMessageBox.warning(self, "Error", f"Failed to set brightness: {e}")
    
    def on_contrast_changed(self, value: int):
        """Handle contrast slider change."""
        if self.updating:
            return
        
        self.contrast_label.setText(f"{value}%")
        
        try:
            self.controller.set_contrast(self.monitor, value)
        except DDCError as e:
            QMessageBox.warning(self, "Error", f"Failed to set contrast: {e}")
    
    def set_preset(self, brightness: int, contrast: int):
        """Set brightness and contrast to preset values."""
        self.brightness_slider.setValue(brightness)
        self.contrast_slider.setValue(contrast)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.controller = DDCController()
        self.monitors: List[Monitor] = []
        self.monitor_widgets: List[MonitorControlWidget] = []
        self.init_ui()
        self.create_system_tray()
        self.detect_monitors()
    
    def init_ui(self):
        self.setWindowTitle("Monitor Brightness Control")
        self.setFixedSize(400, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Monitor Brightness Control")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Monitors")
        refresh_btn.clicked.connect(self.detect_monitors)
        layout.addWidget(refresh_btn)
        
        # Progress bar for loading
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Monitors container
        self.monitors_widget = QWidget()
        self.monitors_layout = QVBoxLayout()
        self.monitors_widget.setLayout(self.monitors_layout)
        layout.addWidget(self.monitors_widget)
        
        # Status label
        self.status_label = QLabel("Detecting monitors...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        central_widget.setLayout(layout)
    
    def create_system_tray(self):
        """Create system tray icon with menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
    
    def on_tray_activated(self, reason):
        """Handle system tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
    
    def detect_monitors(self):
        """Start monitor detection in background thread."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_label.setText("Detecting monitors...")
        
        # Clear existing widgets
        for widget in self.monitor_widgets:
            widget.setParent(None)
        self.monitor_widgets.clear()
        
        # Start detection worker
        self.detection_worker = MonitorDetectionWorker()
        self.detection_worker.monitors_detected.connect(self.on_monitors_detected)
        self.detection_worker.error_occurred.connect(self.on_detection_error)
        self.detection_worker.start()
    
    def on_monitors_detected(self, monitors: List[Monitor]):
        """Handle successful monitor detection."""
        self.progress_bar.setVisible(False)
        self.monitors = monitors
        
        if not monitors:
            self.status_label.setText("No monitors detected. Make sure ddcutil is installed and you have proper permissions.")
            return
        
        self.status_label.setText(f"Found {len(monitors)} monitor(s)")
        
        # Create control widgets for each monitor
        for monitor in monitors:
            widget = MonitorControlWidget(monitor, self.controller)
            self.monitor_widgets.append(widget)
            self.monitors_layout.addWidget(widget)
    
    def on_detection_error(self, error: str):
        """Handle monitor detection error."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error}")
        QMessageBox.critical(self, "Error", f"Failed to detect monitors:\n{error}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        if QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            if hasattr(self, 'tray_icon'):
                self.tray_icon.showMessage(
                    "Monitor Control",
                    "Application minimized to system tray",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )


def main():
    """Main entry point for GUI application."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Check for ddcutil
    try:
        controller = DDCController()
    except DDCError as e:
        QMessageBox.critical(None, "Error", str(e))
        sys.exit(1)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()