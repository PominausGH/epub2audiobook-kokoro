# Docker Self-Hosted Release Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a polished, self-hosted epub2audiobook with multi-user auth, queue-based conversion, Kokoro TTS, and Docker-first deployment within 3-4 weeks.

**Target Audience:** Technical users running self-hosted services (NAS, VPS, homelab)

**Distribution:** GitHub releases + Docker Hub + awesome-selfhosted listings

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Container                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │   Gunicorn  │───▶│  Flask App  │───▶│  SQLite (users) │ │
│  │  (WSGI)     │    │  + Tailwind │    │  + jobs queue   │ │
│  └─────────────┘    └──────┬──────┘    └─────────────────┘ │
│                            │                                 │
│                     ┌──────▼──────┐                         │
│                     │ Job Queue   │                         │
│                     │ (1 at time) │                         │
│                     └──────┬──────┘                         │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│  ┌────────────┐    ┌─────────────┐    ┌────────────┐       │
│  │ EPubParser │───▶│ Kokoro TTS  │───▶│ M4BCreator │       │
│  └────────────┘    │ (default)   │    └────────────┘       │
│                    │ + pyttsx3   │                          │
│                    └─────────────┘                          │
├─────────────────────────────────────────────────────────────┤
│  Volumes: /data/uploads  /data/output  /data/db             │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

SQLite database at `/data/db/epub2audiobook.db`:

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Jobs queue
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,  -- UUID
    user_id INTEGER REFERENCES users(id),
    status TEXT DEFAULT 'queued',  -- queued, processing, completed, failed
    epub_filename TEXT NOT NULL,
    epub_path TEXT NOT NULL,
    output_path TEXT,
    voice_id TEXT,
    speed INTEGER DEFAULT 150,
    error_message TEXT,
    progress INTEGER DEFAULT 0,  -- 0-100
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Sessions (Flask-Login compatible)
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
```

### Authentication

- First user to register becomes admin
- Admin can enable/disable registration via settings
- Password hashing with `werkzeug.security` (bcrypt-based)
- Session cookies with configurable expiry (default 7 days)
- Environment variable `ADMIN_PASSWORD` for initial admin setup

---

## Job Queue System

Single background worker thread processes jobs sequentially:

```python
class ConversionWorker(threading.Thread):
    def run(self):
        while True:
            job = db.get_next_queued_job()  # ORDER BY created_at ASC LIMIT 1
            if job:
                self.process_job(job)
            else:
                time.sleep(2)  # Poll interval
```

### Job Lifecycle

```
Upload ePub → queued → processing → completed
                 │           │
                 │           └──→ failed (with error_message)
                 │
                 └──→ cancelled (user can cancel while queued)
```

### Resource Management

- Temp files cleaned up on job completion/failure
- Old completed jobs auto-deleted after 7 days (configurable)
- Output files kept until user deletes or storage limit hit
- Per-user storage limit: 5GB default (env configurable)

### Graceful Shutdown

- SIGTERM triggers graceful stop
- Current job completes before exit
- Job marked "queued" again if killed mid-process
- Docker stop timeout: 300s (5 min for long chapters)

---

## Web Frontend

### Routes

| Route | Description |
|-------|-------------|
| `/` | Landing - login or redirect to dashboard |
| `/login` | Login form |
| `/register` | Registration (if enabled) |
| `/dashboard` | User's jobs list + upload form |
| `/convert` | Conversion settings (voice, speed) after upload |
| `/jobs/<id>` | Job detail with progress |
| `/admin` | Admin panel (users, queue, settings) |

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  📚 epub2audiobook                    [Username ▼] [Logout] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📁 Drop ePub here or click to browse               │   │
│  │     ─────────────────────────────────────           │   │
│  │     Supported: .epub files up to 100MB              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Your Conversions                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📖 The Great Gatsby    ✅ Completed    [Download]   │   │
│  │ 📖 1984                ⏳ Processing   63%  ████░░  │   │
│  │ 📖 Dune                🕐 Queued       #2 in queue  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

- Jinja2 templates with Tailwind CSS (CDN)
- Alpine.js for interactivity (dropzone, progress polling, modals)
- No build step - keeps Docker image simple
- Responsive design - works on mobile

### Real-time Updates

- Polling-based (not WebSocket) - simpler, works behind proxies
- `/api/jobs/<id>/status` returns current progress
- Frontend polls every 2 seconds during active conversion
- Shows queue position for waiting jobs ("3rd in queue")

---

## Structured Logging

### Format (JSON lines)

```json
{"ts":"2026-01-14T10:23:45Z","level":"INFO","msg":"Job started","job_id":"abc123","user":"john","epub":"gatsby.epub"}
{"ts":"2026-01-14T10:24:12Z","level":"INFO","msg":"Chapter synthesized","job_id":"abc123","chapter":3,"of":12,"duration_s":45.2}
{"ts":"2026-01-14T10:25:01Z","level":"ERROR","msg":"TTS failed","job_id":"abc123","error":"Kokoro timeout","retry":1}
```

### Log Levels

| Level | Use |
|-------|-----|
| DEBUG | TTS chunk details, file operations |
| INFO | Job lifecycle, user actions, startup |
| WARNING | Fallback to pyttsx3, retries, low disk |
| ERROR | Job failures, auth failures, exceptions |

### Configuration

- `LOG_LEVEL=INFO` (default)
- `LOG_FORMAT=json` or `text` (text for local dev)
- Logs to stdout (Docker captures automatically)

---

## Kokoro TTS Integration

### Engine Priority

1. **Kokoro** (default) - Neural TTS, high quality, 24 voices
2. **pyttsx3** (fallback) - If Kokoro fails or user prefers system voices

### Voice Selection UI

```
┌─────────────────────────────────────┐
│ Voice                           ▼   │
├─────────────────────────────────────┤
│ ★ NEURAL VOICES (Kokoro)            │
│   ♀ Heart (American)                │
│   ♀ Bella (American)                │
│   ♂ Adam (American)                 │
│   ♂ Michael (American)              │
│   ♀ Alice (British)                 │
│   ♂ George (British)                │
│   ... 18 more                       │
├─────────────────────────────────────┤
│   SYSTEM VOICES                     │
│   ♂ espeak-ng (English)             │
│   ... others if available           │
└─────────────────────────────────────┘
```

### Docker Image

```dockerfile
# Additional dependencies for Kokoro
RUN pip install kokoro>=0.9.4 soundfile numpy

