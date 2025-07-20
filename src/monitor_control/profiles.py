"""Profile management and keyboard shortcuts for monitor control."""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from pynput import keyboard
from pynput.keyboard import Key, KeyCode
import threading
import time

from .ddc import DDCController, Monitor, DDCError


@dataclass
class MonitorSettings:
    """Settings for a single monitor."""
    bus: int
    brightness: int
    contrast: int
    name: str = ""


@dataclass
class Profile:
    """A profile containing settings for multiple monitors."""
    name: str
    monitors: List[MonitorSettings]
    description: str = ""


class ProfileManager:
    """Manages monitor profiles and settings."""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".config", "monitor-control")
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_file = self.config_dir / "profiles.json"
        self.settings_file = self.config_dir / "settings.json"
        
        self.controller = DDCController()
        self.profiles: Dict[str, Profile] = {}
        self.settings: Dict[str, Any] = {}
        
        self.load_profiles()
        self.load_settings()
    
    def load_profiles(self):
        """Load profiles from JSON file."""
        if not self.profiles_file.exists():
            self.create_default_profiles()
            return
        
        try:
            with open(self.profiles_file, 'r') as f:
                data = json.load(f)
            
            self.profiles = {}
            for name, profile_data in data.items():
                monitors = [MonitorSettings(**m) for m in profile_data['monitors']]
                self.profiles[name] = Profile(
                    name=profile_data['name'],
                    monitors=monitors,
                    description=profile_data.get('description', '')
                )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading profiles: {e}")
            self.create_default_profiles()
    
    def save_profiles(self):
        """Save profiles to JSON file."""
        data = {}
        for name, profile in self.profiles.items():
            data[name] = {
                'name': profile.name,
                'description': profile.description,
                'monitors': [asdict(m) for m in profile.monitors]
            }
        
        with open(self.profiles_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_settings(self):
        """Load application settings."""
        if not self.settings_file.exists():
            self.settings = {
                'auto_apply_on_startup': True,
                'default_profile': 'day',
                'hotkeys_enabled': True,
                'hotkeys': {
                    'day_profile': ['ctrl', 'alt', '1'],
                    'night_profile': ['ctrl', 'alt', '2'],
                    'gaming_profile': ['ctrl', 'alt', '3'],
                    'brightness_up': ['ctrl', 'alt', 'up'],
                    'brightness_down': ['ctrl', 'alt', 'down']
                }
            }
            self.save_settings()
            return
        
        try:
            with open(self.settings_file, 'r') as f:
                self.settings = json.load(f)
        except json.JSONDecodeError:
            self.settings = {}
    
    def save_settings(self):
        """Save application settings."""
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def create_default_profiles(self):
        """Create default profiles."""
        try:
            monitors = self.controller.detect_monitors()
            
            # Day profile - bright settings
            day_monitors = []
            for monitor in monitors:
                day_monitors.append(MonitorSettings(
                    bus=monitor.bus,
                    brightness=80,
                    contrast=75,
                    name=monitor.name
                ))
            
            # Night profile - dim settings
            night_monitors = []
            for monitor in monitors:
                night_monitors.append(MonitorSettings(
                    bus=monitor.bus,
                    brightness=20,
                    contrast=60,
                    name=monitor.name
                ))
            
            # Gaming profile - maximum settings
            gaming_monitors = []
            for monitor in monitors:
                gaming_monitors.append(MonitorSettings(
                    bus=monitor.bus,
                    brightness=100,
                    contrast=90,
                    name=monitor.name
                ))
            
            self.profiles = {
                'day': Profile(
                    name='day',
                    description='Bright settings for daytime use',
                    monitors=day_monitors
                ),
                'night': Profile(
                    name='night',
                    description='Dim settings for nighttime use',
                    monitors=night_monitors
                ),
                'gaming': Profile(
                    name='gaming',
                    description='Maximum brightness and contrast for gaming',
                    monitors=gaming_monitors
                )
            }
            
            self.save_profiles()
        except DDCError:
            # Create empty profiles if no monitors detected
            self.profiles = {}
    
    def create_profile_from_current(self, name: str, description: str = "") -> bool:
        """Create a new profile from current monitor settings."""
        try:
            monitors = self.controller.detect_monitors()
            profile_monitors = []
            
            for monitor in monitors:
                try:
                    brightness_current, brightness_max = self.controller.get_brightness(monitor)
                    contrast_current, contrast_max = self.controller.get_contrast(monitor)
                    
                    brightness_pct = round((brightness_current / brightness_max) * 100) if brightness_max > 0 else 50
                    contrast_pct = round((contrast_current / contrast_max) * 100) if contrast_max > 0 else 50
                    
                    profile_monitors.append(MonitorSettings(
                        bus=monitor.bus,
                        brightness=brightness_pct,
                        contrast=contrast_pct,
                        name=monitor.name
                    ))
                except DDCError:
                    continue
            
            if profile_monitors:
                self.profiles[name] = Profile(
                    name=name,
                    description=description,
                    monitors=profile_monitors
                )
                self.save_profiles()
                return True
            
        except DDCError:
            pass
        
        return False
    
    def apply_profile(self, profile_name: str) -> bool:
        """Apply a profile to all monitors."""
        if profile_name not in self.profiles:
            return False
        
        profile = self.profiles[profile_name]
        success = True
        
        try:
            current_monitors = self.controller.detect_monitors()
            monitor_map = {m.bus: m for m in current_monitors}
            
            for monitor_settings in profile.monitors:
                if monitor_settings.bus not in monitor_map:
                    continue
                
                monitor = monitor_map[monitor_settings.bus]
                
                try:
                    self.controller.set_brightness(monitor, monitor_settings.brightness)
                    self.controller.set_contrast(monitor, monitor_settings.contrast)
                except DDCError:
                    success = False
                    continue
            
        except DDCError:
            success = False
        
        return success
    
    def delete_profile(self, profile_name: str) -> bool:
        """Delete a profile."""
        if profile_name in self.profiles:
            del self.profiles[profile_name]
            self.save_profiles()
            return True
        return False
    
    def list_profiles(self) -> List[str]:
        """Get list of profile names."""
        return list(self.profiles.keys())
    
    def get_profile(self, name: str) -> Optional[Profile]:
        """Get a profile by name."""
        return self.profiles.get(name)


class HotkeyManager:
    """Manages global keyboard shortcuts for monitor control."""
    
    def __init__(self, profile_manager: ProfileManager):
        self.profile_manager = profile_manager
        self.listener: Optional[keyboard.Listener] = None
        self.pressed_keys = set()
        self.hotkey_combinations = {}
        self.enabled = False
        self.load_hotkeys()
    
    def load_hotkeys(self):
        """Load hotkey configurations from settings."""
        hotkeys = self.profile_manager.settings.get('hotkeys', {})
        
        # Convert string key combinations to sets of keys
        for action, key_combo in hotkeys.items():
            if isinstance(key_combo, list):
                keys = set()
                for key_str in key_combo:
                    if key_str.lower() == 'ctrl':
                        keys.add(Key.ctrl_l)
                    elif key_str.lower() == 'alt':
                        keys.add(Key.alt_l)
                    elif key_str.lower() == 'shift':
                        keys.add(Key.shift_l)
                    elif key_str.lower() == 'up':
                        keys.add(Key.up)
                    elif key_str.lower() == 'down':
                        keys.add(Key.down)
                    elif len(key_str) == 1:
                        keys.add(KeyCode.from_char(key_str.lower()))
                
                self.hotkey_combinations[frozenset(keys)] = action
    
    def start(self):
        """Start listening for hotkeys."""
        if self.listener is not None:
            return
        
        self.enabled = self.profile_manager.settings.get('hotkeys_enabled', True)
        if not self.enabled:
            return
        
        self.listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.listener.start()
    
    def stop(self):
        """Stop listening for hotkeys."""
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
        self.pressed_keys.clear()
    
    def on_key_press(self, key):
        """Handle key press events."""
        self.pressed_keys.add(key)
        
        # Check for hotkey combinations
        for key_combo, action in self.hotkey_combinations.items():
            if key_combo.issubset(self.pressed_keys):
                self.execute_action(action)
                # Small delay to prevent multiple triggers
                time.sleep(0.1)
    
    def on_key_release(self, key):
        """Handle key release events."""
        self.pressed_keys.discard(key)
    
    def execute_action(self, action: str):
        """Execute a hotkey action."""
        if action == 'day_profile':
            self.profile_manager.apply_profile('day')
        elif action == 'night_profile':
            self.profile_manager.apply_profile('night')
        elif action == 'gaming_profile':
            self.profile_manager.apply_profile('gaming')
        elif action == 'brightness_up':
            self.adjust_all_brightness(10)
        elif action == 'brightness_down':
            self.adjust_all_brightness(-10)
    
    def adjust_all_brightness(self, delta: int):
        """Adjust brightness of all monitors by delta percentage."""
        try:
            monitors = self.profile_manager.controller.detect_monitors()
            
            for monitor in monitors:
                try:
                    current, maximum = self.profile_manager.controller.get_brightness(monitor)
                    current_pct = round((current / maximum) * 100) if maximum > 0 else 50
                    new_pct = max(0, min(100, current_pct + delta))
                    self.profile_manager.controller.set_brightness(monitor, new_pct)
                except DDCError:
                    continue
        except DDCError:
            pass


def start_background_service():
    """Start the background service for profiles and hotkeys."""
    profile_manager = ProfileManager()
    hotkey_manager = HotkeyManager(profile_manager)
    
    # Apply default profile on startup if enabled
    if profile_manager.settings.get('auto_apply_on_startup', True):
        default_profile = profile_manager.settings.get('default_profile', 'day')
        if default_profile in profile_manager.profiles:
            profile_manager.apply_profile(default_profile)
    
    # Start hotkey listener
    hotkey_manager.start()
    
    try:
        # Keep the service running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        hotkey_manager.stop()


if __name__ == '__main__':
    start_background_service()