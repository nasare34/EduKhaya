import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

load_dotenv()

from shared.models.database import db, User

bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-this')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///eduai.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB upload limit
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static', 'audio'), exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from flask_app.routes.auth import auth_bp
    from flask_app.routes.dashboard import dash_bp
    from flask_app.routes.documents import docs_bp
    from flask_app.routes.generate import gen_bp
    from flask_app.routes.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dash_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(gen_bp)
    app.register_blueprint(settings_bp)

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
