from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify, Response
from flask_login import login_required, current_user
import os, requests, json
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

@docs_bp.route('/documents')
@login_required
def index():
    docs = Document.query.filter_by(user_id=current_user.id)\
        .order_by(Document.uploaded_at.desc()).all()
    return render_template('documents/index.html', docs=docs,
                           subjects=SUBJECTS, grade_levels=GRADE_LEVELS)


@docs_bp.route('/documents/upload', methods=['POST'])
@login_required
def upload():
    """Save file to disk and redirect to the streaming progress page."""
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
        flash(f'File type not allowed. Use: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')
        return redirect(url_for('documents.index'))

    if not subject:
        flash('Please select a subject.', 'danger')
        return redirect(url_for('documents.index'))

    filename = secure_filename(file.filename)
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'],
                             f"{current_user.id}_{filename}")
    file.save(save_path)

    # Store pending info in session-like query params, render progress page
    return render_template(
        'documents/progress.html',
        filename=filename,
        subject=subject,
        grade_level=grade_level,
        save_path=save_path,
        user_id=current_user.id
    )


@docs_bp.route('/documents/ingest-stream')
@login_required
def ingest_stream():
    """
    Flask SSE proxy — streams events from FastAPI /ingest/stream to the browser.
    Query params: filename, subject, grade_level, save_path, user_id
    """
    filename    = request.args.get('filename', '')
    subject     = request.args.get('subject', '')
    grade_level = request.args.get('grade_level', '')
    save_path   = request.args.get('save_path', '')

    # ── Capture user_id as a plain int NOW, before the generator runs ────────
    # current_user is a Flask-Login proxy tied to the request context.
    # The generator runs lazily after the response starts streaming, at which
    # point the request context (and therefore current_user) is gone.
    # Capturing it into a plain variable here keeps it alive in the closure.
    uid = current_user.id

    if not save_path or not os.path.exists(save_path):
        def err():
            yield f"data: {json.dumps({'done': True, 'error': 'Uploaded file not found on server. Please try uploading again.'})}\n\n"
        return Response(err(), mimetype='text/event-stream')

    def generate():
        try:
            with open(save_path, 'rb') as f:
                resp = requests.post(
                    f"{FASTAPI_URL}/ingest/stream",
                    data={
                        "user_id": uid,        # plain int, not current_user.id
                        "subject": subject,
                        "grade_level": grade_level
                    },
                    files={"file": (filename, f, 'application/octet-stream')},
                    stream=True,
                    timeout=300
                )
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        decoded = line.decode('utf-8')
                        yield f"{decoded}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'done': True, 'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )


@docs_bp.route('/documents/save', methods=['POST'])
@login_required
def save_document():
    """Called by JS after streaming completes — persists the document record to DB."""
    data = request.get_json()
    filename        = data.get('filename', '')
    subject         = data.get('subject', '')
    grade_level     = data.get('grade_level', '')
    save_path       = data.get('save_path', '')
    collection_name = data.get('collection_name', '')
    chunk_count     = data.get('chunk_count', 0)

    try:
        doc = Document(
            user_id=current_user.id,
            filename=filename,
            subject=subject,
            grade_level=grade_level,
            file_path=save_path,
            chroma_collection=collection_name,
            chunk_count=chunk_count
        )
        db.session.add(doc)
        db.session.commit()
        return jsonify({"success": True, "doc_id": doc.id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
