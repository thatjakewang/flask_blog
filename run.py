from app import create_app, db
from app.models import Post, Tag, Category

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Post': Post, 'Tag': Tag, 'Category': Category}

if __name__ == '__main__':
    app.run(debug=True)