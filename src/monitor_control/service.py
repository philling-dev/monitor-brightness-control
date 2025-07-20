"""Background service for monitor control."""

import sys
import signal
import time
import argparse
from pathlib import Path

from .profiles import ProfileManager, HotkeyManager
from .ddc import DDCError


class MonitorControlService:
    """Background service for monitor control with hotkeys and profiles."""
    
    def __init__(self):
        self.profile_manager = ProfileManager()
        self.hotkey_manager = HotkeyManager(self.profile_manager)
        self.running = False
    
    def start(self):
        """Start the service."""
        print("Starting Monitor Control Service...")
        
        # Apply default profile on startup if enabled
        if self.profile_manager.settings.get('auto_apply_on_startup', True):
            default_profile = self.profile_manager.settings.get('default_profile', 'day')
            if default_profile in self.profile_manager.profiles:
                print(f"Applying default profile: {default_profile}")
                if self.profile_manager.apply_profile(default_profile):
                    print("Default profile applied successfully")
                else:
                    print("Failed to apply default profile")
        
        # Start hotkey listener
        if self.profile_manager.settings.get('hotkeys_enabled', True):
            print("Starting hotkey listener...")
            self.hotkey_manager.start()
            print("Hotkeys enabled:")
            hotkeys = self.profile_manager.settings.get('hotkeys', {})
            for action, keys in hotkeys.items():
                print(f"  {action}: {' + '.join(keys)}")
        else:
            print("Hotkeys disabled in settings")
        
        self.running = True
        print("Monitor Control Service is running")
        print("Press Ctrl+C to stop")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Keep the service running
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Stop the service."""
        print("\nStopping Monitor Control Service...")
        self.running = False
        self.hotkey_manager.stop()
        print("Service stopped")
    
    def signal_handler(self, signum, frame):
        """Handle system signals."""
        print(f"\nReceived signal {signum}")
        self.stop()
        sys.exit(0)
    
    def status(self):
        """Show service status."""
        print("Monitor Control Service Status")
        print("=" * 30)
        
        # Check if ddcutil is available
        try:
            monitors = self.profile_manager.controller.detect_monitors()
            print(f"Monitors detected: {len(monitors)}")
            for monitor in monitors:
                print(f"  - {monitor.name} (Bus: {monitor.bus})")
        except DDCError as e:
            print(f"Error detecting monitors: {e}")
        
        # Show profiles
        profiles = self.profile_manager.list_profiles()
        print(f"\nProfiles available: {len(profiles)}")
        for profile_name in profiles:
            profile = self.profile_manager.get_profile(profile_name)
            print(f"  - {profile_name}: {profile.description}")
        
        # Show settings
        settings = self.profile_manager.settings
        print(f"\nSettings:")
        print(f"  Auto-apply on startup: {settings.get('auto_apply_on_startup', False)}")
        print(f"  Default profile: {settings.get('default_profile', 'None')}")
        print(f"  Hotkeys enabled: {settings.get('hotkeys_enabled', False)}")
        
        # Show config location
        print(f"\nConfig directory: {self.profile_manager.config_dir}")


def main():
    """Main entry point for the service command."""
    parser = argparse.ArgumentParser(description="Monitor Control Background Service")
    parser.add_argument('action', choices=['start', 'status'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    service = MonitorControlService()
    
    if args.action == 'start':
        service.start()
    elif args.action == 'status':
        service.status()


if __name__ == '__main__':
    main()