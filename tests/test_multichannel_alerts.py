"""
PRAVAH — Multi-Channel Alerting System Comprehensive Test Suite
Tests:
1. Alert Rules Engine (Risk > 70%, River Stage Thresholds, Heavy Rainfall Forecast)
2. Severity & Channel-Specific Template Rendering (WARNING, CRITICAL, EVACUATION)
3. Channel Providers (SMS, WhatsApp, Telegram) in Live & Simulation Modes
4. AlertManager Orchestration (Concurrent Dispatch, Fault-Tolerant Isolation)
5. Duplicate Cooldown & Severity Escalation Guarantee
6. REST API Endpoints (Trigger, History, Stats, Channel Status, Single Record)
7. Backward Compatibility: Existing /api/alerts/send Endpoint Preserved
"""

import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.app import app
from src.alerts.alert_manager import alert_manager
from src.alerts.alert_rules import evaluate_alert_rules
from src.alerts.alert_templates import render_alert_message
from src.alerts.channels.sms import SMSAlertChannel
from src.alerts.channels.telegram import TelegramAlertChannel
from src.alerts.channels.whatsapp import WhatsAppAlertChannel
from src.alerts.models.alert import (
    AlertSeverity,
    ChannelDeliveryDetail,
    ChannelType,
    DeliveryStatus,
    TriggerType,
)


