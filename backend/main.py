"""Main FastAPI application for Serenity backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routes import auth, serenity

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="Serenity API",
    description="Backend API for Serenity - Break scheduling and wellness",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# Auth routes at /auth/* to match OAuth app redirect URIs
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(serenity.router, prefix="/api/serenity", tags=["serenity"])

# Import and include wellness router
from routes import wellness
app.include_router(wellness.router, prefix="/api/wellness", tags=["wellness"])

# Import and include audio router
from routes import audio
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])

# Import and include breaks router
from routes import breaks
app.include_router(breaks.router, prefix="/api/breaks", tags=["breaks"])

# Import and include checklist router
from routes import checklist
app.include_router(checklist.router, prefix="/api/checklist", tags=["checklist"])

# Import and include automation router
from routes import automation
app.include_router(automation.router, prefix="/api/automation", tags=["automation"])

# Import and include Twilio router (server-side call initiation)
from routes import twilio
app.include_router(twilio.router, prefix="/api/twilio", tags=["twilio"])


# Initialize automation scheduler
try:
    from utils.automation_scheduler import get_scheduler
    scheduler = get_scheduler()
    print("Automation scheduler initialized")
except Exception as e:
    print(f"Warning: Could not initialize automation scheduler: {str(e)}")
    scheduler = None


@app.get("/")
async def root():
    """Root endpoint - returns API info or HTML landing page."""
    from fastapi.responses import HTMLResponse
    from fastapi import Request
    
    # Check if client accepts HTML
    # For browser requests, return HTML; for API clients, return JSON
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Serenity API</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
            }
            .version {
                color: #666;
                font-size: 14px;
                margin-bottom: 30px;
            }
            .endpoints {
                margin-top: 30px;
            }
            .endpoint {
                background: #f8f9fa;
                padding: 15px;
                margin: 10px 0;
                border-radius: 4px;
                border-left: 4px solid #4CAF50;
            }
            .endpoint strong {
                color: #4CAF50;
                font-family: monospace;
            }
            a {
                color: #4CAF50;
                text-decoration: none;
                font-weight: 600;
            }
            a:hover {
                text-decoration: underline;
            }
            .docs-link {
                display: inline-block;
                margin-top: 20px;
                padding: 12px 24px;
                background: #4CAF50;
                color: white;
                border-radius: 4px;
                text-decoration: none;
            }
            .docs-link:hover {
                background: #45a049;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌊 Serenity API</h1>
            <div class="version">Version 1.0.0 - Break scheduling and wellness API</div>
            
            <p>Welcome to the Serenity API! This backend provides integration with Google Calendar, Notion, and AI-powered break suggestions.</p>
            
            <div class="endpoints">
                <h2>Key Endpoints</h2>
                <div class="endpoint">
                    <strong>GET /auth/status</strong> - Check OAuth connection status
                </div>
                <div class="endpoint">
                    <strong>GET /api/serenity/schedule</strong> - Get schedule with break suggestions
                </div>
                <div class="endpoint">
                    <strong>GET /auth/google</strong> - Initiate Google OAuth flow
                </div>
                <div class="endpoint">
                    <strong>GET /auth/notion</strong> - Initiate Notion OAuth flow
                </div>
            </div>
            
            <a href="/docs" class="docs-link">📚 View API Documentation</a>
            
            <p style="margin-top: 30px; color: #666; font-size: 14px;">
                API is running and ready to accept requests. Use the interactive documentation above to explore all endpoints.
            </p>
        </div>
    </body>
    </html>
    """)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

