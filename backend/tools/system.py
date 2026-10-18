import psutil
import datetime
from backend.tools.registry import register_tool

@register_tool(
    name="get_system_telemetry",
    description="Get real-time computer system diagnostics including CPU usage, RAM memory usage, battery percentage, and charging state.",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def get_system_telemetry():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    battery = psutil.sensors_battery()
    
    data = {
        "cpu_percent": cpu,
        "ram_percent": ram.percent,
        "ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ram_total_gb": round(ram.total / (1024 ** 3), 2),
        "battery_percent": round(battery.percent, 1) if battery else None,
        "battery_plugged": battery.power_plugged if battery else None
    }
    
    battery_info = f"{data['battery_percent']}%" + (" (Charging)" if data.get("battery_plugged") else "") if data["battery_percent"] else "Desktop / No battery"
    return f"System Status: CPU is at {cpu}%, RAM usage is {ram.percent}% ({data['ram_used_gb']}GB / {data['ram_total_gb']}GB), Battery is {battery_info}."

@register_tool(
    name="get_current_time_and_date",
    description="Get the current local time, date, and day of the week.",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def get_current_time_and_date():
    now = datetime.datetime.now()
    return now.strftime("It is %I:%M %p on %A, %B %d, %Y.")
