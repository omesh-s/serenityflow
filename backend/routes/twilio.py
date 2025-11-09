"""Twilio call route - server-side call initiation to avoid exposing credentials in the browser."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

try:
    from twilio.rest import Client
except Exception:
    Client = None

router = APIRouter()


class CallRequest(BaseModel):
    to: str
    message: str = "Hello from Serenity"


@router.post("/call")
async def make_call(payload: CallRequest):
    """Initiate a voice call using Twilio. Credentials must be set via environment variables:
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_NUMBER. Optionally TWILIO_ALLOWED_TO (comma-separated list).
    """
    if Client is None:
        raise HTTPException(status_code=500, detail="Twilio SDK is not installed on the server")

    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_NUMBER")
    allowed_to = os.getenv("TWILIO_ALLOWED_TO")

    if not sid or not token or not from_number:
        raise HTTPException(status_code=500, detail="Twilio credentials not configured on server")

    to = payload.to
    # If an allowed list is configured, enforce it to prevent misuse
    if allowed_to:
        allowed = [s.strip() for s in allowed_to.split(",") if s.strip()]
        if to not in allowed:
            raise HTTPException(status_code=403, detail="Destination number not allowed")

    client = Client(sid, token)
    try:
        # Use TwiML directly to speak a short message
        twiml = f"<Response><Say voice=\"alice\">{payload.message}</Say></Response>"
        call = client.calls.create(to=to, from_=from_number, twiml=twiml)
        return {"sid": call.sid, "status": call.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
