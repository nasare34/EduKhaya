from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.models.database import db
from shared.utils.llm import SUPPORTED_LLMS

settings_bp = Blueprint('settings', __name__)

REGIONS = [
    "Greater Accra", "Ashanti", "Western", "Eastern", "Central",
    "Volta", "Northern", "Upper East", "Upper West", "Brong-Ahafo",
    "Oti", "Ahafo", "Bono East", "North East", "Savannah", "Western North"
]

@settings_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name).strip()
        current_user.school = request.form.get('school', current_user.school).strip()
        current_user.region = request.form.get('region', current_user.region)
        current_user.preferred_llm = request.form.get('preferred_llm', current_user.preferred_llm)
        db.session.commit()
        flash('Settings updated!', 'success')
        return redirect(url_for('settings.index'))
    return render_template('settings/index.html', llms=SUPPORTED_LLMS, regions=REGIONS)