class TestMultiChannelAlerts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Alert Trigger Rules
    # -------------------------------------------------------------------------

    def test_risk_score_trigger_rule(self):
        """Verify Risk Score trigger rule: < 70% does not trigger; >= 70% triggers."""
        # Below threshold (e.g. 50%)
        eval_safe = evaluate_alert_rules(risk_score=50.0)
        self.assertFalse(eval_safe.is_triggered)

        # At / above threshold (e.g. 75%) -> WARNING
        eval_warn = evaluate_alert_rules(risk_score=75.0)
        self.assertTrue(eval_warn.is_triggered)
        self.assertEqual(eval_warn.severity, AlertSeverity.WARNING)
        self.assertIn("75%", eval_warn.trigger_reason)

        # High risk (e.g. 86%) -> CRITICAL
        eval_crit = evaluate_alert_rules(risk_score=86.0)
        self.assertTrue(eval_crit.is_triggered)
        self.assertEqual(eval_crit.severity, AlertSeverity.CRITICAL)

        # Extreme risk (e.g. 95%) -> EVACUATION
        eval_evac = evaluate_alert_rules(risk_score=95.0)
        self.assertTrue(eval_evac.is_triggered)
        self.assertEqual(eval_evac.severity, AlertSeverity.EVACUATION)

    def test_river_level_trigger_rule(self):
        """Verify river level threshold triggers."""
        # Below warning threshold (e.g. 6.5m vs 8.0m warning)
        eval_safe = evaluate_alert_rules(river_level=6.5, river_threshold=8.0)
        self.assertFalse(eval_safe.is_triggered)

        # Exceeds warning threshold (e.g. 8.4m vs 8.0m) -> WARNING
        eval_warn = evaluate_alert_rules(river_level=8.4, river_threshold=8.0)
        self.assertTrue(eval_warn.is_triggered)
        self.assertEqual(eval_warn.severity, AlertSeverity.WARNING)
        self.assertEqual(eval_warn.trigger_type, TriggerType.RIVER_LEVEL)

        # Exceeds critical threshold (e.g. 9.2m vs 9.0m) -> CRITICAL
        eval_crit = evaluate_alert_rules(river_level=9.2, river_threshold=8.0)
        self.assertTrue(eval_crit.is_triggered)
        self.assertEqual(eval_crit.severity, AlertSeverity.CRITICAL)

    def test_rainfall_forecast_trigger_rule(self):
        """Verify heavy rainfall forecast triggers."""
        # Below threshold (e.g. 80mm vs 150mm)
        eval_safe = evaluate_alert_rules(rainfall_forecast=80.0)
        self.assertFalse(eval_safe.is_triggered)

        # Exceeds heavy rain threshold (e.g. 175mm) -> WARNING
        eval_warn = evaluate_alert_rules(rainfall_forecast=175.0)
        self.assertTrue(eval_warn.is_triggered)
        self.assertEqual(eval_warn.severity, AlertSeverity.WARNING)
        self.assertEqual(eval_warn.trigger_type, TriggerType.RAINFALL_FORECAST)

    # -------------------------------------------------------------------------
    # 2. Template Rendering
    # -------------------------------------------------------------------------

    def test_template_rendering_across_channels(self):
        """Verify message formatting for SMS, WhatsApp, and Telegram."""
        context = {
            "location": "Panchgani",
            "risk_percentage": 82,
            "river_level": 8.8,
            "river_threshold": 8.0,
            "rainfall_forecast": 190.0,
            "evacuation_route": "SH-72 North Ridge Corridor",
            "shelter_location": "Panchgani High-Ground Refuge",
        }

        # 1. SMS (concise plain text)
        sms_text = render_alert_message(AlertSeverity.CRITICAL, "sms", context)
        self.assertIn("PRAVAH CRITICAL", sms_text)
        self.assertIn("Panchgani", sms_text)
        self.assertIn("82%", sms_text)

        # 2. WhatsApp (bold formatting with *)
        wa_text = render_alert_message(AlertSeverity.CRITICAL, "whatsapp", context)
        self.assertIn("*PRAVAH CRITICAL FLOOD ALERT*", wa_text)
        self.assertIn("*Location:* Panchgani", wa_text)

        # 3. Telegram (HTML formatting)
        tg_text = render_alert_message(AlertSeverity.EVACUATION, "telegram", context)
        self.assertIn("<b>PRAVAH EVACUATION DIRECTIVE", tg_text)
        self.assertIn("SH-72 North Ridge Corridor", tg_text)

    # -------------------------------------------------------------------------
    # 3. Channel Providers
    # -------------------------------------------------------------------------

    def test_sms_channel_simulation_mode(self):
        """Verify SMS provider successfully delivers in simulation mode."""
        sms_ch = SMSAlertChannel()
        self.assertTrue(sms_ch.is_enabled())
        # Call send asynchronously via event loop or client
        res = self.client.post("/api/alerts/trigger", json={
            "location": f"TestSMSZone_{int(time.time())}",
            "risk_score": 85.0,
            "channels": ["sms"],
            "custom_recipient_phone": "+919876543210",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("channels", data)
        sms_deliv = next((c for c in data["channels"] if c["channel"] == "sms"), None)
        self.assertIsNotNone(sms_deliv)
        self.assertIn(sms_deliv["delivery_status"], ("SENT", "DELIVERED"))

    def test_whatsapp_channel_simulation_mode(self):
        """Verify WhatsApp provider delivers in simulation mode."""
        res = self.client.post("/api/alerts/trigger", json={
            "location": f"TestWAZone_{int(time.time())}",
            "risk_score": 88.0,
            "channels": ["whatsapp"],
            "custom_recipient_phone": "+919822011223",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        wa_deliv = next((c for c in data["channels"] if c["channel"] == "whatsapp"), None)
        self.assertIsNotNone(wa_deliv)
        self.assertIn(wa_deliv["delivery_status"], ("SENT", "DELIVERED"))

    def test_telegram_channel_simulation_mode(self):
        """Verify Telegram provider delivers in simulation mode."""
        res = self.client.post("/api/alerts/trigger", json={
            "location": f"TestTGZone_{int(time.time())}",
            "risk_score": 79.0,
            "channels": ["telegram"],
            "custom_telegram_chat_id": "@pravah_sih_demo",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        tg_deliv = next((c for c in data["channels"] if c["channel"] == "telegram"), None)
        self.assertIsNotNone(tg_deliv)
        self.assertIn(tg_deliv["delivery_status"], ("SENT", "DELIVERED"))

    # -------------------------------------------------------------------------
    # 4. Multi-Channel Concurrent Dispatch & Fault Isolation
    # -------------------------------------------------------------------------

    def test_multichannel_simultaneous_dispatch(self):
        """Dispatch concurrently to SMS + WhatsApp + Telegram in a single trigger."""
        payload = {
            "location": f"MultiZone_{int(time.time())}",
            "region": "Maharashtra",
            "risk_score": 92.0,
            "river_level": 9.4,
            "rainfall_forecast": 220.0,
            "evacuation_route": "NH-48 High Flyover",
            "shelter_location": "Karad High Ground Staging Area",
        }
        res = self.client.post("/api/alerts/trigger", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["severity"], "EVACUATION")
        self.assertEqual(data["overall_status"], "DELIVERED")
        channels_received = [c["channel"] for c in data["channels"]]
        self.assertIn("sms", channels_received)
        self.assertIn("whatsapp", channels_received)
        self.assertIn("telegram", channels_received)

    def test_fault_tolerant_channel_isolation(self):
        """Verify that failure in one channel (e.g. WhatsApp) does NOT crash SMS or Telegram."""
        # Temporarily mock whatsapp_channel.send to raise an Exception
        async def failing_send(*args, **kwargs):
            raise ConnectionError("Mock WhatsApp network drop")

        with patch.object(alert_manager.whatsapp_channel, "send", side_effect=failing_send):
            payload = {
                "location": f"FaultZone_{int(time.time())}",
                "risk_score": 85.0,
                "channels": ["sms", "whatsapp", "telegram"],
            }
            res = self.client.post("/api/alerts/trigger", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()

            # WhatsApp failed, but overall status is PARTIAL and other channels succeeded
            self.assertEqual(data["overall_status"], "PARTIAL")
            wa_deliv = next(c for c in data["channels"] if c["channel"] == "whatsapp")
            sms_deliv = next(c for c in data["channels"] if c["channel"] == "sms")
            tg_deliv = next(c for c in data["channels"] if c["channel"] == "telegram")

            self.assertEqual(wa_deliv["delivery_status"], "FAILED")
            self.assertIn(sms_deliv["delivery_status"], ("SENT", "DELIVERED"))
            self.assertIn(tg_deliv["delivery_status"], ("SENT", "DELIVERED"))

    # -------------------------------------------------------------------------
    # 5. Duplicate Cooldown & Severity Escalation
    # -------------------------------------------------------------------------

    def test_duplicate_alert_cooldown_and_escalation(self):
        """Verify duplicate suppression within cooldown, but immediate trigger on escalation."""
        loc_name = f"CooldownLoc_{int(time.time())}"

        # 1. First trigger at WARNING (risk 74%)
        p1 = {"location": loc_name, "risk_score": 74.0}
        r1 = self.client.post("/api/alerts/trigger", json=p1)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["severity"], "WARNING")

        # 2. Immediate second trigger at same WARNING (risk 74%) -> should be suppressed
        p2 = {"location": loc_name, "risk_score": 74.0}
        r2 = self.client.post("/api/alerts/trigger", json=p2)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["status"], "cooldown_suppressed")

        # 3. Third trigger escalates to CRITICAL (risk 88%) -> MUST bypass cooldown and dispatch!
        p3 = {"location": loc_name, "risk_score": 88.0}
        r3 = self.client.post("/api/alerts/trigger", json=p3)
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()["severity"], "CRITICAL")
        self.assertIn("channels", r3.json())

    # -------------------------------------------------------------------------
    # 6. REST API Endpoints
    # -------------------------------------------------------------------------

    def test_get_alerts_history_and_filters(self):
        """Verify GET /api/alerts returns chronological records and accepts filters."""
        res = self.client.get("/api/alerts?limit=20")
        self.assertEqual(res.status_code, 200)
        alerts = res.json()
        self.assertIsInstance(alerts, list)
        self.assertGreaterEqual(len(alerts), 1)

        first_alert = alerts[0]
        self.assertIn("alert_code", first_alert)
        self.assertIn("severity", first_alert)
        self.assertIn("channels", first_alert)

    def test_get_alert_stats(self):
        """Verify GET /api/alerts/stats returns KPI metrics."""
        res = self.client.get("/api/alerts/stats")
        self.assertEqual(res.status_code, 200)
        stats = res.json()

        self.assertIn("total_alerts", stats)
        self.assertIn("critical_alerts", stats)
        self.assertIn("warnings", stats)
        self.assertIn("evacuation_alerts", stats)
        self.assertIn("successful_deliveries", stats)
        self.assertGreaterEqual(stats["total_alerts"], 1)

    def test_get_channel_status(self):
        """Verify GET /api/alerts/status returns provider modes."""
        res = self.client.get("/api/alerts/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("sms_enabled", data)
        self.assertIn("whatsapp_enabled", data)
        self.assertIn("telegram_enabled", data)
        self.assertIn("sms_mode", data)
        self.assertIn("whatsapp_mode", data)
        self.assertIn("telegram_mode", data)

    # -------------------------------------------------------------------------
    # 7. Backward Compatibility Guarantee
    # -------------------------------------------------------------------------

    def test_existing_single_channel_alerts_send_endpoint(self):
        """Confirm original POST /api/alerts/send (Twilio WhatsApp) remains 100% operational."""
        legacy_payload = {
            "phone_number": "+919876543210",
            "alert_message": "Legacy endpoint backward-compatibility check.",
        }
        res = self.client.post("/api/alerts/send", json=legacy_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("recipient", data)


if __name__ == "__main__":
    unittest.main()
