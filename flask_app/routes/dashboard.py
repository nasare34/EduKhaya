from flask import Blueprint, render_template
from flask_login import login_required, current_user
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.models.database import Document, Generation

dash_bp = Blueprint('dashboard', __name__)

@dash_bp.route('/dashboard')
@login_required
def home():
    doc_count = Document.query.filter_by(user_id=current_user.id).count()
    gen_count = Generation.query.filter_by(user_id=current_user.id).count()
    recent_gens = Generation.query.filter_by(user_id=current_user.id)\
        .order_by(Generation.created_at.desc()).limit(5).all()
    return render_template('dashboard/home.html',
                           doc_count=doc_count,
                           gen_count=gen_count,
                           recent_gens=recent_gens)
