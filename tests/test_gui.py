"""Tests for GUI functionality."""

import pytest


def test_gui_imports():
    """Test that GUI module imports successfully."""
    try:
        from monitor_control.gui import main
        assert main is not None
    except ImportError as e:
        pytest.fail(f"GUI import failed: {e}")


def test_gui_module_structure():
    """Test GUI module has required components."""
    from monitor_control import gui
    
    # Check that main functions exist
    assert hasattr(gui, 'main')
    assert hasattr(gui, 'MainWindow')
    assert hasattr(gui, 'MonitorControlWidget')


if __name__ == '__main__':
    pytest.main([__file__])