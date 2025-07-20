"""DDC/CI interface for monitor control."""

import subprocess
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class DDCFeature(Enum):
    """Common DDC/CI feature codes."""
    BRIGHTNESS = 0x10
    CONTRAST = 0x12
    INPUT_SOURCE = 0x60
    POWER_MODE = 0xD6


@dataclass
class Monitor:
    """Represents a detected monitor."""
    bus: int
    name: str
    manufacturer: str
    model: str
    serial: Optional[str] = None


class DDCError(Exception):
    """Exception raised for DDC/CI errors."""
    pass


class DDCController:
    """Main class for controlling monitors via DDC/CI."""
    
    def __init__(self):
        self._check_ddcutil()
    
    def _check_ddcutil(self) -> None:
        """Check if ddcutil is available."""
        try:
            result = subprocess.run(['ddcutil', '--version'], 
                                  capture_output=True, text=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise DDCError("ddcutil not found. Please install ddcutil package.")
    
    def detect_monitors(self) -> List[Monitor]:
        """Detect all available monitors."""
        try:
            result = subprocess.run(['ddcutil', 'detect'], 
                                  capture_output=True, text=True, check=True)
            return self._parse_detect_output(result.stdout)
        except subprocess.CalledProcessError as e:
            raise DDCError(f"Failed to detect monitors: {e.stderr}")
    
    def _parse_detect_output(self, output: str) -> List[Monitor]:
        """Parse ddcutil detect output."""
        monitors = []
        current_monitor = {}
        
        for line in output.split('\n'):
            line = line.strip()
            
            if line.startswith('Display'):
                if current_monitor:
                    monitors.append(self._create_monitor(current_monitor))
                    current_monitor = {}
            
            elif line.strip().startswith('I2C bus:'):
                # Extract bus number from I2C bus line
                bus_match = re.search(r'/dev/i2c-(\d+)', line)
                if bus_match:
                    current_monitor['bus'] = int(bus_match.group(1))
            
            elif line.startswith('Monitor:'):
                current_monitor['name'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('Mfg id:'):
                current_monitor['manufacturer'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('Model:'):
                current_monitor['model'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('Serial number:'):
                current_monitor['serial'] = line.split(':', 1)[1].strip()
        
        if current_monitor:
            monitors.append(self._create_monitor(current_monitor))
        
        return monitors
    
    def _create_monitor(self, data: Dict) -> Monitor:
        """Create Monitor object from parsed data."""
        # Smart fallback for monitor name
        name = data.get('name')
        if not name or name == 'Unknown':
            # Try to build name from manufacturer and model
            manufacturer = data.get('manufacturer', '')
            model = data.get('model', '')
            
            if manufacturer and model and manufacturer != 'Unknown' and model != 'Unknown':
                name = f"{manufacturer} {model}"
            elif model and model != 'Unknown':
                name = model
            elif manufacturer and manufacturer != 'Unknown':
                name = manufacturer
            else:
                name = f"Monitor on I2C-{data.get('bus', 0)}"
        
        return Monitor(
            bus=data.get('bus', 0),
            name=name,
            manufacturer=data.get('manufacturer', 'Unknown'),
            model=data.get('model', 'Unknown'),
            serial=data.get('serial')
        )
    
    def get_value(self, monitor: Monitor, feature: DDCFeature) -> Tuple[int, int]:
        """Get current and maximum value for a feature."""
        try:
            cmd = ['ddcutil', f'--bus={monitor.bus}', 'getvcp', f'{feature.value:02x}']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return self._parse_value_output(result.stdout)
        except subprocess.CalledProcessError as e:
            raise DDCError(f"Failed to get value for feature {feature.name}: {e.stderr}")
    
    def _parse_value_output(self, output: str) -> Tuple[int, int]:
        """Parse ddcutil getvcp output."""
        # Example: "VCP code 0x10 (Brightness): current value = 50, max value = 100"
        match = re.search(r'current value = (\d+), max value = (\d+)', output)
        if match:
            return int(match.group(1)), int(match.group(2))
        
        # Alternative format for some monitors
        match = re.search(r'current value =\s*(\d+)', output)
        if match:
            return int(match.group(1)), 100  # Assume max 100 if not specified
        
        raise DDCError(f"Could not parse value output: {output}")
    
    def set_value(self, monitor: Monitor, feature: DDCFeature, value: int) -> None:
        """Set value for a feature."""
        try:
            cmd = ['ddcutil', f'--bus={monitor.bus}', 'setvcp', f'{feature.value:02x}', str(value)]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise DDCError(f"Failed to set value for feature {feature.name}: {e.stderr}")
    
    def get_brightness(self, monitor: Monitor) -> Tuple[int, int]:
        """Get current and maximum brightness."""
        return self.get_value(monitor, DDCFeature.BRIGHTNESS)
    
    def set_brightness(self, monitor: Monitor, value: int) -> None:
        """Set brightness value."""
        self.set_value(monitor, DDCFeature.BRIGHTNESS, value)
    
    def get_contrast(self, monitor: Monitor) -> Tuple[int, int]:
        """Get current and maximum contrast."""
        return self.get_value(monitor, DDCFeature.CONTRAST)
    
    def set_contrast(self, monitor: Monitor, value: int) -> None:
        """Set contrast value."""
        self.set_value(monitor, DDCFeature.CONTRAST, value)
    
    def get_supported_features(self, monitor: Monitor) -> List[DDCFeature]:
        """Get list of supported features for a monitor."""
        try:
            cmd = ['ddcutil', f'--bus={monitor.bus}', 'capabilities']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return self._parse_capabilities(result.stdout)
        except subprocess.CalledProcessError:
            # Fallback to common features
            return [DDCFeature.BRIGHTNESS, DDCFeature.CONTRAST]
    
    def _parse_capabilities(self, output: str) -> List[DDCFeature]:
        """Parse capabilities output to find supported features."""
        supported = []
        
        # Look for VCP codes in capabilities string
        for feature in DDCFeature:
            if f'{feature.value:02x}' in output.lower() or f'{feature.value:02X}' in output:
                supported.append(feature)
        
        return supported