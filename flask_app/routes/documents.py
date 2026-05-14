from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify, Response
from flask_login import login_required, current_user
import os, requests, json, threading
from werkzeug.utils import secure_filename
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.models.database import db, Document

docs_bp = Blueprint('documents', __name__)

FASTAPI_URL = os.getenv('FASTAPI_URL', 'http://127.0.0.1:8000')
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.md', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'}

SUBJECTS = [
    "Mathematics", "English Language", "Science", "Social Studies",
    "Ghanaian Language", "Religious & Moral Education", "Creative Arts",
    "Physical Education", "ICT", "French", "History", "Geography", "Other"
]
GRADE_LEVELS = [
    "Primary 1", "Primary 2", "Primary 3", "Primary 4", "Primary 5", "Primary 6",
    "JHS 1", "JHS 2", "JHS 3"
]

# In-memory job store: job_id -> status dict
_jobs = {}

def _run_ingest(job_id, save_path, filename, uid, subject, grade_level):
    """Run in background thread — calls FastAPI /ingest and updates job status."""
    try:
        _jobs[job_id] = {"status": "reading", "label": "Reading your file...", "progress": 10, "done": False, "error": None}
        with open(save_path, 'rb') as f:
            _jobs[job_id] = {"status": "embedding", "label": "Splitting and embedding content...", "progress": 40, "done": False, "error": None}
            resp = requests.post(
                f"{FASTAPI_URL}/ingest",
                data={"user_id": uid, "subject": subject, "grade_level": grade_level},
                files={"file": (filename, f, 'application/octet-stream')},
                timeout=300
            )
            resp.raise_for_status()
            data = resp.json()

        _jobs[job_id] = {
            "status": "done", "label": "Ready to use!", "progress": 100,
            "done": True, "error": None,
            "collection_name": data.get("collection_name", ""),
            "chunk_count": data.get("chunk_count", 0),
        }
    except Exception as e:
        _jobs[job_id] = {"status": "error", "label": "Processing failed", "progress": 0, "done": True, "error": str(e)}


@docs_bp.route('/documents')
@login_required
def index():
    docs = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).all()
    return render_template('documents/index.html', docs=docs, subjects=SUBJECTS, grade_levels=GRADE_LEVELS)


@docs_bp.route('/documents/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('documents.index'))

    file = request.files['file']
    subject = request.form.get('subject', '')
    grade_level = request.form.get('grade_level', '')

    if not file.filename:
        flash('No file selected.', 'danger')
        return redirect(url_for('documents.index'))

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash(f'File type not allowed.', 'danger')
        return redirect(url_for('documents.index'))

    if not subject:
        flash('Please select a subject.', 'danger')
        return redirect(url_for('documents.index'))

    filename = secure_filename(file.filename)
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{current_user.id}_{filename}")
    file.save(save_path)

    # Create job and start background thread
    import uuid
    job_id = str(uuid.uuid4())[:12]
    uid = current_user.id
    _jobs[job_id] = {"status": "starting", "label": "Starting...", "progress": 5, "done": False, "error": None}

    t = threading.Thread(
        target=_run_ingest,
        args=(job_id, save_path, filename, uid, subject, grade_level),
        daemon=True
    )
    t.start()

    return render_template(
        'documents/progress.html',
        filename=filename,
        subject=subject,
        grade_level=grade_level,
        save_path=save_path,
        user_id=uid,
        job_id=job_id
    )


@docs_bp.route('/documents/job-status/<job_id>')
@login_required
def job_status(job_id):
    """Poll endpoint — returns current job status as JSON."""
    status = _jobs.get(job_id, {"status": "unknown", "label": "Job not found", "progress": 0, "done": True, "error": "Job not found"})
    return jsonify(status)


@docs_bp.route('/documents/save', methods=['POST'])
@login_required
def save_document():
    data = request.get_json()
    try:
        doc = Document(
            user_id=current_user.id,
            filename=data.get('filename', ''),
            subject=data.get('subject', ''),
            grade_level=data.get('grade_level', ''),
            file_path=data.get('save_path', ''),
            chroma_collection=data.get('collection_name', ''),
            chunk_count=data.get('chunk_count', 0)
        )
        db.session.add(doc)
        db.session.commit()
        return jsonify({"success": True, "doc_id": doc.id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@docs_bp.route('/documents/delete-all', methods=['POST'])
@login_required
def delete_all():
    docs = Document.query.filter_by(user_id=current_user.id).all()
    count = len(docs)
    try:
        for doc in docs:
            try:
                if doc.chroma_collection:
                    requests.delete(f"{FASTAPI_URL}/collections/{doc.chroma_collection}", timeout=10)
            except Exception:
                pass
            try:
                if doc.file_path and os.path.exists(doc.file_path):
                    os.remove(doc.file_path)
            except Exception:
                pass
            db.session.delete(doc)
        db.session.commit()
        flash(f'All {count} documents deleted.', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('documents.index'))


@docs_bp.route('/documents/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete(doc_id):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    try:
        if doc.chroma_collection:
            requests.delete(f"{FASTAPI_URL}/collections/{doc.chroma_collection}", timeout=10)
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        db.session.delete(doc)
        db.session.commit()
        flash('Document deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting: {str(e)}', 'danger')
    return redirect(url_for('documents.index'))
