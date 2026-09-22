"""Configuration parameters for the PRAVAH Evacuation Planning Engine."""
import os

# Routing Weights
EVACUATION_RISK_WEIGHT: float = float(os.getenv("EVACUATION_RISK_WEIGHT", "2.5"))
EVACUATION_TIME_WEIGHT: float = float(os.getenv("EVACUATION_TIME_WEIGHT", "1.0"))

# Road Condition Penalties
ROAD_CLOSURE_PENALTY: float = 1e9  # Effectively infinite; closed roads strictly excluded
PARTIALLY_BLOCKED_TIME_PENALTY: float = float(os.getenv("PARTIALLY_BLOCKED_TIME_PENALTY", "10.0"))  # Minutes
PARTIALLY_BLOCKED_RISK_PENALTY: float = float(os.getenv("PARTIALLY_BLOCKED_RISK_PENALTY", "0.20"))  # Added risk score
HIGH_RISK_PENALTY: float = float(os.getenv("HIGH_RISK_PENALTY", "30.0"))

# Speeds
DEFAULT_VEHICLE_SPEED_KMH: float = float(os.getenv("DEFAULT_VEHICLE_SPEED_KMH", "40.0"))
DEFAULT_WALK_SPEED_KMH: float = float(os.getenv("DEFAULT_WALK_SPEED_KMH", "4.5"))

# Safety Classifications Thresholds
RISK_THRESHOLD_LOW: float = 0.25
RISK_THRESHOLD_MODERATE: float = 0.50
RISK_THRESHOLD_HIGH: float = 0.75

# Default Maximum Options to compute
MAX_ROUTE_OPTIONS: int = 3