# espeak-ng still needed (Kokoro uses it for phonemization)
RUN apt-get install -y espeak-ng
```

### Image Size

- Current: ~800MB
- With Kokoro: ~1.5GB (adds PyTorch)
- Model: ~200MB (downloaded on first use, cached in volume)

### Model Caching

```yaml
volumes:
  - kokoro_cache:/home/appuser/.cache/huggingface
```

---

## Deployment

### Docker Hub

```bash
docker run -d \
  -p 5000:5000 \
  -v epub2audiobook_data:/data \
  -e ADMIN_PASSWORD=changeme \
  yourusername/epub2audiobook:latest
```

### Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Current stable release |
| `1.0.0` | Semantic version |
| `1.0` | Minor version (latest patch) |
| `slim` | Future: pyttsx3 only, smaller image |

### GitHub Releases

Each release includes:
- `docker-compose.yml`
- `epub2audiobook-linux-x64.tar.gz`
- `epub2audiobook-windows-x64.zip`
- `epub2audiobook-macos-arm64.tar.gz`
- `CHANGELOG.md`

### Marketplace Listings

- awesome-selfhosted (Media/Books section)
- selfh.st
- alternativeto.net
- r/selfhosted launch post

---

## Implementation Roadmap

### Week 1: Foundation

| Task | Days |
|------|------|
| Implement Kokoro TTS engine (from kokoro-tts-engine.md) | 2 |
| Create SQLite models (users, jobs, sessions) | 1 |
| Build auth system (register, login, sessions) | 1 |
| Job queue worker with persistence | 1 |

### Week 2: Web Frontend

| Task | Days |
|------|------|
| Tailwind templates (login, register, dashboard) | 2 |
| Conversion page (voice picker, settings) | 1 |
| Job progress page with polling | 1 |
| Admin panel (users, queue management) | 1 |

### Week 3: Polish & Testing

| Task | Days |
|------|------|
| Structured logging throughout | 0.5 |
| Test suite (auth, queue, conversion) | 2 |
| Error handling & edge cases | 1 |
| Docker optimization | 0.5 |
| Documentation updates | 1 |

### Week 4: Release Prep

| Task | Days |
|------|------|
| CI/CD pipeline (GitHub Actions) | 1 |
| Build release binaries | 1 |
| Docker Hub setup & push | 0.5 |
| CHANGELOG, README updates | 0.5 |
| Marketplace submissions | 1 |
| Buffer for fixes | 1 |

### Milestones

- **End of Week 1:** Working backend with Kokoro + queue
- **End of Week 2:** Usable web interface
- **End of Week 3:** Tested and stable
- **End of Week 4:** Released and listed

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (required) | Flask session secret |
| `ADMIN_PASSWORD` | (required) | Initial admin password |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | `json` or `text` |
| `MAX_UPLOAD_MB` | `100` | Max ePub file size |
| `USER_STORAGE_GB` | `5` | Per-user storage limit |
| `JOB_RETENTION_DAYS` | `7` | Auto-delete old jobs |
| `REGISTRATION_ENABLED` | `true` | Allow new registrations |

---

## Success Criteria

1. One-command Docker deployment works
2. Multi-user auth with admin controls
3. Queue processes jobs reliably
4. Kokoro produces quality audio
5. Web UI is clean and responsive
6. Listed on awesome-selfhosted
7. 10+ GitHub stars in first month
