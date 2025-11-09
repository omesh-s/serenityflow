# Serenity Backend

FastAPI backend for Serenity Flow application that integrates with Google Calendar, Notion, Gemini, and Eleven Labs APIs.

## Setup

### Prerequisites
- Python 3.8 or higher
- pip

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

5. Fill in your API keys and OAuth credentials in the `.env` file:

   **Google OAuth:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable Google Calendar API
   - Create OAuth 2.0 credentials (Web application)
   - Add `http://localhost:8000/auth/google/callback` as an authorized redirect URI
   - Copy Client ID and Client Secret to `.env`

   **Notion OAuth:**
   - Go to [Notion Integrations](https://www.notion.so/my-integrations)
   - Create a new integration
   - Copy the OAuth client ID and secret
   - Set redirect URI to `http://localhost:8000/auth/notion/callback`
   - Add the integration to your Notion workspace

   **Gemini API Key:**
   - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Copy the API key to `.env`

   **Eleven Labs API Key:**
   - Get from [Eleven Labs](https://elevenlabs.io/)
   - Copy the API key to `.env`

6. Run the server:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
API documentation will be available at `http://localhost:8000/docs`

## API Endpoints

### Authentication
- `GET /auth/google` - Initiate Google OAuth flow
  - Returns: `{ "authorization_url": "...", "state": "..." }`
- `GET /auth/google/callback` - Google OAuth callback (handled automatically)
- `GET /auth/notion` - Initiate Notion OAuth flow
  - Returns: `{ "authorization_url": "..." }`
- `GET /auth/notion/callback` - Notion OAuth callback (handled automatically)
- `GET /auth/status` - Check OAuth connection status
  - Returns: `{ "google": {"connected": true}, "notion": {"connected": false} }`
- `POST /auth/disconnect/{service}` - Disconnect a service (google or notion)

### Serenity
- `GET /api/serenity/schedule` - Get schedule with break suggestions and wellness metrics
  - Query parameters:
    - `max_events` (default: 10) - Maximum number of calendar events
    - `max_pages` (default: 10) - Maximum number of Notion pages (wellness analysis uses up to 50)
  - Returns:
    ```json
    {
      "events": [...],
      "pages": [...],
      "break_suggestions": [
        {
          "time": "2024-01-15T10:30:00",
          "duration": 10,
          "activity": "meditation",
          "reason": "Gap between back-to-back meetings"
        }
      ],
      "wellness_metrics": {
        "wellness_score": 75.5,
        "completion_rate": 65.0,
        "peak_productivity_hours": "10:00 AM - 12:00 PM",
        "insights": ["High completion rate (65%) - Great productivity!"]
      }
    }
    ```

### Wellness
- `GET /api/wellness` - Get wellness analytics from Notion notes
  - Query parameters:
    - `max_notes` (default: 50) - Maximum number of notes to analyze
  - Returns:
    ```json
    {
      "wellness_score": 75.5,
      "completion_rate": 65.0,
      "peak_productivity_hours": "10:00 AM - 12:00 PM",
      "insights": [
        "High completion rate (65%) - Great productivity!",
        "Peak productivity hours: 10 AM - 12 PM"
      ],
      "total_notes": 25,
      "analyzed_notes": 25
    }
    ```

### Health Check
- `GET /api/health` - Health check endpoint
- `GET /` - Root endpoint with API information

## Database

The application uses SQLite by default to store OAuth tokens. The database file (`serenity.db`) will be created automatically on first run in the `backend` directory.

## CORS

CORS is configured to allow requests from `http://localhost:3000` (the frontend development server).

## Environment Variables

See `.env.example` for all required environment variables. Make sure to set:
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- `NOTION_CLIENT_ID` and `NOTION_CLIENT_SECRET`
- `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY` (optional, for future use)
- `SECRET_KEY` (change in production)

## Development

The server runs with auto-reload enabled when using `uvicorn --reload`. This means changes to Python files will automatically restart the server.

## Troubleshooting

1. **OAuth redirect URI mismatch**: Make sure the redirect URIs in your OAuth app settings match exactly with the ones in `.env`
2. **Database errors**: Delete `serenity.db` and restart the server to recreate the database
3. **Import errors**: Make sure you're in the `backend` directory and have activated your virtual environment
4. **API key errors**: Verify all API keys are correctly set in `.env` file

