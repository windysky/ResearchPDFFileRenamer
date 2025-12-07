# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research PDF File Renamer is a web application that automatically renames academic/research PDF files using LLM-based content analysis. Users upload PDFs via drag-and-drop, the system extracts text (focusing on title, authors, abstract from first 1-2 pages), sends it to an LLM for structured filename generation, renames files, and provides automatic download.

## Architecture

### Tech Stack
- **Backend**: Python Flask (REST API)
- **Frontend**: HTML/CSS/JavaScript with drag-and-drop interface
- **Database**: SQLite (users, usage tracking)
- **PDF Processing**: pdfplumber for text extraction
- **LLM Integration**: OpenAI API (GPT-4o-mini), designed for future local LLM swap
- **Concurrency**: UUID-based session folders isolate concurrent uploads

### Core Components

```
backend/
  app.py              - Flask application factory and entry point
  config.py           - Configuration (loads APISetting.txt)
  models/
    user.py           - User model with password hashing
    usage.py          - Anonymous user usage tracking
  routes/
    auth.py           - Login, registration, logout endpoints
    admin.py          - User approval and management
    upload.py         - PDF upload and processing endpoint
  services/
    pdf_service.py    - PDF text extraction (up to abstract)
    llm_service.py    - LLM abstraction (OpenAI + Ollama stub)
    file_service.py   - File rename, zip, cleanup
  utils/
    rate_limiter.py   - Rate limiting for anonymous users

frontend/
  static/css/main.css - Styling
  static/js/upload.js - Drag-drop and upload handling
  templates/          - Jinja2 templates (base, index, login, register, admin)
```

### Key Design Decisions

1. **Concurrent Upload Isolation**: Each upload request gets a UUID-based session folder to prevent file conflicts between simultaneous users.

2. **LLM Abstraction**: `LLMService` uses provider pattern - swap between OpenAI and local LLMs by changing `LLM_PROVIDER` in config.

3. **Usage Limits**:
   - Registered (approved) users: 30 PDFs per submission
   - Anonymous: 5 PDFs per submission, max 5 submissions/year (IP + fingerprint tracking)

4. **Privacy-First**:
   - Only extracted text sent to LLM (not PDF binary)
   - Only first 1-2 pages processed (up to abstract)
   - Files deleted 30 seconds after download starts
   - No persistent storage of uploaded content

5. **Filename Format**: `AuthorLastName_Year_ShortTitle.pdf`

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (from project root)
python run.py
# or
python run.py --port 8000

# Alternative: run directly
python backend/app.py

# Access at http://localhost:5000
# Default admin: admin@example.com / admin123
```

## Configuration

API key in `APISetting.txt` (gitignored):
```
sk-proj-your-openai-key-here
```

To switch to local LLM, set environment variables:
```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3.2
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/upload | Upload PDFs, returns renamed files |
| GET | /api/limits | Get user's upload limits |
| POST | /api/auth/login | User login |
| POST | /api/auth/register | User registration |
| POST | /api/auth/logout | User logout |
| GET | /api/admin/pending | List pending users (admin) |
| POST | /api/admin/approve/:id | Approve user (admin) |
