class Config:
    SECRET_KEY = 'this-should-be-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/inventory.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
