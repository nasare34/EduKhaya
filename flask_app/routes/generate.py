from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
import os, requests
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.models.database import db, Generation, Document
from shared.utils.llm import SUPPORTED_LLMS
from shared.utils.khaya import TRANSLATION_LANGUAGES, TTS_LANGUAGES, TTS_SPEAKERS

gen_bp = Blueprint('generate', __name__)
FASTAPI_URL = os.getenv('FASTAPI_URL', 'http://127.0.0.1:8000')

SUBJECTS = [
    "Mathematics", "English Language", "Science", "Social Studies",
    "Ghanaian Language", "Religious & Moral Education", "Creative Arts",
    "Physical Education", "ICT", "French", "History", "Geography", "Other"
]
GRADE_LEVELS = [
    "Primary 1", "Primary 2", "Primary 3", "Primary 4", "Primary 5", "Primary 6",
    "JHS 1", "JHS 2", "JHS 3"
]
GENERATION_TYPES = {
    "lesson_plan":     "📋 Lesson Plan",
    "exam_questions":  "📝 Exam Questions",
    "examples":        "💡 Examples & Exercises",
    "explanation":     "📖 Explanation"
}

@gen_bp.route('/generate', methods=['GET'])
@login_required
def index():
    user_docs = Document.query.filter_by(user_id=current_user.id).all()
    subjects_with_docs = list(set([d.subject for d in user_docs]))
    return render_template('generate/index.html',
                           subjects=SUBJECTS,
                           grade_levels=GRADE_LEVELS,
                           generation_types=GENERATION_TYPES,
                           llms=SUPPORTED_LLMS,
                           languages=TRANSLATION_LANGUAGES,
                           subjects_with_docs=subjects_with_docs,
                           current_llm=current_user.preferred_llm)

@gen_bp.route('/generate', methods=['POST'])
@login_required
def generate():
    subject       = request.form.get('subject')
    grade_level   = request.form.get('grade_level')
    topic         = request.form.get('topic')
    generation_type = request.form.get('generation_type')
    llm_choice    = request.form.get('llm_choice', current_user.preferred_llm or 'groq')
    extra         = request.form.get('extra_instructions', '')

    if not all([subject, grade_level, topic, generation_type]):
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('generate.index'))

    try:
        resp = requests.post(f"{FASTAPI_URL}/generate", json={
            "user_id": current_user.id,
            "subject": subject,
            "grade_level": grade_level,
            "topic": topic,
            "generation_type": generation_type,
            "llm_choice": llm_choice,
            "extra_instructions": extra
        }, timeout=120)

        # Extract the real error detail before raising
        if not resp.ok:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            flash(f'Generation failed: {detail}', 'danger')
            return redirect(url_for('generate.index'))

        data = resp.json()
        content = data['content']

        gen = Generation(
            user_id=current_user.id,
            subject=subject,
            grade_level=grade_level,
            generation_type=generation_type,
            prompt=topic,
            response_english=content,
            llm_used=llm_choice
        )
        db.session.add(gen)
        db.session.commit()

        return render_template('generate/result.html',
                               generation=gen,
                               content=content,
                               translation_languages=TRANSLATION_LANGUAGES,
                               tts_languages=TTS_LANGUAGES,
                               tts_speakers=TTS_SPEAKERS,
                               generation_types=GENERATION_TYPES)
    except Exception as e:
        flash(f'Generation error: {str(e)}', 'danger')
        return redirect(url_for('generate.index'))

@gen_bp.route('/generate/translate', methods=['POST'])
@login_required
def translate():
    data = request.get_json()
    gen_id      = data.get('generation_id')
    target_lang = data.get('target_lang')
    text        = data.get('text', '')

    try:
        resp = requests.post(f"{FASTAPI_URL}/translate", json={
            "text": text,
            "source_lang": "en",
            "target_lang": target_lang
        }, timeout=60)
        resp.raise_for_status()
        result = resp.json()

        if gen_id:
            gen = Generation.query.filter_by(id=gen_id, user_id=current_user.id).first()
            if gen:
                gen.response_translated = result['translated_text']
                gen.target_language = target_lang
                db.session.commit()

        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@gen_bp.route('/generate/tts', methods=['POST'])
@login_required
def tts():
    data       = request.get_json()
    text       = data.get('text', '')
    language   = data.get('language', 'twi')
    speaker_id = data.get('speaker_id', 'female')
    fmt        = data.get('format', 'mp3')
    gen_id     = data.get('generation_id')

    try:
        resp = requests.post(f"{FASTAPI_URL}/tts", json={
            "text": text,
            "language": language,
            "speaker_id": speaker_id,
            "audio_format": fmt
        }, timeout=60)
        resp.raise_for_status()
        result = resp.json()

        if gen_id and result.get('audio_url'):
            gen = Generation.query.filter_by(id=gen_id, user_id=current_user.id).first()
            if gen:
                gen.audio_url = result['audio_url']
                db.session.commit()

        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@gen_bp.route('/history')
@login_required
def history():
    gens = Generation.query.filter_by(user_id=current_user.id)\
        .order_by(Generation.created_at.desc()).all()
    return render_template('generate/history.html',
                           generations=gens,
                           generation_types=GENERATION_TYPES,
                           languages=TRANSLATION_LANGUAGES)

@gen_bp.route('/history/<int:gen_id>/delete', methods=['POST'])
@login_required
def delete_generation(gen_id):
    gen = Generation.query.filter_by(id=gen_id, user_id=current_user.id).first_or_404()
    try:
        # Delete audio file if it exists
        if gen.audio_url:
            audio_path = os.path.join(
                os.path.dirname(__file__), '..', 'static',
                gen.audio_url.lstrip('/')
            )
            if os.path.exists(audio_path):
                os.remove(audio_path)
        db.session.delete(gen)
        db.session.commit()
        flash('Generation deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting: {str(e)}', 'danger')
    return redirect(url_for('generate.history'))


@gen_bp.route('/history/delete-all', methods=['POST'])
@login_required
def delete_all_generations():
    try:
        gens = Generation.query.filter_by(user_id=current_user.id).all()
        for gen in gens:
            if gen.audio_url:
                audio_path = os.path.join(
                    os.path.dirname(__file__), '..', 'static',
                    gen.audio_url.lstrip('/')
                )
                if os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except Exception:
                        pass
            db.session.delete(gen)
        db.session.commit()
        flash(f'All {len(gens)} generations deleted.', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('generate.history'))
    gen = Generation.query.filter_by(id=gen_id, user_id=current_user.id).first_or_404()
    return render_template('generate/result.html',
                           generation=gen,
                           content=gen.response_english,
                           translation_languages=TRANSLATION_LANGUAGES,
                           tts_languages=TTS_LANGUAGES,
                           tts_speakers=TTS_SPEAKERS,
                           generation_types=GENERATION_TYPES)
