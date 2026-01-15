"""
ePub to Audiobook - Web Application
Flask-based web interface with authentication.
"""

import os
import sys
import threading
import shutil
from pathlib import Path
from datetime import timedelta

from flask import (
    Flask, render_template, request, jsonify, send_file,
    redirect, url_for, flash, session
)
from werkzeug.utils import secure_filename

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import EPubParser, TextCleaner, CleanerOptions
from tts import TTSEngine, TTSConfig
from audio import AudioProcessor, M4BCreator, AudiobookMetadata, AudioFormat

from .database import (
    init_db, create_user, verify_user, get_user_by_username,
    create_job, get_job, get_user_jobs, get_next_queued_job,
    update_job, update_job_status, delete_job, get_queue_position
)
from .auth import get_current_user, login_user, logout_user, login_required

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/data/uploads')
app.config['OUTPUT_FOLDER'] = os.environ.get('OUTPUT_FOLDER', '/data/output')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize database
init_db()

# Background worker
worker_thread = None
worker_running = False


def get_tts_engine():
    """Get initialized TTS engine."""
    engine = TTSEngine()
    engine.initialize()
    return engine


# Auth routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if get_current_user():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = verify_user(username, password)
        if user:
            login_user(user)
            next_url = request.args.get('next', url_for('dashboard'))
            return redirect(next_url)
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page."""
    if get_current_user():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        errors = []
        if len(username) < 3:
            errors.append('Username must be at least 3 characters')
        if '@' not in email:
            errors.append('Invalid email address')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters')
        if password != confirm:
            errors.append('Passwords do not match')
        if get_user_by_username(username):
            errors.append('Username already taken')

        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            user = create_user(username, email, password)
            if user:
                login_user(user)
                flash('Account created! You are now logged in.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Failed to create account', 'error')

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Logout."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


# Main routes

@app.route('/')
def index():
    """Home - redirect to dashboard or login."""
    if get_current_user():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with jobs list."""
    user = get_current_user()
    jobs = get_user_jobs(user.id)

    # Add queue position for queued jobs
    jobs_data = []
    for job in jobs:
        job_dict = {
            'id': job.id,
            'title': job.title or job.epub_filename,
            'author': job.author,
            'status': job.status,
            'progress': job.progress,
            'created_at': job.created_at,
            'error_message': job.error_message,
        }
        if job.status == 'queued':
            job_dict['queue_position'] = get_queue_position(job.id)
        jobs_data.append(job_dict)

    return render_template('dashboard.html', user=user, jobs=jobs_data)


@app.route('/api/voices')
@login_required
def list_voices():
    """List available TTS voices."""
    engine = get_tts_engine()
    voices = []

    # Group by engine
    kokoro_voices = []
    system_voices = []

    for v in engine.get_voices():
        voice_data = {
            'id': v.id,
            'name': v.name,
            'gender': v.gender,
            'engine': v.engine
        }
        if v.engine == 'kokoro':
            kokoro_voices.append(voice_data)
        else:
            system_voices.append(voice_data)

    engine.cleanup()
    return jsonify({
        'kokoro_voices': kokoro_voices,
        'system_voices': system_voices,
        'engine': engine.get_engine_name()
    })


