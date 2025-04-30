from dotenv import load_dotenv
from app import create_app, db
from app.models import Post, User
from config import Config


load_dotenv()

app = create_app(Config)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Post': Post, 'User': User}

if __name__ == '__main__':
    if app.config.get('FLASK_ENV', 'production') == 'development':
        app.run(debug=app.config.get('DEBUG', False))