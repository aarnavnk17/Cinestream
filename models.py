from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Junction Table for Many-to-Many relationship between Movies and Genres
movie_genres = db.Table('movie_genres',
    db.Column('movie_id', db.Integer, db.ForeignKey('movie.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    rentals = db.relationship('Rental', backref='user', lazy=True)

class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Language(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True)

class PricingTier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True) # e.g., "Premium", "Vintage"
    price = db.Column(db.Integer)
    description = db.Column(db.String(100))

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    release_year = db.Column(db.String(10))
    available = db.Column(db.Integer, default=10)
    
    # Foreign Keys for 2NF/3NF
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'))
    tier_id = db.Column(db.Integer, db.ForeignKey('pricing_tier.id'))
    
    # Relationships
    language = db.relationship('Language', backref='movies')
    tier = db.relationship('PricingTier', backref='movies')
    genres = db.relationship('Genre', secondary=movie_genres, backref='movies')

class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'))
    returned = db.Column(db.Boolean, default=False)
    rental_date = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.String(20))
    cost = db.Column(db.Integer)

    movie = db.relationship('Movie')

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'))
    duration = db.Column(db.String(20))

    movie = db.relationship('Movie')