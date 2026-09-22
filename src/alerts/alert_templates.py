"""
PRAVAH — Centralized Alert Message Template System
Generates standardized WARNING, CRITICAL, and EVACUATION alerts
tailored for SMS, WhatsApp, and Telegram formats.
"""

from __future__ import annotations

from typing import Any, Dict
from src.alerts.models.alert import AlertSeverity


def render_alert_message(
    severity: AlertSeverity,
    channel: str,
    context: Dict[str, Any],
) -> str:
    """
    Renders message text adapted to channel formatting rules.
    Dynamic keys:
      location, risk_percentage, river_level, river_threshold,
      rainfall_forecast, timestamp, evacuation_route, shelter_location
    """
    loc = context.get("location", "Monitored Catchment")
    risk_pct = context.get("risk_percentage", 75)
    river_lvl = context.get("river_level")
    river_thresh = context.get("river_threshold")
    rain_fc = context.get("rainfall_forecast")
    route = context.get("evacuation_route") or "Designated primary high-ground evacuation route"
    shelter = context.get("shelter_location") or "Nearest verified elevated disaster refuge center"
    ts = context.get("timestamp", "")

    # Detail line helpers
    river_line = f"River Stage: {river_lvl}m" + (f" (Threshold: {river_thresh}m)" if river_thresh else "") if river_lvl else ""
    rain_line = f"Forecast Rain: {rain_fc}mm" if rain_fc else ""

    if channel == "sms":
        # Concise plain-text formatting (SMS budget)
        if severity == AlertSeverity.EVACUATION:
            return (
                f"PRAVAH EVACUATION: Immediate action required in {loc}! "
                f"Flood risk {risk_pct}%. Evacuate via {route} to {shelter}. Follow local authorities."
            )
        elif severity == AlertSeverity.CRITICAL:
            info = f" | {river_line}" if river_line else ""
            return (
                f"PRAVAH CRITICAL: Severe flood threat detected in {loc}! "
                f"Risk: {risk_pct}%{info}. Move to higher ground immediately. SDRF on alert."
            )
        else:  # WARNING
            info = f" | {river_line}" if river_line else ""
            return (
                f"PRAVAH WARNING: Elevated flood risk in {loc}. "
                f"Risk: {risk_pct}%{info}. Stay alert, monitor water levels, avoid riverbanks."
            )

    elif channel == "whatsapp":
        # WhatsApp Markdown formatting (*bold*, _italic_)
        if severity == AlertSeverity.EVACUATION:
            return (
                f"🚨 *PRAVAH EVACUATION DIRECTIVE — IMMEDIATE ACTION REQUIRED*\n\n"
                f"📍 *Location:* {loc}\n"
                f"⚠️ *Flood Threat:* EXTREME (Risk: {risk_pct}%)\n"
                f"{f'🌊 *{river_line}*\n' if river_line else ''}"
                f"{f'🌧️ *{rain_line}*\n' if rain_line else ''}\n"
                f"🏃 *Evacuation Action:*\n"
                f"• Immediate evacuation initiated by SDRF/NDRF.\n"
                f"• *Safe Route:* {route}\n"
                f"• *Emergency Shelter:* {shelter}\n\n"
                f"Do not attempt to cross flooded bridges or culverts."
            )
        elif severity == AlertSeverity.CRITICAL:
            return (
                f"🚨 *PRAVAH CRITICAL FLOOD ALERT*\n\n"
                f"📍 *Location:* {loc}\n"
                f"⚠️ *Risk Assessment:* CRITICAL ({risk_pct}%)\n"
                f"{f'🌊 {river_line}\n' if river_line else ''}"
                f"{f'🌧️ {rain_line}\n' if rain_line else ''}\n"
                f"Rapidly rising water levels detected. Move families, livestock, and essential equipment "
                f"to upper stories or elevated community refuges immediately."
            )
        else:  # WARNING
            return (
                f"⚠️ *PRAVAH FLOOD ADVISORY / WARNING*\n\n"
                f"📍 *Location:* {loc}\n"
                f"📊 *Flood Probability:* {risk_pct}%\n"
                f"{f'🌊 {river_line}\n' if river_line else ''}"
                f"{f'🌧️ {rain_line}\n' if rain_line else ''}\n"
                f"Elevated catchment saturation detected. Avoid low-lying riparian areas and follow "
                f"official disaster telemetry broadcasts."
            )

    elif channel == "telegram":  # Telegram (HTML formatted)
        if severity == AlertSeverity.EVACUATION:
            return (
                f"🚨 <b>PRAVAH EVACUATION DIRECTIVE — IMMEDIATE ACTION</b>\n\n"
                f"📍 <b>Location:</b> {loc}\n"
                f"⚠️ <b>Severity:</b> EVACUATION (Risk: {risk_pct}%)\n"
                f"{f'🌊 <b>{river_line}</b>\n' if river_line else ''}"
                f"{f'🌧️ <b>{rain_line}</b>\n' if rain_line else ''}\n"
                f"🏃 <b>Directive:</b>\n"
                f"• Evacuate immediately via designated corridors.\n"
                f"• <b>Route:</b> {route}\n"
                f"• <b>Safe Shelter:</b> {shelter}\n\n"
                f"<i>Issued by PRAVAH Disaster Early Warning Network</i>"
            )
        elif severity == AlertSeverity.CRITICAL:
            return (
                f"🚨 <b>PRAVAH CRITICAL FLOOD ALERT</b>\n\n"
                f"📍 <b>Location:</b> {loc}\n"
                f"⚠️ <b>Risk Tier:</b> CRITICAL ({risk_pct}%)\n"
                f"{f'🌊 {river_line}\n' if river_line else ''}"
                f"{f'🌧️ {rain_line}\n' if rain_line else ''}\n"
                f"Water stage approaching emergency danger level. Move to high ground immediately."
            )
        else:  # WARNING
            return (
                f"⚠️ <b>PRAVAH FLOOD WARNING ADVISORY</b>\n\n"
                f"📍 <b>Location:</b> {loc}\n"
                f"📊 <b>Risk Level:</b> {risk_pct}%\n"
                f"{f'🌊 {river_line}\n' if river_line else ''}"
                f"{f'🌧️ {rain_line}\n' if rain_line else ''}\n"
                f"Hydrological models predict significant catchment runoff. Stay vigilant."
            )

    elif channel == "ivrs":
        # Clear, natural spoken voice script for outbound phone calls
        if severity == AlertSeverity.EVACUATION:
            return (
                f"Emergency alert. This is an urgent evacuation call from the PRAVAH disaster management center. "
                f"Severe flash flooding is occurring in {loc}. "
                f"Estimated flood risk is {risk_pct} percent. "
                f"Please evacuate your area immediately using designated route {route}. "
                f"Proceed to the nearest relief shelter at {shelter}. "
                f"Repeat, evacuate immediately to {shelter}. Stay safe."
            )
        elif severity == AlertSeverity.CRITICAL:
            return (
                f"Emergency notification from the PRAVAH flood early warning network. "
                f"Critical flood danger detected for {loc}. "
                f"River levels are surging. "
                f"Move to high ground immediately and avoid all riverbanks, bridges, and low-lying roads. "
                f"Emergency disaster response teams have been activated."
            )
        else:  # WARNING
            return (
                f"Attention. This is a flood warning advisory from PRAVAH disaster management for {loc}. "
                f"Heavy upstream rainfall is causing rising water levels. "
                f"Please monitor official advisories, keep emergency supplies ready, and avoid flooded roadways."
            )

    return f"PRAVAH ALERT [{severity.value}] for {loc}: Flood risk estimated at {risk_pct}%."
