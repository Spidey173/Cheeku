import datetime
from backend.tools.registry import register_tool
from backend.utils.logger import logger

try:
    import psutil
except ImportError:
    psutil = None


@register_tool(
    name="get_system_telemetry",
    description="Get real-time computer system diagnostics including CPU usage, RAM memory usage, battery percentage, and charging state.",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    requires_system_action=False
)
def get_system_telemetry() -> str:
    if psutil is None:
        return "System telemetry is unavailable (psutil package is not installed)."

    try:
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
    except Exception as e:
        logger.error(f"Error reading system telemetry: {e}")
        return f"Error retrieving system diagnostics: {str(e)}"


@register_tool(
    name="get_current_time_and_date",
    description="Get the current local time, date, and day of the week.",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    requires_system_action=False
)
def get_current_time_and_date() -> str:
    now = datetime.datetime.now()
    return now.strftime("It is %I:%M %p on %A, %B %d, %Y.")
