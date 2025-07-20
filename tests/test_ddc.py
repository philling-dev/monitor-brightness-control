"""Tests for DDC/CI functionality."""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

from monitor_control.ddc import DDCController, DDCError, Monitor, DDCFeature


class TestDDCController:
    """Test DDC controller functionality."""
    
    @patch('subprocess.run')
    def test_check_ddcutil_success(self, mock_run):
        """Test ddcutil check when available."""
        mock_run.return_value = MagicMock(returncode=0)
        controller = DDCController()
        assert controller is not None
    
    @patch('subprocess.run')
    def test_check_ddcutil_not_found(self, mock_run):
        """Test ddcutil check when not available."""
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(DDCError, match="ddcutil not found"):
            DDCController()
    
    @patch('subprocess.run')
    def test_detect_monitors_success(self, mock_run):
        """Test successful monitor detection."""
        # Mock ddcutil check
        mock_run.return_value = MagicMock(returncode=0)
        controller = DDCController()
        
        # Mock detect output
        detect_output = """
Display 1
   I2C bus:  /dev/i2c-4
   Monitor:  LG HDR 4K
   EDID synopsis:
      Mfg id:               LGD
      Model:                LG HDR 4K
      Product code:         1234
      Serial number:        ABC123

Display 2
   I2C bus:  /dev/i2c-6
   Monitor:  DELL U2720Q
   EDID synopsis:
      Mfg id:               DEL
      Model:                U2720Q
      Product code:         5678
      Serial number:        XYZ789
"""
        mock_run.return_value.stdout = detect_output
        mock_run.return_value.returncode = 0
        
        monitors = controller.detect_monitors()
        
        assert len(monitors) == 2
        assert monitors[0].bus == 4
        assert monitors[0].name == "LG HDR 4K"
        assert monitors[0].manufacturer == "LGD"
        assert monitors[0].serial == "ABC123"
        
        assert monitors[1].bus == 6
        assert monitors[1].name == "DELL U2720Q"
        assert monitors[1].manufacturer == "DEL"
        assert monitors[1].serial == "XYZ789"
    
    @patch('subprocess.run')
    def test_detect_monitors_empty(self, mock_run):
        """Test monitor detection with no monitors."""
        # Mock ddcutil check
        mock_run.return_value = MagicMock(returncode=0)
        controller = DDCController()
        
        # Mock empty detect output
        mock_run.return_value.stdout = "No displays detected"
        mock_run.return_value.returncode = 0
        
        monitors = controller.detect_monitors()
        assert len(monitors) == 0
    
    @patch('subprocess.run')
    def test_get_brightness_success(self, mock_run):
        """Test getting brightness value."""
        # Mock ddcutil check
        mock_run.return_value = MagicMock(returncode=0)
        controller = DDCController()
        
        # Mock brightness output
        brightness_output = "VCP code 0x10 (Brightness): current value = 80, max value = 100"
        mock_run.return_value.stdout = brightness_output
        mock_run.return_value.returncode = 0
        
        monitor = Monitor(bus=4, name="Test", manufacturer="TEST", model="MODEL")
        current, maximum = controller.get_brightness(monitor)
        
        assert current == 80
        assert maximum == 100
    
    @patch('subprocess.run')
    def test_set_brightness_success(self, mock_run):
        """Test setting brightness value."""
        # Mock ddcutil check
        mock_run.return_value = MagicMock(returncode=0)
        controller = DDCController()
        
        # Mock successful set
        mock_run.return_value.returncode = 0
        
        monitor = Monitor(bus=4, name="Test", manufacturer="TEST", model="MODEL")
        controller.set_brightness(monitor, 75)
        
        # Verify correct command was called
        mock_run.assert_called_with(
            ['ddcutil', '--bus=4', 'setvcp', '10', '75'],
            capture_output=True, text=True, check=True
        )
    
    @patch('subprocess.run')
    def test_parse_value_output_formats(self, mock_run):
        """Test parsing different ddcutil output formats."""
        # Mock ddcutil check
        mock_run.return_value = MagicMock(returncode=0)
        controller = DDCController()
        
        # Test standard format
        output1 = "VCP code 0x10 (Brightness): current value = 50, max value = 100"
        current, maximum = controller._parse_value_output(output1)
        assert current == 50
        assert maximum == 100
        
        # Test alternative format
        output2 = "VCP code 0x10 (Brightness): current value =    75"
        current, maximum = controller._parse_value_output(output2)
        assert current == 75
        assert maximum == 100  # Default when max not specified


class TestMonitor:
    """Test Monitor dataclass."""
    
    def test_monitor_creation(self):
        """Test monitor object creation."""
        monitor = Monitor(
            bus=4,
            name="Test Monitor",
            manufacturer="TEST",
            model="MODEL123",
            serial="ABC123"
        )
        
        assert monitor.bus == 4
        assert monitor.name == "Test Monitor"
        assert monitor.manufacturer == "TEST"
        assert monitor.model == "MODEL123"
        assert monitor.serial == "ABC123"
    
    def test_monitor_without_serial(self):
        """Test monitor creation without serial number."""
        monitor = Monitor(
            bus=5,
            name="Test Monitor 2",
            manufacturer="TEST2",
            model="MODEL456"
        )
        
        assert monitor.serial is None


class TestDDCFeature:
    """Test DDC feature enum."""
    
    def test_feature_values(self):
        """Test DDC feature code values."""
        assert DDCFeature.BRIGHTNESS.value == 0x10
        assert DDCFeature.CONTRAST.value == 0x12
        assert DDCFeature.INPUT_SOURCE.value == 0x60
        assert DDCFeature.POWER_MODE.value == 0xD6


if __name__ == '__main__':
    pytest.main([__file__])