"""Tests for profile management functionality."""

import pytest
import tempfile
import json
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

from monitor_control.profiles import ProfileManager, Profile, MonitorSettings, HotkeyManager
from monitor_control.ddc import Monitor


class TestMonitorSettings:
    """Test MonitorSettings dataclass."""
    
    def test_monitor_settings_creation(self):
        """Test MonitorSettings creation."""
        settings = MonitorSettings(
            bus=4,
            brightness=80,
            contrast=75,
            name="Test Monitor"
        )
        
        assert settings.bus == 4
        assert settings.brightness == 80
        assert settings.contrast == 75
        assert settings.name == "Test Monitor"


class TestProfile:
    """Test Profile dataclass."""
    
    def test_profile_creation(self):
        """Test Profile creation."""
        monitor_settings = [
            MonitorSettings(bus=4, brightness=80, contrast=75, name="Monitor 1"),
            MonitorSettings(bus=6, brightness=60, contrast=70, name="Monitor 2")
        ]
        
        profile = Profile(
            name="test_profile",
            monitors=monitor_settings,
            description="Test profile description"
        )
        
        assert profile.name == "test_profile"
        assert len(profile.monitors) == 2
        assert profile.description == "Test profile description"


class TestProfileManager:
    """Test ProfileManager functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        
    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('monitor_control.profiles.DDCController')
    def test_profile_manager_init(self, mock_controller):
        """Test ProfileManager initialization."""
        mock_controller.return_value = MagicMock()
        
        manager = ProfileManager(str(self.config_dir))
        
        assert manager.config_dir == self.config_dir
        assert self.config_dir.exists()
        assert manager.profiles_file == self.config_dir / "profiles.json"
        assert manager.settings_file == self.config_dir / "settings.json"
    
    @patch('monitor_control.profiles.DDCController')
    def test_save_and_load_profiles(self, mock_controller):
        """Test saving and loading profiles."""
        mock_controller.return_value = MagicMock()
        
        manager = ProfileManager(str(self.config_dir))
        
        # Create test profile
        monitor_settings = [MonitorSettings(bus=4, brightness=80, contrast=75, name="Test")]
        test_profile = Profile(name="test", monitors=monitor_settings, description="Test profile")
        
        manager.profiles["test"] = test_profile
        manager.save_profiles()
        
        # Verify file was created
        assert manager.profiles_file.exists()
        
        # Load profiles into new manager
        manager2 = ProfileManager(str(self.config_dir))
        
        assert "test" in manager2.profiles
        assert manager2.profiles["test"].name == "test"
        assert manager2.profiles["test"].description == "Test profile"
        assert len(manager2.profiles["test"].monitors) == 1
        assert manager2.profiles["test"].monitors[0].bus == 4
    
    @patch('monitor_control.profiles.DDCController')
    def test_save_and_load_settings(self, mock_controller):
        """Test saving and loading settings."""
        mock_controller.return_value = MagicMock()
        
        manager = ProfileManager(str(self.config_dir))
        
        # Modify settings
        manager.settings["test_setting"] = "test_value"
        manager.save_settings()
        
        # Verify file was created
        assert manager.settings_file.exists()
        
        # Load settings into new manager
        manager2 = ProfileManager(str(self.config_dir))
        
        assert manager2.settings["test_setting"] == "test_value"
    
    @patch('monitor_control.profiles.DDCController')
    def test_create_default_profiles(self, mock_controller):
        """Test default profile creation."""
        # Mock controller and monitors
        mock_controller_instance = MagicMock()
        mock_controller.return_value = mock_controller_instance
        
        test_monitors = [
            Monitor(bus=4, name="Monitor 1", manufacturer="TEST", model="MODEL1"),
            Monitor(bus=6, name="Monitor 2", manufacturer="TEST", model="MODEL2")
        ]
        mock_controller_instance.detect_monitors.return_value = test_monitors
        
        manager = ProfileManager(str(self.config_dir))
        
        # Should have created default profiles
        assert "day" in manager.profiles
        assert "night" in manager.profiles
        assert "gaming" in manager.profiles
        
        # Check day profile
        day_profile = manager.profiles["day"]
        assert len(day_profile.monitors) == 2
        assert day_profile.monitors[0].brightness == 80
        assert day_profile.monitors[0].contrast == 75
        
        # Check night profile
        night_profile = manager.profiles["night"]
        assert night_profile.monitors[0].brightness == 20
        assert night_profile.monitors[0].contrast == 60
        
        # Check gaming profile
        gaming_profile = manager.profiles["gaming"]
        assert gaming_profile.monitors[0].brightness == 100
        assert gaming_profile.monitors[0].contrast == 90
    
    @patch('monitor_control.profiles.DDCController')
    def test_delete_profile(self, mock_controller):
        """Test profile deletion."""
        mock_controller.return_value = MagicMock()
        
        manager = ProfileManager(str(self.config_dir))
        
        # Add test profile
        monitor_settings = [MonitorSettings(bus=4, brightness=80, contrast=75, name="Test")]
        test_profile = Profile(name="test", monitors=monitor_settings)
        manager.profiles["test"] = test_profile
        
        # Delete profile
        result = manager.delete_profile("test")
        assert result is True
        assert "test" not in manager.profiles
        
        # Try to delete non-existent profile
        result = manager.delete_profile("non_existent")
        assert result is False
    
    @patch('monitor_control.profiles.DDCController')
    def test_list_profiles(self, mock_controller):
        """Test listing profiles."""
        mock_controller.return_value = MagicMock()
        
        manager = ProfileManager(str(self.config_dir))
        
        # Should have default profiles
        profiles = manager.list_profiles()
        assert isinstance(profiles, list)
        assert "day" in profiles
        assert "night" in profiles
        assert "gaming" in profiles


class TestHotkeyManager:
    """Test HotkeyManager functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
    
    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('monitor_control.profiles.DDCController')
    @patch('monitor_control.profiles.keyboard.Listener')
    def test_hotkey_manager_init(self, mock_listener, mock_controller):
        """Test HotkeyManager initialization."""
        mock_controller.return_value = MagicMock()
        
        profile_manager = ProfileManager(str(self.config_dir))
        hotkey_manager = HotkeyManager(profile_manager)
        
        assert hotkey_manager.profile_manager == profile_manager
        assert hotkey_manager.listener is None
        assert not hotkey_manager.enabled
    
    @patch('monitor_control.profiles.DDCController')
    def test_load_hotkeys(self, mock_controller):
        """Test hotkey configuration loading."""
        mock_controller.return_value = MagicMock()
        
        profile_manager = ProfileManager(str(self.config_dir))
        hotkey_manager = HotkeyManager(profile_manager)
        
        # Should have loaded default hotkeys
        assert len(hotkey_manager.hotkey_combinations) > 0
        
        # Test that hotkey combinations are properly converted
        actions = []
        for keys, action in hotkey_manager.hotkey_combinations.items():
            actions.append(action)
        
        assert "day_profile" in actions
        assert "night_profile" in actions
        assert "gaming_profile" in actions


if __name__ == '__main__':
    pytest.main([__file__])