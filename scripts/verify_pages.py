#!/usr/bin/env python3
import os
import sys
import re
from dataclasses import dataclass

# Ensure project root on sys.path
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app, db
from config import DevelopmentConfig
from app.models import User, Category, Post


class TestConfig(DevelopmentConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False
    FORCE_HTTPS = False
    SERVER_NAME = 'example.test'
    PREFERRED_URL_SCHEME = 'https'
    DEBUG = False


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str


def seed(app):
    with app.app_context():
        db.create_all()
        # Create a user
        u = User(username='admin', email='admin@example.test')
        u.set_password('password')
        db.session.add(u)
        # Create a category
        c = Category(name='Tech', slug='tech', description='Tech posts')
        db.session.add(c)
        db.session.flush()
        # Create a post
        p = Post(
            title='Hello World',
            slug='hello-world',
            description='Desc',
            content='<p>Hi</p>',
            status='published',
            author_id=u.id,
            category_id=c.id,
            thumbnail='sample.png'
        )
        db.session.add(p)
        db.session.commit()


def _optional_absolute(meta_regex: str, html: str) -> bool:
    present_regex = meta_regex.replace('https?://', '')
    if not re.search(present_regex, html, re.IGNORECASE):
        return True
    return re.search(meta_regex, html, re.IGNORECASE) is not None


def check_absolute_urls(html: str) -> CheckResult:
    # Allow OG/Twitter meta to be absent on listing; enforce JSON-LD image/logo absolute URLs
    checks = [
        _optional_absolute(r'<meta[^>]+property="og:image"[^>]+content="https?://', html),
        _optional_absolute(r'<meta[^>]+name="twitter:image"[^>]+content="https?://', html),
        bool(re.search(r'"image"\s*:\s*"https?://', html, re.IGNORECASE)),
        bool(re.search(r'"logo"\s*:\s*\{\s*"@type"\s*:\s*"ImageObject"\s*,\s*"url"\s*:\s*"https?://', html, re.IGNORECASE)),
    ]
    passed = all(checks)
    details = 'OK' if passed else 'One or more absolute URL checks failed'
    return CheckResult('absolute_urls', passed, details)


def main():
    app = create_app(config_class=TestConfig)
    seed(app)
    results = []
    with app.test_client() as c:
        # Index page
        res = c.get('/')
        html = res.get_data(as_text=True)
        results.append(('GET /', check_absolute_urls(html)))
        # Post page
        res = c.get('/hello-world/')
        html = res.get_data(as_text=True)
        results.append(('GET /hello-world/', check_absolute_urls(html)))

    print('Verification results:')
    for route, r in results:
        status = 'PASS' if r.passed else 'FAIL'
        print(f'- {route}: {status} - {r.details}')


if __name__ == '__main__':
    main()
