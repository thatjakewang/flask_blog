import os

#取得目前位置
CONFIG_DIR = os.path.abspath(os.path.dirname(__file__))

INSTANCE_FOLDER = os.path.join(CONFIG_DIR, "instance")

class Config:


    SECRET_KEY = os.environ.get('SECRET_KEY')

    CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = SECRET_KEY

    #上線後改為 False
    DEBUG = True

    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(INSTANCE_FOLDER, "blog.db")}'