@app.route('/api/upload', methods=['POST'])
@login_required
def upload_epub():
    """Upload an ePub file and get book info."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.epub'):
        return jsonify({'error': 'File must be an ePub'}), 400

    user = get_current_user()

    # Save file with unique name
    filename = secure_filename(file.filename)
    import uuid
    file_id = str(uuid.uuid4())[:8]
    epub_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{user.id}_{file_id}_{filename}")
    file.save(epub_path)

    try:
        # Parse ePub to get info
        parser = EPubParser(epub_path)
        parser.parse()

        # Estimate duration
        duration_sec = parser.get_estimated_duration()
        hours = duration_sec // 3600
        minutes = (duration_sec % 3600) // 60

        return jsonify({
            'file_id': file_id,
            'epub_path': epub_path,
            'filename': filename,
            'title': parser.metadata.title,
            'author': parser.metadata.author,
            'chapters': len(parser.chapters),
            'word_count': parser.get_total_word_count(),
            'estimated_duration': f"{hours}h {minutes}m",
            'chapter_list': [
                {'number': ch.number, 'title': ch.title, 'words': ch.word_count}
                for ch in parser.chapters
            ]
        })

    except Exception as e:
        os.unlink(epub_path)
        return jsonify({'error': str(e)}), 400


@app.route('/api/convert', methods=['POST'])
@login_required
def start_conversion():
    """Start conversion job."""
    data = request.json
    user = get_current_user()

    epub_path = data.get('epub_path')
    if not epub_path or not os.path.exists(epub_path):
        return jsonify({'error': 'Upload not found'}), 404

    filename = os.path.basename(epub_path)
    voice_id = data.get('voice_id')
    speed = int(data.get('speed', 150))

    # Create job in database
    job = create_job(
        user_id=user.id,
        epub_filename=filename,
        epub_path=epub_path,
        voice_id=voice_id,
        speed=speed
    )

    # Ensure worker is running
    start_worker()

    return jsonify({'job_id': job.id, 'status': 'queued'})


@app.route('/api/status/<job_id>')
@login_required
def get_status(job_id):
    """Get conversion job status."""
    user = get_current_user()
    job = get_job(job_id)

    if not job or job.user_id != user.id:
        return jsonify({'error': 'Job not found'}), 404

    result = {
        'id': job.id,
        'status': job.status,
        'progress': job.progress,
        'title': job.title,
        'author': job.author,
        'chapters': job.chapters,
        'error_message': job.error_message,
    }

    if job.status == 'queued':
        result['queue_position'] = get_queue_position(job.id)

    return jsonify(result)


@app.route('/api/download/<job_id>')
@login_required
def download_file(job_id):
    """Download the converted audiobook."""
    user = get_current_user()
    job = get_job(job_id)

    if not job or job.user_id != user.id:
        return jsonify({'error': 'Job not found'}), 404

    if job.status != 'completed':
        return jsonify({'error': 'Conversion not complete'}), 400

    if not job.output_path or not os.path.exists(job.output_path):
        return jsonify({'error': 'Output file not found'}), 404

    # Determine download filename
    ext = '.m4b' if job.output_path.endswith('.m4b') else '.mp3'
    download_name = f"{job.title or 'audiobook'}{ext}"

    return send_file(
        job.output_path,
        as_attachment=True,
        download_name=download_name
    )


@app.route('/api/jobs/<job_id>', methods=['DELETE'])
@login_required
def delete_job_route(job_id):
    """Delete a job and its files."""
    user = get_current_user()
    job = get_job(job_id)

    if not job or job.user_id != user.id:
        return jsonify({'error': 'Job not found'}), 404

    # Remove files
    if job.epub_path and os.path.exists(job.epub_path):
        os.unlink(job.epub_path)
    if job.output_path and os.path.exists(job.output_path):
        os.unlink(job.output_path)

    delete_job(job_id)
    return jsonify({'status': 'deleted'})


# Background worker

def start_worker():
    """Start the background worker if not running."""
    global worker_thread, worker_running

    if worker_thread and worker_thread.is_alive():
        return

    worker_running = True
    worker_thread = threading.Thread(target=worker_loop, daemon=True)
    worker_thread.start()


def worker_loop():
    """Background worker that processes jobs."""
    global worker_running
    import time

    while worker_running:
        job = get_next_queued_job()
        if job:
            process_job(job)
        else:
            time.sleep(2)  # Poll interval


def process_job(job):
    """Process a single conversion job."""
    temp_dir = None

    try:
        update_job_status(job.id, 'processing')
        update_job(job.id, progress=5)

        # Parse ePub
        parser = EPubParser(job.epub_path)
        parser.parse()

        update_job(job.id,
                   title=parser.metadata.title,
                   author=parser.metadata.author,
                   chapters=len(parser.chapters))

        if not parser.chapters:
            raise Exception("No chapters found in ePub")

        # Initialize TTS
        update_job(job.id, progress=10)

        tts = TTSEngine()
        if not tts.initialize():
            raise Exception("Failed to initialize TTS engine")

        # Configure voice
        config = TTSConfig(rate=job.speed)
        if job.voice_id:
            config.voice_id = job.voice_id
        tts.configure(config)

        # Text cleaner
        cleaner = TextCleaner(CleanerOptions(add_chapter_announcement=True))

        # Create temp directory
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='epub2audio_')

        # Convert chapters
        chapter_files = []
        total_chapters = len(parser.chapters)

        for i, chapter in enumerate(parser.chapters):
            progress = 10 + int((i / total_chapters) * 60)
            update_job(job.id, progress=progress)

            cleaned_text = cleaner.clean(chapter.content, chapter.title)
            if not cleaned_text.strip():
                continue

            chapter_path = os.path.join(temp_dir, f"ch_{i + 1:03d}.wav")
            if tts.synthesize_chapter(cleaned_text, chapter_path):
                if os.path.exists(chapter_path):
                    chapter_files.append(chapter_path)

        if not chapter_files:
            raise Exception("No audio files were generated")

        # Merge chapters
        update_job(job.id, progress=75)

        processor = AudioProcessor(quality='medium')
        merged_path = os.path.join(temp_dir, "merged.wav")

        success, markers = processor.merge_chapters(chapter_files, merged_path, gap_ms=1500)
        if not success:
            raise Exception("Failed to merge chapters")

        # Update markers with titles
        for i, marker in enumerate(markers):
            if i < len(parser.chapters):
                marker.title = parser.chapters[i].title

        # Normalize
        update_job(job.id, progress=85)

        normalized_path = os.path.join(temp_dir, "normalized.wav")
        processor.normalize_audio(merged_path, normalized_path)

        # Create final output
        update_job(job.id, progress=90)

        output_filename = f"{job.id}_audiobook.m4b"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        creator = M4BCreator()
        meta = AudiobookMetadata(
            title=parser.metadata.title,
            author=parser.metadata.author,
            cover_image=parser.metadata.cover_image,
            cover_mime_type=parser.metadata.cover_mime_type
        )
        success = creator.create_m4b(normalized_path, output_path, markers, meta)

        if not success or not os.path.exists(output_path):
            raise Exception("Failed to create output file")

        # Done!
        update_job(job.id, progress=100, output_path=output_path)
        update_job_status(job.id, 'completed')

        # Cleanup TTS
        tts.cleanup()

    except Exception as e:
        update_job_status(job.id, 'failed', error_message=str(e))

    finally:
        # Cleanup temp files
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    start_worker()
    app.run(host='0.0.0.0', port=5000, debug=True)
