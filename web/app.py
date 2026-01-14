"""
ePub to Audiobook - Web Application
Flask-based web interface for converting ePub files to audiobooks.
"""

import os
import sys
import uuid
import threading
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional

from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import EPubParser, TextCleaner, CleanerOptions
from tts import TTSEngine, TTSConfig
from audio import AudioProcessor, M4BCreator, AudiobookMetadata, AudioFormat

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
app.config['UPLOAD_FOLDER'] = '/data/uploads'
app.config['OUTPUT_FOLDER'] = '/data/output'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Store conversion jobs
jobs = {}


@dataclass
class ConversionJob:
    """Tracks a conversion job."""
    id: str
    epub_path: str
    output_path: str
    status: str  # pending, processing, complete, error
    progress: int  # 0-100
    message: str
    title: str = ""
    author: str = ""
    chapters: int = 0
    created_at: str = ""
    error: str = ""

    def to_dict(self):
        return asdict(self)


def get_tts_engine():
    """Get initialized TTS engine."""
    engine = TTSEngine()
    engine.initialize()
    return engine


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/voices')
def list_voices():
    """List available TTS voices."""
    engine = get_tts_engine()
    voices = []
    for v in engine.get_voices():
        voices.append({
            'id': v.id,
            'name': v.name,
            'gender': v.gender
        })
    engine.cleanup()
    return jsonify({'voices': voices, 'engine': engine.get_engine_name()})


@app.route('/api/upload', methods=['POST'])
def upload_epub():
    """Upload an ePub file and get book info."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.epub'):
        return jsonify({'error': 'File must be an ePub'}), 400

    # Save file with unique name
    job_id = str(uuid.uuid4())[:8]
    filename = secure_filename(file.filename)
    epub_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
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
            'job_id': job_id,
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
def start_conversion():
    """Start conversion job."""
    data = request.json

    job_id = data.get('job_id')
    if not job_id:
        return jsonify({'error': 'Missing job_id'}), 400

    # Find the uploaded file
    upload_dir = Path(app.config['UPLOAD_FOLDER'])
    epub_files = list(upload_dir.glob(f"{job_id}_*.epub"))
    if not epub_files:
        return jsonify({'error': 'Upload not found'}), 404

    epub_path = str(epub_files[0])

    # Get settings
    voice_id = data.get('voice_id')
    speed = int(data.get('speed', 150))
    output_format = data.get('format', 'm4b')

    # Determine output path
    output_ext = '.m4b' if output_format == 'm4b' else '.mp3'
    output_filename = f"{job_id}_audiobook{output_ext}"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

    # Create job
    job = ConversionJob(
        id=job_id,
        epub_path=epub_path,
        output_path=output_path,
        status='pending',
        progress=0,
        message='Queued for conversion',
        created_at=datetime.now().isoformat()
    )
    jobs[job_id] = job

    # Start conversion in background
    thread = threading.Thread(
        target=run_conversion,
        args=(job, voice_id, speed, output_format)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'job_id': job_id, 'status': 'started'})


def run_conversion(job: ConversionJob, voice_id: str, speed: int, output_format: str):
    """Run the conversion process in background."""
    temp_dir = None
    try:
        job.status = 'processing'
        job.progress = 5
        job.message = 'Parsing ePub...'

        # Parse ePub
        parser = EPubParser(job.epub_path)
        parser.parse()

        job.title = parser.metadata.title
        job.author = parser.metadata.author
        job.chapters = len(parser.chapters)

        if not parser.chapters:
            raise Exception("No chapters found in ePub")

        # Initialize TTS
        job.progress = 10
        job.message = 'Initializing TTS engine...'

        tts = TTSEngine()
        if not tts.initialize():
            raise Exception("Failed to initialize TTS engine")

        # Configure voice
        if voice_id:
            tts.configure(TTSConfig(voice_id=voice_id, rate=speed))
        else:
            tts.configure(TTSConfig(rate=speed))

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
            job.progress = progress
            job.message = f'Converting chapter {i + 1}/{total_chapters}: {chapter.title}'

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
        job.progress = 75
        job.message = 'Merging chapters...'

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
        job.progress = 85
        job.message = 'Normalizing audio...'

        normalized_path = os.path.join(temp_dir, "normalized.wav")
        processor.normalize_audio(merged_path, normalized_path)

        # Create final output
        job.progress = 90
        job.message = 'Creating final audiobook...'

        if output_format == 'm4b':
            creator = M4BCreator()
            meta = AudiobookMetadata(
                title=parser.metadata.title,
                author=parser.metadata.author,
                cover_image=parser.metadata.cover_image,
                cover_mime_type=parser.metadata.cover_mime_type
            )
            success = creator.create_m4b(normalized_path, job.output_path, markers, meta)
        else:
            processor.convert_format(normalized_path, job.output_path, AudioFormat.MP3)
            success = True

        if not success or not os.path.exists(job.output_path):
            raise Exception("Failed to create output file")

        # Done!
        job.progress = 100
        job.status = 'complete'
        job.message = 'Conversion complete!'

        # Cleanup TTS
        tts.cleanup()

    except Exception as e:
        job.status = 'error'
        job.error = str(e)
        job.message = f'Error: {str(e)}'

    finally:
        # Cleanup temp files
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get conversion job status."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs[job_id]
    return jsonify(job.to_dict())


@app.route('/api/download/<job_id>')
def download_file(job_id):
    """Download the converted audiobook."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs[job_id]
    if job.status != 'complete':
        return jsonify({'error': 'Conversion not complete'}), 400

    if not os.path.exists(job.output_path):
        return jsonify({'error': 'Output file not found'}), 404

    # Determine download filename
    ext = '.m4b' if job.output_path.endswith('.m4b') else '.mp3'
    download_name = f"{job.title or 'audiobook'}{ext}"

    return send_file(
        job.output_path,
        as_attachment=True,
        download_name=download_name
    )


@app.route('/api/cleanup/<job_id>', methods=['DELETE'])
def cleanup_job(job_id):
    """Clean up job files."""
    if job_id in jobs:
        job = jobs[job_id]

        # Remove files
        if os.path.exists(job.epub_path):
            os.unlink(job.epub_path)
        if os.path.exists(job.output_path):
            os.unlink(job.output_path)

        del jobs[job_id]

    return jsonify({'status': 'cleaned'})


if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)
