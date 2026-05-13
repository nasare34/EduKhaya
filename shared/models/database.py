from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    school = db.Column(db.String(200))
    region = db.Column(db.String(100))
    preferred_llm = db.Column(db.String(50), default='groq')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    documents = db.relationship('Document', backref='teacher', lazy=True)
    generations = db.relationship('Generation', backref='teacher', lazy=True)

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    grade_level = db.Column(db.String(50))
    file_path = db.Column(db.String(500), nullable=False)
    chroma_collection = db.Column(db.String(200))
    chunk_count = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Generation(db.Model):
    __tablename__ = 'generations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(100))
    grade_level = db.Column(db.String(50))
    generation_type = db.Column(db.String(50))  # lesson_plan, exam_questions, examples, explanation
    prompt = db.Column(db.Text)
    response_english = db.Column(db.Text)
    response_translated = db.Column(db.Text)
    target_language = db.Column(db.String(50))
    audio_url = db.Column(db.String(500))
    llm_used = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
