import os
import uuid
import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request as FastAPIRequest, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from pydantic import BaseModel

from app.db import crud
from app.deps.auth import CurrentUser, get_current_user
from app.db.session import get_db
from app.db.models import GoogleCalendarToken, GoogleEventSync

# We assume pip install google-auth-oauthlib has finished
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

router = APIRouter(prefix="/calendar", tags=["calendar"])

# Store PKCE code verifiers in-memory linked to the state (user_id) for the OAuth flow
oauth_verifiers: dict[str, str] = {}

class EventOut(BaseModel):
    id: str | int
    title: str
    start_datetime: str
    end_datetime: str
    description: str | None = None
    type: str | None = "study"

def get_user_events(db: Session, user_uuid: uuid.UUID) -> list[dict]:
    plans = crud.list_study_plans(db=db, user_id=user_uuid)
    events = []
    
    for plan in plans:
        schedule = plan.plan_json.get("schedule", [])
        start_date = plan.created_at
        title_prefix = plan.plan_json.get("title", "Study Plan")
        
        for idx, day_plan in enumerate(schedule):
            # Place study sessions at 10 AM on consecutive days
            event_date = start_date + timedelta(days=idx)
            event_start = event_date.replace(hour=10, minute=0, second=0, microsecond=0)
            event_end = event_start + timedelta(hours=2)
            
            tasks_list = day_plan.get("tasks", [])
            desc = "• " + "\n• ".join(tasks_list) if tasks_list else "Study block"
            
            events.append({
                "id": f"{plan.id}_day_{idx}",
                "title": f"{title_prefix}: {day_plan.get('day', f'Day {idx+1}')}",
                "start_datetime": event_start.isoformat(),
                "end_datetime": event_end.isoformat(),
                "description": desc,
                "type": "study"
            })
            
    return events

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_flow(state: str = None):
    # Allow local HTTP traffic for OAuth
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    # Fallback to mock config if no env vars present
    client_config = {
        "web": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", "mock_client"),
            "project_id": "gradepilot",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", "mock_secret")
        }
    }
    
    flow = Flow.from_client_config(
        client_config, 
        scopes=SCOPES, 
        state=state
    )
    # Redirect URI must exactly match the callback route
    flow.redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/calendar/callback")
    return flow

@router.get("/events", response_model=list[EventOut])
def get_events(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user.user_id)
        return get_user_events(db, user_uuid)
    except Exception as e:
        print(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve events")

@router.post("/sync")
def sync_events(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user.user_id)
        token_record = db.query(GoogleCalendarToken).filter(GoogleCalendarToken.user_id == user_uuid).first()
        
        if not token_record:
            raise HTTPException(status_code=400, detail="Calendar not connected")

        creds = Credentials(
            token=token_record.access_token,
            refresh_token=token_record.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get("GOOGLE_CLIENT_ID", "mock_client"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "mock_secret"),
            expiry=token_record.expiry.replace(tzinfo=None) if token_record.expiry else None
        )

        if creds.expired and creds.refresh_token:
            if os.environ.get("GOOGLE_CLIENT_ID") is not None:
                creds.refresh(Request())
                token_record.access_token = creds.token
                if creds.expiry:
                    token_record.expiry = creds.expiry.replace(tzinfo=timezone.utc)
                db.commit()

        # Build Google Calendar client, bypassing discovery cache issues if any
        service = build('calendar', 'v3', credentials=creds, cache_discovery=False)

        real_events = get_user_events(db, user_uuid)

        for app_event in real_events:
            body = {
                "summary": app_event["title"],
                "description": app_event["description"],
                "start": {
                    "dateTime": app_event["start_datetime"],
                },
                "end": {
                    "dateTime": app_event["end_datetime"],
                }
            }
            
            if os.environ.get("GOOGLE_CLIENT_ID") is None:
                print(f"Mock push event to Google: {body['summary']}")
                continue
                
            app_evt_id_str = str(app_event["id"])
            mapping = db.query(GoogleEventSync).filter_by(
                user_id=user_uuid, 
                app_event_id=app_evt_id_str
            ).first()

            if mapping:
                try:
                    service.events().update(
                        calendarId="primary", 
                        eventId=mapping.google_event_id, 
                        body=body
                    ).execute()
                except Exception as e:
                    print(f"Failed to update existing event -> {str(e)}")
            else:
                res = service.events().insert(
                    calendarId="primary", 
                    body=body
                ).execute()
                
                new_mapping = GoogleEventSync(
                    user_id=user_uuid,
                    app_event_id=app_evt_id_str,
                    google_event_id=res["id"]
                )
                db.add(new_mapping)

        db.commit()
        return {"status": "synced"}
    except Exception as e:
        db.rollback()
        print(f"Calendar sync error: {str(e)}")
        raise HTTPException(status_code=500, detail="Calendar synchronization failed")

@router.get("/connect")
def connect_calendar(user: CurrentUser = Depends(get_current_user)):
    # We use the user.user_id as the state so we know who to bound the token to in the callback
    # Warning: this exposes the user_id in the oauth callback, but it's acceptable for this prototype
    flow = get_flow(state=user.user_id)
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Track the PKCE challenge securely in memory for the callback to use
    oauth_verifiers[user.user_id] = flow.code_verifier
    
    return JSONResponse({"url": authorization_url})

@router.get("/callback")
def calendar_callback(request: FastAPIRequest, state: str, code: str, db: Session = Depends(get_db)):
    # Verify we got standard params
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing auth code or state")

    google_code_verifier = oauth_verifiers.get(state)

    try:
        user_uuid = uuid.UUID(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state")
        
    try:
        flow = get_flow(state=state)
        # We need the full URL from the request to fetch the token
        # but because of proxies we construct it.
        # Use a mock token set for testing since we might not have real credentials
        if os.environ.get("GOOGLE_CLIENT_ID") is None:
            # Local mock behaviour
            mock_access = "mock-access-token"
            mock_refresh = "mock-refresh-token"
            expiry = None
        else:
            # We'd fetch using real flow. We force https scheme so oauthlib doesn't throw insecure_transport
            auth_response = str(request.url).replace('http://', 'https://')
            flow.fetch_token(
                authorization_response=auth_response,
                code_verifier=google_code_verifier
            )
            creds = flow.credentials
            mock_access = creds.token
            mock_refresh = creds.refresh_token
            expiry = creds.expiry

        # Upsert the token
        stmt = insert(GoogleCalendarToken).values(
            user_id=user_uuid,
            access_token=mock_access,
            refresh_token=mock_refresh,
            expiry=expiry
        )
        
        # Postgres UPSERT
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id'],
            set_={
                'access_token': stmt.excluded.access_token,
                'refresh_token': stmt.excluded.refresh_token,
                'expiry': stmt.excluded.expiry
            }
        )
        db.execute(stmt)
        db.commit()

        # Redirect user back to the application calendar
        return RedirectResponse("http://localhost:3000/dashboard/calendar")
        
    except Exception as e:
        db.rollback()
        print(f"Calendar auth error: {str(e)}")
        raise HTTPException(status_code=500, detail="Calendar authentication failed")

@router.get("/status")
def calendar_status(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user.user_id)
        token = db.query(GoogleCalendarToken).filter(GoogleCalendarToken.user_id == user_uuid).first()
        return {"connected": token is not None}
    except Exception:
        return {"connected": False}

