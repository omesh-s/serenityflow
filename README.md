# Serenity Flow 🌊

**Serenity Flow** is an intelligent productivity and wellness application that automates meeting insights, manages your backlog, and helps you maintain work-life balance through smart break scheduling and wellness tracking.

## 📖 About

Serenity Flow integrates with your existing tools (Google Calendar, Notion) to:
- **Automate meeting insights** - Extract action items and stories from meeting notes
- **Manage your backlog** - Automatically organize, deduplicate, and prioritize tasks
- **Schedule intelligent breaks** - AI-powered break suggestions based on your schedule
- **Track wellness metrics** - Monitor your meeting patterns and wellness scores
- **Generate reports** - Automated release reports and stakeholder updates

## ✨ Features

### 🎯 Automation Agents
- **Story Extraction** - Automatically extract actionable items from Notion meeting notes
- **Backlog Auditing** - Identify duplicates and low-priority items
- **Stakeholder Mapping** - Track and map stakeholders from stories
- **Customer Research** - Analyze customer feedback and market trends
- **Release Reports** - Generate automated release reports
- **Meeting Insights** - Extract insights and action items from meetings
- **Sprint Planning** - Assist with sprint planning and story organization

### 🧘 Wellness & Breaks
- **Smart Break Scheduling** - AI-powered break suggestions based on your calendar
- **Wellness Tracking** - Monitor meeting patterns, engagement, and wellness scores
- **Calming Audio** - Theme-based background sounds (Forest, Rain, Ocean, Wind Chimes)
- **Break Types** - Different break types based on time available and context

### 🎨 User Experience
- **Theme System** - Multiple calming themes (Ocean Waves, Forest, Gentle Rain, Wind Chimes)
- **Sound Controls** - Mute/unmute functionality with persistent preferences
- **Real-time Notifications** - Toast notifications for actions and status updates
- **Interactive Dashboard** - Clean, modern UI with real-time updates
- **Responsive Design** - Works on desktop and mobile devices

