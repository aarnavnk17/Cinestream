from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    rentals = db.relationship('Rental', backref='user', lazy=True)


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    genre = db.Column(db.String(50))
    language = db.Column(db.String(50))
    release_year = db.Column(db.String(10))
    price = db.Column(db.Integer)
    available = db.Column(db.Integer)


class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'))
    returned = db.Column(db.Boolean, default=False)
    rental_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    duration = db.Column(db.String(20))
    cost = db.Column(db.Integer)

    movie = db.relationship('Movie')

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'))
    duration = db.Column(db.String(20))
    cost = db.Column(db.Integer)

    movie = db.relationship('Movie')