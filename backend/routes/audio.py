"""Audio routes for generating sound previews using ElevenLabs."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from config import settings
from io import BytesIO
import base64

router = APIRouter()

# Try to import elevenlabs, but make it optional
try:
    import elevenlabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    print("Warning: elevenlabs not installed. Audio previews will not work.")


@router.get("/preview/{theme_id}")
async def get_sound_preview(theme_id: str):
    """Generate a short sound preview for a theme using ElevenLabs."""
    try:
        if not settings.elevenlabs_api_key:
            raise HTTPException(
                status_code=500,
                detail="ElevenLabs API key not configured"
            )
        
        # Theme-specific preview texts
        theme_previews = {
            'ocean': 'gentle ocean waves crashing softly on the shore',
            'forest': 'peaceful forest with birds chirping and leaves rustling',
            'rain': 'gentle rain falling softly on leaves',
            'wind': 'delicate wind chimes tinkling in a gentle breeze',
        }
        
        preview_text = theme_previews.get(theme_id, theme_previews['ocean'])
        
        # Configure ElevenLabs
        elevenlabs.set_api_key(settings.elevenlabs_api_key)
        
        # Generate audio using text-to-speech with ambient sound description
        # Note: ElevenLabs TTS may not generate ambient sounds directly,
        # but we can create a brief descriptive text that sounds calming
        # For true ambient sounds, you'd need ElevenLabs' sound generation API if available
        
        # Try to generate a short ambient-like audio
        # Using a calm voice with the ambient description
        try:
            audio = elevenlabs.generate(
                text=f"*{preview_text}*",  # Emphasis on the ambient description
                voice="Rachel",  # Use a calm, clear voice
                model="eleven_multilingual_v2"
            )
            
            # Return audio as streaming response
            return StreamingResponse(
                BytesIO(audio),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"inline; filename={theme_id}_preview.mp3"
                }
            )
        except Exception as e:
            # Fallback: Return a simple chime-like text
            # For better results, you might want to use pre-recorded samples
            # or a dedicated sound generation service
            print(f"Error generating audio with ElevenLabs: {str(e)}")
            
            # Return error or use fallback
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate audio preview: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in audio preview generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating sound preview: {str(e)}"
        )


@router.get("/chime/{theme_id}")
async def get_theme_chime(theme_id: str):
    """Generate a short chime sound for theme selection feedback."""
    try:
        if not ELEVENLABS_AVAILABLE or not settings.elevenlabs_api_key:
            # Return a minimal silent audio response if ElevenLabs is not available
            # In production, you might want to use pre-recorded audio files
            return Response(
                content=b'',
                media_type="audio/mpeg",
                headers={"Cache-Control": "no-cache"}
            )
        
        # Try to use ElevenLabs sound effects API if available, otherwise use TTS
        # For theme chimes, we want very brief, pleasant sounds
        try:
            # Check if sound effects API is available (newer ElevenLabs feature)
            # For now, use TTS with very short, chime-like text
            chime_texts = {
                'ocean': 'ah',  # Very brief sound for chime effect
                'forest': 'mm',
                'rain': 'sh',
                'wind': 'oh',
            }
            
            chime_text = chime_texts.get(theme_id, 'ah')
            
            elevenlabs.set_api_key(settings.elevenlabs_api_key)
            
            # Generate a very short audio clip
            # Using minimal text to create a quick chime-like sound
            audio = elevenlabs.generate(
                text=chime_text,
                voice="Rachel",  # Calm, soft voice
                model="eleven_multilingual_v2"
            )
            
            return StreamingResponse(
                BytesIO(audio),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"inline; filename={theme_id}_chime.mp3",
                    "Cache-Control": "public, max-age=3600"
                }
            )
        except Exception as e:
            print(f"Error generating chime with ElevenLabs: {str(e)}")
            # Return empty response if generation fails
            # In production, fallback to pre-recorded chime sounds
            return Response(
                content=b'',
                media_type="audio/mpeg",
                headers={"Cache-Control": "no-cache"}
            )
            
    except Exception as e:
        print(f"Error in chime generation: {str(e)}")
        # Return empty response on error (frontend will handle gracefully)
        return Response(
            content=b'',
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache"}
        )

