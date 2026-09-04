import os
import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger("pravah.alerts")

# -----------------------------------------------------------------------------
# Twilio Configuration (Set via environment variables or replace placeholders)
# -----------------------------------------------------------------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "YOUR_TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


def trigger_emergency_alert(
    phone_number: str,
    catchment_name: str,
    probability: float,
) -> Optional[str]:
    """
    Sends an urgent WhatsApp disaster alert to a citizen using the Twilio API
    when flood probability reaches the EMERGENCY tier (>= 75%).

    :param phone_number: Recipient's mobile number (e.g., '+919876543210' or '9876543210')
    :param catchment_name: Name of the affected catchment/station (e.g., 'Karad' or 'Mahad')
    :param probability: Predicted flood risk probability (0.0 to 1.0 or 0 to 100)
    :return: Twilio Message SID if sent successfully, None otherwise.
    """
    try:
        # Normalize probability to integer percentage
        prob_pct = int(probability * 100) if probability <= 1.0 else int(probability)

        # Ensure the recipient phone number is properly prefixed for WhatsApp
        cleaned_number = phone_number.strip().replace(" ", "").replace("-", "")
        if not cleaned_number.startswith("+"):
            cleaned_number = "+" + cleaned_number
        if not cleaned_number.startswith("whatsapp:"):
            to_whatsapp = f"whatsapp:{cleaned_number}"
        else:
            to_whatsapp = cleaned_number

        # Compose official emergency broadcast message
        message_body = (
            f"🚨 PRAVAH EMERGENCY ALERT: High flood probability ({prob_pct}%) "
            f"detected for {catchment_name}. Immediate evacuation recommended. "
            f"Please stay safe, avoid low-lying riparian areas, and follow official SDRF directives."
        )

        # SIH Live Demo Sandbox Fallback (when credentials are unconfigured)
        is_demo_mode = (
            TWILIO_ACCOUNT_SID == "YOUR_TWILIO_ACCOUNT_SID"
            or not TWILIO_ACCOUNT_SID
            or TWILIO_ACCOUNT_SID.startswith("YOUR_")
        )
        if is_demo_mode:
            simulated_sid = f"SM_DEMO_SANDBOX_{abs(hash(cleaned_number + catchment_name)) % 1000000:06d}"
            logger.info(
                "📢 [DEMO SIMULATION] WhatsApp alert simulated for %s (%s, %d%% risk). Simulated SID: %s",
                to_whatsapp,
                catchment_name,
                prob_pct,
                simulated_sid,
            )
            return simulated_sid

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=to_whatsapp,
            body=message_body,
        )

        logger.info(
            "WhatsApp emergency alert sent to %s for %s (Message SID: %s)",
            to_whatsapp,
            catchment_name,
            message.sid,
        )
        return message.sid

    except TwilioRestException as exc:
        logger.error("Twilio API error sending alert to %s: %s", phone_number, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error in trigger_emergency_alert: %s", exc)
        return None


# -----------------------------------------------------------------------------
# Non-Blocking Asynchronous Twilio Dispatcher (SRE / Fast-Fail Patch)
# -----------------------------------------------------------------------------
import asyncio
from typing import List, Dict, Any

async def async_trigger_emergency_alert(
    phone_number: str,
    catchment_name: str,
    probability: float,
    timeout_secs: float = 4.0,
) -> Optional[str]:
    """
    Asynchronous, non-blocking wrapper around trigger_emergency_alert.
    Runs the blocking network I/O in a separate thread pool with a hard timeout
    to prevent Twilio latency spikes from stalling the FastAPI event loop.
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                trigger_emergency_alert,
                phone_number=phone_number,
                catchment_name=catchment_name,
                probability=probability,
            ),
            timeout=timeout_secs,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Twilio alert request timed out after %.1fs for %s. Bypassed to preserve event loop.",
            timeout_secs,
            phone_number,
        )
        return None
    except Exception as exc:
        logger.error("Async alert dispatch error for %s: %s", phone_number, exc)
        return None


async def batch_dispatch_emergency_alerts(
    subscribers: List[Dict[str, Any]],
    catchment_name: str,
    probability: float,
) -> int:
    """
    Concurrently dispatches emergency WhatsApp alerts to all matching subscribers
    using asyncio.gather, ensuring instantaneous broadcast without blocking.
    """
    if not subscribers:
        return 0

    tasks = [
        async_trigger_emergency_alert(
            phone_number=sub.get("phone_number") or sub.get("phone", ""),
            catchment_name=catchment_name,
            probability=probability,
        )
        for sub in subscribers
        if sub.get("phone_number") or sub.get("phone")
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if isinstance(r, str) and r)
    logger.info(
        "Dispatched %d/%d emergency WhatsApp alerts for %s",
        success_count,
        len(tasks),
        catchment_name,
    )
    return success_count

