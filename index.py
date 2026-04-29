from flask import Flask, render_template, redirect, request, session, url_for
from models import db, Movie, User, Rental, CartItem, Language, Genre, PricingTier
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "secret123"

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
# Workaround for Heroku/Vercel postgres:// vs postgresql://
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

db.init_app(app)

with app.app_context():
    db.create_all()
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        hashed_pw = generate_password_hash('admin123')
        db.session.add(User(username='admin', password=hashed_pw, is_admin=True))
        db.session.commit()

# Automatic Sync is disabled on startup to prevent timeouts on Vercel.
# Run 'python tmdb_sync.py' locally or trigger via /admin/sync.

def calculate_cost(movie, duration):
    base_price = movie.tier.price
    if duration == "1 Week": return int(base_price * 2.5)
    if duration == "1 Month": return base_price * 6
    return base_price

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect('/movies')
        else:
            from flask import flash
            flash("Invalid username or password ❌", "danger")
            return redirect('/')
    return render_template('login.html')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['POST'])
def register():
    existing_user = User.query.filter_by(username=request.form['username']).first()
    if existing_user:
        from flask import flash
        flash("Username already exists ❌", "warning")
        return redirect('/')
    hashed_password = generate_password_hash(request.form['password'])
    is_admin = True if User.query.count() == 0 else False
    user = User(username=request.form['username'], password=hashed_password, is_admin=is_admin)
    db.session.add(user)
    db.session.commit()
    return redirect('/')

# ---------------- MOVIES ----------------
@app.route('/movies')
def movies():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user: return redirect('/logout')
    
    query = request.args.get('q', '')
    lang_id = request.args.get('lang', '')
    genre_id = request.args.get('genre', '')

    movie_query = Movie.query
    if query:
        movie_query = movie_query.filter(Movie.title.contains(query) | Movie.description.contains(query))
    if lang_id:
        movie_query = movie_query.filter(Movie.language_id == lang_id)
    if genre_id:
        movie_query = movie_query.filter(Movie.genres.any(id=genre_id))

    all_movies = movie_query.all()
    all_languages = Language.query.all()
    all_genres = Genre.query.all()

    return render_template('movies.html', 
                           movies=all_movies, 
                           user=user, 
                           languages=all_languages, 
                           all_genres=all_genres,
                           selected_lang=lang_id,
                           selected_genre=genre_id,
                           search_query=query)

# ---------------- CART ROUTES ----------------
@app.route('/cart')
def view_cart():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user: return redirect('/logout')
    cart_items = CartItem.query.filter_by(user_id=user.id).all()
    # Calculate costs dynamically for 3NF
    for item in cart_items:
        item.dynamic_cost = calculate_cost(item.movie, item.duration)
    total = sum(item.dynamic_cost for item in cart_items)
    return render_template('cart.html', user=user, cart_items=cart_items, total=total)

@app.route('/add-to-cart/<int:id>', methods=['POST'])
def add_to_cart(id):
    if 'user_id' not in session: return redirect('/')
    movie = Movie.query.get(id)
    duration = request.form.get('duration')
    
    new_item = CartItem(user_id=session['user_id'], movie_id=id, duration=duration)
    db.session.add(new_item)
    db.session.commit()
    return redirect('/cart')

@app.route('/remove-from-cart/<int:id>')
def remove_from_cart(id):
    if 'user_id' not in session: return redirect('/')
    item = CartItem.query.get(id)
    if item and item.user_id == session['user_id']:
        db.session.delete(item)
        db.session.commit()
    return redirect('/cart')

# ---------------- PAYMENT & CHECKOUT ----------------
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user: return redirect('/logout')
    cart_items = CartItem.query.filter_by(user_id=user.id).all()
    for item in cart_items:
        item.dynamic_cost = calculate_cost(item.movie, item.duration)
    total = sum(item.dynamic_cost for item in cart_items)

    if request.method == 'POST':
        for item in cart_items:
            movie = Movie.query.get(item.movie_id)
            if movie.available > 0:
                # Capture cost snapshot for Rental (Historical Record)
                final_cost = calculate_cost(movie, item.duration)
                rental = Rental(user_id=user.id, movie_id=item.movie_id, duration=item.duration, cost=final_cost)
                movie.available -= 1
                db.session.add(rental)
        CartItem.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        return render_template('payment_success.html', user=user)
    return render_template('payment.html', user=user, cart_items=cart_items, total=total)

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user: return redirect('/logout')
    rentals = Rental.query.filter_by(user_id=user.id, returned=False).all()
    return render_template('dashboard.html', rentals=rentals)

# ---------------- RETURN ----------------
@app.route('/return/<int:id>')
def return_movie(id):
    if 'user_id' not in session: return redirect('/')
    rental = Rental.query.get(id)
    if rental:
        rental.returned = True
        rental.movie.available += 1
        db.session.commit()
    return redirect('/dashboard')

# ---------------- ADMIN PORTAL ----------------
@app.route('/admin')
def admin():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin: return redirect('/logout' if not user else '/movies')
    movies = Movie.query.all()
    return render_template('admin.html', movies=movies)

@app.route('/admin/db-view')
def db_view():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin: return redirect('/logout' if not user else '/movies')
    return render_template('db_view.html', users=User.query.all(), movies=Movie.query.all(), rentals=Rental.query.all(),
                           genres=Genre.query.all(), languages=Language.query.all(), tiers=PricingTier.query.all())

@app.route('/admin/sync')
def admin_sync():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin: return redirect('/movies')
    try:
        from tmdb_sync import sync
        sync()
        return "Sync Successful! ✅ <a href='/admin'>Back to Admin</a>"
    except Exception as e:
        return f"Sync Failed: {str(e)} ❌ <a href='/admin'>Back to Admin</a>"

@app.route('/admin/delete/<int:id>')
def admin_delete(id):
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin: return "Access Denied ❌"
    movie = Movie.query.get(id)
    if movie:
        db.session.delete(movie)
        db.session.commit()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)