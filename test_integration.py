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


def print_banner(text: str) -> None:
    print(f"\n{CYAN}{BOLD}{'=' * 78}")
    print(f" {text}")
    print(f"{'=' * 78}{RESET}\n")


def test_system_health(base_url: str) -> bool:
    print(f"{BOLD}[1/4] Testing System Health Check (GET {base_url}/api/health)...{RESET}")
    try:
        resp = requests.get(f"{base_url}/api/health", timeout=6.0)
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


def test_live_prediction_loop(base_url: str) -> bool:
    print(f"{BOLD}[2/4] Testing Backend -> ML -> Inference Loop (POST {base_url}/api/v1/predict/live)...{RESET}")
    
    # 10-day severe rainfall accumulation sequence (simulating monsoon cloudburst)
    payload: Dict[str, Any] = {
        "gauge_id": "684",
        "rainfall_history_10d": [12.0, 18.5, 25.0, 42.0, 68.5, 95.0, 115.0, 130.0, 150.0, 180.0],
        "onset_model": "RandomForest",
        "active_model": "XGBoost",
    }

    try:
        resp = requests.post(f"{base_url}/api/v1/predict/live", json=payload, timeout=8.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        assert data.get("status") == "success", "Response status is not 'success'"
        
        # Extract predictions
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

        # Assertions
        assert 0.0 <= prob <= 1.0, f"Probability {prob} out of valid [0, 1] range!"
        assert tier in {"NORMAL", "ADVISORY", "WARNING", "EMERGENCY"}, f"Invalid alert tier: {tier}"

        print(f"  {GREEN}✓ End-to-End ML Inference Loop: PASSED{RESET}\n")
        return True
    except Exception as exc:
        print(f"  {RED}✗ Prediction Loop Failed: {exc}{RESET}\n")
        return False


def test_citizen_sos_pipeline(base_url: str) -> bool:
    print(f"{BOLD}[3/4] Testing Citizen SOS Ingestion & Retrieval (/api/report-flood & /api/reports)...{RESET}")
    report_payload = {
        "latitude": 17.2890,
        "longitude": 74.1810,
        "severity": "above_waist_danger",
        "landmark_notes": "Integration Test: Karad Old Bridge overflowing",
    }
    try:
        # 1. Post report
        post_resp = requests.post(f"{base_url}/api/report-flood", json=report_payload, timeout=5.0)
        assert post_resp.status_code == 200, f"Expected 200, got {post_resp.status_code}"
        
        # 2. Get reports
        get_resp = requests.get(f"{base_url}/api/reports", timeout=5.0)
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


def test_evacuation_routing(base_url: str) -> bool:
    print(f"{BOLD}[4/4] Testing Evacuation Routing Telemetry (/api/evacuation-route)...{RESET}")
    try:
        resp = requests.get(f"{base_url}/api/evacuation-route?lat=18.5204&lng=73.8567", timeout=5.0)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="PRAVAH End-to-End Integration Suite")
    parser.add_argument("--host", default="http://localhost:8000", help="FastAPI backend host URL")
    args = parser.parse_args()

    print_banner("🌊 PRAVAH END-TO-END INTEGRATION TEST SUITE (SIH 2026)")
    print(f"Target Backend Server: {args.host}\n")

    results = [
        test_system_health(args.host),
        test_live_prediction_loop(args.host),
        test_citizen_sos_pipeline(args.host),
        test_evacuation_routing(args.host),
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
