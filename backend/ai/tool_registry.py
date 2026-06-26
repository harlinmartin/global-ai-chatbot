"""
Phase 12 — Agentic Tool Calling: Tool Registry

Defines the tools the AI can invoke during a conversation, their
OpenAI/Groq-compatible JSON-Schema descriptions, and a dispatcher
that executes them by name.
"""

import json
import httpx
from typing import Any

# ---------------------------------------------------------------------------
# 1.  TOOL IMPLEMENTATIONS
# ---------------------------------------------------------------------------

# Simulated orders database (demo data)
_ORDERS_DB: dict[str, dict] = {
    "1024": {"status": "Shipped", "tracking": "UPS-9876543210", "eta": "June 28, 2026"},
    "1025": {"status": "Processing", "tracking": None, "eta": "July 1, 2026"},
    "1026": {"status": "Delivered", "tracking": "FEDEX-1122334455", "eta": "June 20, 2026"},
    "1027": {"status": "Cancelled", "tracking": None, "eta": None},
    "2048": {"status": "Out for Delivery", "tracking": "DHL-5566778899", "eta": "Today"},
}


def check_order_status(order_id: str) -> str:
    """Look up the status of an order by its ID."""
    order = _ORDERS_DB.get(order_id)
    if not order:
        return json.dumps({
            "error": f"Order #{order_id} not found. Please double-check the order number."
        })
    return json.dumps({
        "order_id": order_id,
        "status": order["status"],
        "tracking_number": order["tracking"],
        "estimated_delivery": order["eta"],
    })


def book_meeting(date: str, time: str) -> str:
    """Book a meeting at the requested date and time (simulated)."""
    # In production this would integrate with Google Calendar, Calendly, etc.
    return json.dumps({
        "confirmation": True,
        "date": date,
        "time": time,
        "meeting_link": "https://meet.example.com/abc-xyz-123",
        "message": f"Meeting booked for {date} at {time}. A calendar invite has been sent!",
    })


def get_weather(location: str) -> str:
    """
    Fetch real weather data from the free Open-Meteo Geocoding + Forecast API.
    No API key required.
    """
    try:
        # Step 1: Geocode the location name → lat/lon
        geo_resp = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1, "language": "en"},
            timeout=10,
        )
        geo_data = geo_resp.json()

        results = geo_data.get("results")
        if not results:
            return json.dumps({"error": f"Could not find location '{location}'."})

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        resolved_name = results[0].get("name", location)
        country = results[0].get("country", "")

        # Step 2: Fetch current weather
        weather_resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "temperature_unit": "celsius",
            },
            timeout=10,
        )
        weather_data = weather_resp.json()
        current = weather_data.get("current_weather", {})

        return json.dumps({
            "location": f"{resolved_name}, {country}",
            "temperature_celsius": current.get("temperature"),
            "windspeed_kmh": current.get("windspeed"),
            "wind_direction_degrees": current.get("winddirection"),
            "weather_code": current.get("weathercode"),
            "is_day": bool(current.get("is_day")),
        })

    except Exception as e:
        return json.dumps({"error": f"Weather API error: {str(e)}"})


# ---------------------------------------------------------------------------
# 2.  TOOL DEFINITIONS (OpenAI / Groq JSON-Schema format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "check_order_status",
            "description": "Look up the current status, tracking number, and estimated delivery date of a customer order by its order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order number/ID to look up, e.g. '1024'.",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_meeting",
            "description": "Book a meeting or appointment at a specified date and time. Returns a confirmation with a meeting link.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date for the meeting, e.g. '2026-06-28' or 'tomorrow'.",
                    },
                    "time": {
                        "type": "string",
                        "description": "The time for the meeting, e.g. '3:00 PM' or '15:00'.",
                    },
                },
                "required": ["date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather conditions for a given location. Returns temperature, wind speed, and conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city or location name, e.g. 'London' or 'New York'.",
                    }
                },
                "required": ["location"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# 3.  DISPATCHER
# ---------------------------------------------------------------------------

_TOOL_MAP: dict[str, callable] = {
    "check_order_status": check_order_status,
    "book_meeting": book_meeting,
    "get_weather": get_weather,
}


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """
    Execute a tool by name with the given arguments.
    Returns the tool's JSON string result.
    Raises ValueError for unknown tools.
    """
    func = _TOOL_MAP.get(name)
    if not func:
        raise ValueError(f"Unknown tool: '{name}'. Available tools: {list(_TOOL_MAP.keys())}")
    return func(**arguments)


def get_tool_label(name: str) -> str:
    """Return a human-friendly status label for the UI spinner."""
    labels = {
        "check_order_status": "⚙️ Checking order database...",
        "book_meeting": "📅 Booking your meeting...",
        "get_weather": "🌤️ Fetching weather data...",
    }
    return labels.get(name, f"⚙️ Running {name}...")
