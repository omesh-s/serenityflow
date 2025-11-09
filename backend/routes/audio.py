"""Audio routes for serving sound files from public folder."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pathlib import Path
import os

router = APIRouter()

# Path to public folder (parent directory's public folder)
# backend/routes/audio.py -> backend -> root -> public
BASE_DIR = Path(__file__).parent.parent.parent
PUBLIC_DIR = BASE_DIR / "public"

# Ensure public directory exists
if not PUBLIC_DIR.exists():
    # Try alternative path (if running from different location)
    PUBLIC_DIR = Path(__file__).parent.parent.parent.parent / "public"

# Theme to sound file mapping
THEME_SOUND_MAP = {
    'forest': 'forest.mp3',
    'rain': 'gentlerain.mp3',
    'ocean': 'oceanwaves.mp3',
    'wind': 'windchimes.mp3',
}


@router.get("/preview/{theme_id}")
async def get_sound_preview(theme_id: str):
    """Get sound preview file for a theme from public folder."""
    try:
        # Get sound file name for theme
        sound_file = THEME_SOUND_MAP.get(theme_id, 'oceanwaves.mp3')
        sound_path = PUBLIC_DIR / sound_file
        
        if not sound_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Sound file not found: {sound_file}"
            )
        
        # Determine media type based on file extension
        media_type = "audio/mpeg" if sound_file.endswith('.mp3') else "audio/wav"
        
        return FileResponse(
            sound_path,
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename={sound_file}",
                "Cache-Control": "public, max-age=3600"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error serving sound preview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error serving sound preview: {str(e)}"
        )


@router.get("/chime/{theme_id}")
async def get_theme_chime(theme_id: str):
    """Get a short chime sound for theme selection feedback."""
    try:
        # Use the same sound file as preview, but play a short clip
        # For now, just return the full file - frontend can handle clipping if needed
        sound_file = THEME_SOUND_MAP.get(theme_id, 'oceanwaves.mp3')
        sound_path = PUBLIC_DIR / sound_file
        
        if not sound_path.exists():
            return Response(
                content=b'',
                media_type="audio/mpeg",
                headers={"Cache-Control": "no-cache"}
            )
        
        media_type = "audio/mpeg" if sound_file.endswith('.mp3') else "audio/wav"
        
        return FileResponse(
            sound_path,
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename={theme_id}_chime.mp3",
                "Cache-Control": "public, max-age=3600"
            }
        )
    except Exception as e:
        print(f"Error serving chime: {str(e)}")
        return Response(
            content=b'',
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache"}
        )


@router.get("/theme/{theme_id}")
async def get_theme_sound(theme_id: str):
    """Get the main theme sound file for background playback."""
    try:
        sound_file = THEME_SOUND_MAP.get(theme_id, 'oceanwaves.mp3')
        sound_path = PUBLIC_DIR / sound_file
        
        if not sound_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Sound file not found: {sound_file}"
            )
        
        media_type = "audio/mpeg" if sound_file.endswith('.mp3') else "audio/wav"
        
        return FileResponse(
            sound_path,
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename={sound_file}",
                "Cache-Control": "public, max-age=86400"  # Cache for 24 hours
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error serving theme sound: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error serving theme sound: {str(e)}"
        )


@router.get("/event/{event_type}")
async def get_event_sound(event_type: str):
    """Get event sound files (startup, error, accept)."""
    try:
        event_sound_map = {
            'startup': 'startup_sound.wav',
            'error': 'error_sound.wav',
            'accept': 'accept_sound.wav',
        }
        
        sound_file = event_sound_map.get(event_type)
        if not sound_file:
            raise HTTPException(
                status_code=404,
                detail=f"Event sound not found: {event_type}"
            )
        
        sound_path = PUBLIC_DIR / sound_file
        
        if not sound_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Sound file not found: {sound_file}"
            )
        
        media_type = "audio/wav" if sound_file.endswith('.wav') else "audio/mpeg"
        
        return FileResponse(
            sound_path,
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename={sound_file}",
                "Cache-Control": "public, max-age=86400"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error serving event sound: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error serving event sound: {str(e)}"
        )

