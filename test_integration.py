"""
===============================================================================
PRAVAH — End-to-End Integration & System Verification Suite (SIH 2026)
===============================================================================
Usage:
    python test_integration.py
    python test_integration.py --host http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class UnifiedClient:
    """Seamlessly bridges between live HTTP server and in-process FastAPI TestClient."""
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.use_test_client = False
        try:
            r = requests.get(f"{self.base_url}/api/health", timeout=1.5)
            if r.status_code == 200:
                print(f"  • Connected to live FastAPI server on {self.base_url}")
                return
        except Exception:
            pass

        print(f"  • Live server not detected on {self.base_url}. Running in-process ASGI test harness.")
        from fastapi.testclient import TestClient
        from src.api.app import app
        self._test_client = TestClient(app)
        self.use_test_client = True

    def get(self, path: str, params: dict = None, timeout: float = 10.0):
        if self.use_test_client:
            return self._test_client.get(path, params=params)
        return requests.get(f"{self.base_url}{path}", params=params, timeout=timeout)

    def post(self, path: str, json: dict = None, timeout: float = 10.0):
        if self.use_test_client:
            return self._test_client.post(path, json=json)
        return requests.post(f"{self.base_url}{path}", json=json, timeout=timeout)


def print_banner(text: str) -> None:
    print(f"\n{CYAN}{BOLD}{'=' * 78}")
    print(f" {text}")
    print(f"{'=' * 78}{RESET}\n")


def test_system_health(client: UnifiedClient) -> bool:
    print(f"{BOLD}[1/6] Testing System Health Check (/api/health)...{RESET}")
    try:
        resp = client.get("/api/health")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        print(f"  • Status               : {GREEN}{data.get('status')}{RESET}")
        print(f"  • ML Models Loaded     : {GREEN if data.get('model_loaded') else RED}{data.get('model_loaded')}{RESET}")
        print(f"  • Data API Reachable   : {GREEN if data.get('data_api_reachable') else YELLOW}{data.get('data_api_reachable')}{RESET}")
        print(f"  • Registered Models    : {len(data.get('available_models', []))} models online")
        print(f"  • Monitored Catchments : {data.get('total_catchments', 0)} CWC stations")

        assert data.get("model_loaded") is True, "Models not loaded in memory!"
        print(f"  {GREEN}✓ Health Diagnostic: PASSED{RESET}\n")
        return True
    except Exception as exc:
        print(f"  {RED}✗ Health Diagnostic Failed: {exc}{RESET}\n")
        return False


def test_live_prediction_loop(client: UnifiedClient) -> bool:
    print(f"{BOLD}[2/6] Testing Backend -> ML -> Inference Loop (/api/v1/predict/live)...{RESET}")
    payload: Dict[str, Any] = {
        "gauge_id": "684",
        "rainfall_history_10d": [12.0, 18.5, 25.0, 42.0, 68.5, 95.0, 115.0, 130.0, 150.0, 180.0],
        "onset_model": "RandomForest",
        "active_model": "XGBoost",
    }

    try:
        resp = client.post("/api/v1/predict/live", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        assert data.get("status") == "success", "Response status is not 'success'"

        task_a = data.get("task_a_onset", {})
        alert = data.get("alert_tier", {})
        station = data.get("station", {})

        prob = float(task_a.get("probability", -1.0))
        tier = alert.get("tier", "UNKNOWN")

        print(f"  • Station Target       : {station.get('station_name')} ({station.get('river')})")
        print(f"  • Extracted Flood Risk : {CYAN}{prob * 100:.2f}%{RESET}")
        print(f"  • Tuned Decision Thresh: {task_a.get('threshold', 0.0):.4f}")
        print(f"  • Alert Tier Assigned  : {RED if tier == 'EMERGENCY' else YELLOW if tier == 'WARNING' else GREEN}{tier}{RESET}")
        print(f"  • Operational Directive: {alert.get('recommendation')}")

        assert 0.0 <= prob <= 1.0, f"Probability {prob} out of valid [0, 1] range!"
        assert tier in {"NORMAL", "ADVISORY", "WARNING", "EMERGENCY"}, f"Invalid alert tier: {tier}"

        print(f"  {GREEN}✓ End-to-End ML Inference Loop: PASSED{RESET}\n")
        return True
    except Exception as exc:
        print(f"  {RED}✗ Prediction Loop Failed: {exc}{RESET}\n")
        return False


def test_citizen_sos_pipeline(client: UnifiedClient) -> bool:
    print(f"{BOLD}[3/6] Testing Citizen SOS Ingestion & Retrieval (/api/report-flood & /api/reports)...{RESET}")
    report_payload = {
        "latitude": 17.2890,
        "longitude": 74.1810,
        "severity": "above_waist_danger",
        "landmark_notes": "Integration Test: Karad Old Bridge overflowing",
    }
    try:
        post_resp = client.post("/api/report-flood", json=report_payload)
        assert post_resp.status_code == 200, f"Expected 200, got {post_resp.status_code}"

        get_resp = client.get("/api/reports")
        assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}"
        reports = get_resp.json()
        assert len(reports) > 0, "No active SOS reports returned in array!"

        print(f"  • SOS Logged ID        : #{post_resp.json().get('report_id')}")
        print(f"  • Active Reports Count : {len(reports)} live ground-truth beacons")
        print(f"  {GREEN}✓ Citizen SOS Telemetry Loop: PASSED{RESET}\n")
        return True
    except Exception as exc:
        print(f"  {RED}✗ Citizen SOS Test Failed: {exc}{RESET}\n")
        return False


def test_evacuation_routing(client: UnifiedClient) -> bool:
    print(f"{BOLD}[4/6] Testing Evacuation Routing Telemetry (/api/evacuation-route)...{RESET}")
    try:
        resp = client.get("/api/evacuation-route?lat=18.5204&lng=73.8567")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        camp = data.get("nearest_camp", {})
        dist = data.get("distance_km")

        print(f"  • Nearest Safe Refuge  : {camp.get('name')} ({camp.get('type')})")
        print(f"  • Calculated Distance  : {dist} km (Haversine Formula)")
        print(f"  • Est. Walk Time       : {data.get('estimated_walk_time_mins')} mins")

        assert dist is not None and dist >= 0.0, "Invalid distance calculated!"
        print(f"  {GREEN}✓ Evacuation Safe-Zone Routing: PASSED{RESET}\n")
        return True
    except Exception as exc:
        print(f"  {RED}✗ Evacuation Routing Test Failed: {exc}{RESET}\n")
        return False


def test_weather_cache(client: UnifiedClient) -> bool:
    print(f"{BOLD}[5/6] Testing Automated Weather Telemetry Cache (/api/weather/latest)...{RESET}")
    try:
        resp = client.get("/api/weather/latest")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()

        print(f"  • Weather Status       : {GREEN if data.get('status') == 'live' else YELLOW}{data.get('status')}{RESET}")
        print(f"  • Rainfall Rate        : {data.get('rainfall')} mm/hr")
        print(f"  • Station Target       : {data.get('station_target')}")

        assert "status" in data, "Missing 'status' in weather state"
        print(f"  {GREEN}✓ Weather Telemetry Cache: PASSED{RESET}\n")
        return True
    except Exception as exc:
        print(f"  {RED}✗ Weather Telemetry Test Failed: {exc}{RESET}\n")
        return False


def test_twilio_alerts(client: UnifiedClient) -> bool:
    print(f"{BOLD}[6/6] Testing Direct Twilio WhatsApp Alert Dispatch (/api/alerts/send)...{RESET}")
    payload = {
        "phone_number": "+919876543210",
        "alert_message": "Integration test: Water level breach warning at Karad Gauge.",
    }
    try:
        resp = client.post("/api/alerts/send", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()

        print(f"  • Dispatch Status      : {GREEN}{data.get('status')}{RESET}")
        print(f"  • Mode                 : {'Simulation Fallback' if data.get('simulated') else 'Live Twilio Carrier'}")
        print(f"  • Message SID          : {data.get('sid')}")
        print(f"  • Dispatched Body      : {data.get('body')}")

        assert data.get("status") == "success", "Alert response status is not success"
        assert "🚨 PRAVAH ALERT:" in data.get("body", ""), "Missing expected PRAVAH prefix in alert body"
        print(f"  {GREEN}✓ Twilio Emergency Alert Dispatch: PASSED{RESET}\n")
        return True
    except Exception as exc:
        print(f"  {RED}✗ Twilio Alert Test Failed: {exc}{RESET}\n")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="PRAVAH End-to-End Integration Suite")
    parser.add_argument("--host", default="http://localhost:8000", help="FastAPI backend host URL")
    args = parser.parse_args()

    print_banner("🌊 PRAVAH END-TO-END INTEGRATION TEST SUITE (SIH 2026)")
    client = UnifiedClient(args.host)

    results = [
        test_system_health(client),
        test_live_prediction_loop(client),
        test_citizen_sos_pipeline(client),
        test_evacuation_routing(client),
        test_weather_cache(client),
        test_twilio_alerts(client),
    ]

    passed = sum(1 for r in results if r)
    total = len(results)

    print("=" * 78)
    if passed == total:
        print(f"{GREEN}{BOLD}🎉 ALL {total}/{total} INTEGRATION CHECKS PASSED! System is 100% demo-ready.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}⚠️ {total - passed}/{total} TESTS FAILED. Review diagnostic logs above.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
