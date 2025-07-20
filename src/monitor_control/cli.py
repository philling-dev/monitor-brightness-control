"""Command-line interface for monitor control."""

import click
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .ddc import DDCController, DDCError, Monitor, DDCFeature


console = Console()


@click.group()
@click.version_option(package_name='monitor-brightness-control')
def main():
    """Control external monitor brightness, contrast and input via DDC/CI."""
    pass


@main.command()
def detect():
    """Detect available monitors."""
    controller = DDCController()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Detecting monitors...", total=None)
        
        try:
            monitors = controller.detect_monitors()
        except DDCError as e:
            console.print(f"[red]Error: {e}[/red]")
            return
        
        progress.remove_task(task)
    
    if not monitors:
        console.print("[yellow]No monitors detected.[/yellow]")
        return
    
    table = Table(title="Detected Monitors")
    table.add_column("Bus", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Manufacturer", style="green")
    table.add_column("Model", style="blue")
    table.add_column("Serial", style="dim")
    
    for monitor in monitors:
        table.add_row(
            str(monitor.bus),
            monitor.name,
            monitor.manufacturer,
            monitor.model,
            monitor.serial or "N/A"
        )
    
    console.print(table)


@main.command()
@click.option('--bus', type=int, help='Monitor bus number (use detect command to find)')
@click.option('--value', type=int, help='Brightness value to set (0-100)')
def brightness(bus: Optional[int], value: Optional[int]):
    """Get or set monitor brightness."""
    controller = DDCController()
    
    try:
        monitors = controller.detect_monitors()
        if not monitors:
            console.print("[red]No monitors detected.[/red]")
            return
        
        # Select monitor
        if bus is not None:
            monitor = next((m for m in monitors if m.bus == bus), None)
            if not monitor:
                console.print(f"[red]Monitor with bus {bus} not found.[/red]")
                return
        else:
            if len(monitors) == 1:
                monitor = monitors[0]
            else:
                console.print("[yellow]Multiple monitors detected. Use --bus option.[/yellow]")
                detect.callback()
                return
        
        if value is not None:
            # Set brightness
            if not 0 <= value <= 100:
                console.print("[red]Brightness value must be between 0 and 100.[/red]")
                return
            
            try:
                controller.set_brightness(monitor, value)
                console.print(f"[green]Set brightness to {value}% for {monitor.name}[/green]")
            except DDCError as e:
                console.print(f"[red]Failed to set brightness: {e}[/red]")
        else:
            # Get brightness
            try:
                current, maximum = controller.get_brightness(monitor)
                percentage = round((current / maximum) * 100) if maximum > 0 else 0
                console.print(f"Brightness for {monitor.name}: {current}/{maximum} ({percentage}%)")
            except DDCError as e:
                console.print(f"[red]Failed to get brightness: {e}[/red]")
    
    except DDCError as e:
        console.print(f"[red]Error: {e}[/red]")


@main.command()
@click.option('--bus', type=int, help='Monitor bus number (use detect command to find)')
@click.option('--value', type=int, help='Contrast value to set (0-100)')
def contrast(bus: Optional[int], value: Optional[int]):
    """Get or set monitor contrast."""
    controller = DDCController()
    
    try:
        monitors = controller.detect_monitors()
        if not monitors:
            console.print("[red]No monitors detected.[/red]")
            return
        
        # Select monitor
        if bus is not None:
            monitor = next((m for m in monitors if m.bus == bus), None)
            if not monitor:
                console.print(f"[red]Monitor with bus {bus} not found.[/red]")
                return
        else:
            if len(monitors) == 1:
                monitor = monitors[0]
            else:
                console.print("[yellow]Multiple monitors detected. Use --bus option.[/yellow]")
                detect.callback()
                return
        
        if value is not None:
            # Set contrast
            if not 0 <= value <= 100:
                console.print("[red]Contrast value must be between 0 and 100.[/red]")
                return
            
            try:
                controller.set_contrast(monitor, value)
                console.print(f"[green]Set contrast to {value}% for {monitor.name}[/green]")
            except DDCError as e:
                console.print(f"[red]Failed to set contrast: {e}[/red]")
        else:
            # Get contrast
            try:
                current, maximum = controller.get_contrast(monitor)
                percentage = round((current / maximum) * 100) if maximum > 0 else 0
                console.print(f"Contrast for {monitor.name}: {current}/{maximum} ({percentage}%)")
            except DDCError as e:
                console.print(f"[red]Failed to get contrast: {e}[/red]")
    
    except DDCError as e:
        console.print(f"[red]Error: {e}[/red]")


@main.command()
@click.option('--bus', type=int, help='Monitor bus number')
def info(bus: Optional[int]):
    """Show detailed information about monitors."""
    controller = DDCController()
    
    try:
        monitors = controller.detect_monitors()
        if not monitors:
            console.print("[red]No monitors detected.[/red]")
            return
        
        monitors_to_show = [monitors[0]] if bus is None and len(monitors) == 1 else \
                          [m for m in monitors if m.bus == bus] if bus is not None else monitors
        
        for monitor in monitors_to_show:
            console.print(f"\n[bold]Monitor: {monitor.name}[/bold]")
            console.print(f"Bus: {monitor.bus}")
            console.print(f"Manufacturer: {monitor.manufacturer}")
            console.print(f"Model: {monitor.model}")
            console.print(f"Serial: {monitor.serial or 'N/A'}")
            
            # Get current values
            try:
                brightness_current, brightness_max = controller.get_brightness(monitor)
                brightness_pct = round((brightness_current / brightness_max) * 100) if brightness_max > 0 else 0
                console.print(f"Brightness: {brightness_current}/{brightness_max} ({brightness_pct}%)")
            except DDCError:
                console.print("Brightness: [dim]Not available[/dim]")
            
            try:
                contrast_current, contrast_max = controller.get_contrast(monitor)
                contrast_pct = round((contrast_current / contrast_max) * 100) if contrast_max > 0 else 0
                console.print(f"Contrast: {contrast_current}/{contrast_max} ({contrast_pct}%)")
            except DDCError:
                console.print("Contrast: [dim]Not available[/dim]")
            
            # Get supported features
            try:
                features = controller.get_supported_features(monitor)
                feature_names = [f.name for f in features]
                console.print(f"Supported features: {', '.join(feature_names)}")
            except DDCError:
                console.print("Supported features: [dim]Could not determine[/dim]")
    
    except DDCError as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == '__main__':
    main()