## 🛠️ Tech Stack

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Framer Motion** - Animation library
- **React Router** - Client-side routing
- **Axios** - HTTP client

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **SQLite** - Database (default, can be configured for PostgreSQL)
- **Google Generative AI (Gemini)** - AI-powered analysis and extraction
- **Google Calendar API** - Calendar integration
- **Notion API** - Notion integration
- **Uvicorn** - ASGI server

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (v16 or higher) - [Download](https://nodejs.org/)
- **Python** (3.8 or higher) - [Download](https://www.python.org/downloads/)
- **pip** - Python package manager
- **Git** - Version control system

### Required API Keys & Credentials

You'll need to set up the following:

1. **Google Cloud Console**
   - Google OAuth Client ID and Secret
   - Google Calendar API enabled
   - Gemini API Key

2. **Notion**
   - Notion OAuth Client ID and Secret
   - Notion workspace with meeting notes

3. **Optional**
   - ElevenLabs API Key (for audio features)
   - Twilio credentials (for voice calls)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd serenityflow
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
cd backend
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

#### Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### Create Environment File

Create a `.env` file in the `backend` directory:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Notion OAuth
NOTION_CLIENT_ID=your_notion_client_id
NOTION_CLIENT_SECRET=your_notion_client_secret
NOTION_REDIRECT_URI=http://localhost:8000/auth/notion/callback

# API Keys
GEMINI_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key  # Optional

# Database
DATABASE_URL=sqlite:///./serenity.db

# Security
SECRET_KEY=change-this-to-a-secure-random-string-in-production
ALGORITHM=HS256

OAUTHLIB_RELAX_TOKEN_SCOPE=1
```

### 3. Frontend Setup

#### Install Node Dependencies

```bash
cd ..
npm install
```

## ⚙️ Configuration

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Calendar API
   - Google OAuth2 API
4. Create OAuth 2.0 credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth client ID"
   - Choose "Web application"
   - Add authorized redirect URI: `http://localhost:8000/auth/google/callback`
   - Copy the Client ID and Client Secret to your `.env` file

### Notion OAuth Setup

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name (e.g., "Serenity Flow")
4. Select capabilities:
   - Read content
   - Update content
   - Insert content
5. Copy the OAuth client ID and secret
6. Add the integration to your Notion workspace
7. Set the redirect URI to: `http://localhost:8000/auth/notion/callback`

### Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your `.env` file as `GEMINI_API_KEY`

### ElevenLabs API Key (Optional)

1. Go to [ElevenLabs](https://elevenlabs.io/)
2. Sign up for an account
3. Get your API key from the dashboard
4. Add it to your `.env` file (optional, for future audio features)

## 🏃 Running the Application

### Start Backend Server

```bash
cd backend
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

### Start Frontend Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000` (or the port shown in terminal)

## 📁 Project Structure

```
serenityflow/
├── backend/                 # FastAPI backend
│   ├── routes/             # API route handlers
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── automation.py  # Automation pipeline
│   │   ├── checklist.py   # Checklist management
│   │   ├── serenity.py    # Main Serenity features
│   │   └── wellness.py    # Wellness tracking
│   ├── utils/             # Utility functions
│   │   ├── agents/        # Automation agents
│   │   ├── gemini.py      # Gemini AI integration
│   │   ├── google_calendar.py  # Google Calendar integration
│   │   └── notion.py      # Notion integration
│   ├── database.py        # Database models
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration settings
│   └── requirements.txt  # Python dependencies
│
├── src/                   # React frontend
│   ├── components/       # React components
│   │   ├── Dashboard.jsx
│   │   ├── AutomationChecklist.jsx
│   │   ├── BreakTimeline.jsx
│   │   └── ...
│   ├── hooks/           # Custom React hooks
│   │   ├── useAuth.js
│   │   ├── useTheme.jsx
│   │   └── ...
│   └── utils/           # Utility functions
│
├── public/              # Static assets
│   ├── *.mp3           # Theme sounds
│   └── *.wav           # Event sounds
│
├── package.json         # Node.js dependencies
└── README.md           # This file
```

## 🎯 Usage

### Initial Setup

1. **Start both servers** (backend and frontend)
2. **Navigate to** `http://localhost:3000`
3. **Authenticate** with Google to connect your calendar
4. **Connect Notion** from the Settings page
5. **Start using** the automation features!

### Using Automation Agents

1. Go to the **Dashboard**
2. Scroll to the **Automation Checklist** section
3. Follow the **Quick Start Workflow**:
   - **Step 1**: Extract stories from your Notion pages
   - **Step 2**: Analyze and clean your backlog
   - **Step 3**: Monitor system health
4. Review and approve extracted items
5. Let the automation handle the rest!

### Managing Breaks

1. The system automatically suggests breaks based on your calendar
2. Click **"Take a Break"** when a break is suggested
3. Choose your preferred theme and background sound
4. The break modal will guide you through a 5-minute meditation

### Wellness Tracking

- View your **wellness metrics** on the dashboard
- Monitor **meeting patterns** and engagement scores
- Track your **break frequency** and effectiveness

## 🔧 Development

### Backend Development

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables auto-reload on file changes.

### Frontend Development

```bash
npm run dev
```

The Vite dev server supports hot module replacement (HMR).

### Building for Production

**Frontend:**
```bash
npm run build
```

**Backend:**
The backend can be deployed as-is or using a production ASGI server like Gunicorn with Uvicorn workers.


## 🔒 Security Notes

- **Never commit** your `.env` file to version control
- **Change the SECRET_KEY** in production
- **Use HTTPS** in production
- **Set up proper CORS** for your production domain
- **Use environment variables** for all sensitive data
- **Regularly rotate** API keys and OAuth credentials

## 📝 Environment Variables

See `backend/config.py` for all configuration options. Required environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | Yes |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | Yes |
| `NOTION_CLIENT_ID` | Notion OAuth Client ID | Yes |
| `NOTION_CLIENT_SECRET` | Notion OAuth Client Secret | Yes |
| `GEMINI_API_KEY` | Google Gemini API Key | Yes |
| `ELEVENLABS_API_KEY` | ElevenLabs API Key | No |
| `DATABASE_URL` | Database connection string | No (defaults to SQLite) |
| `SECRET_KEY` | Secret key for JWT tokens | Yes (change in production) |

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **Google Calendar API** - For calendar integration
- **Notion API** - For workspace integration
- **Google Gemini** - For AI-powered analysis
- **FastAPI** - For the excellent Python web framework
- **React** - For the UI framework
- **Tailwind CSS** - For the utility-first CSS framework
