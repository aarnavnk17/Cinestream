from flask import Flask, render_template, redirect, request, session, url_for
from models import db, Movie, User, Rental, CartItem
from werkzeug.security import generate_password_hash, check_password_hash
from seed_movies import MOVIES_DATA

app = Flask(__name__)
app.secret_key = "secret123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()

        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect('/movies')

        else:
            return "Invalid username or password ❌"

    return render_template('login.html')


# ---------------- REGISTER ----------------
@app.route('/register', methods=['POST'])
def register():
    existing_user = User.query.filter_by(username=request.form['username']).first()

    if existing_user:
        return "Username already exists ❌"

    from werkzeug.security import generate_password_hash

    hashed_password = generate_password_hash(request.form['password'])

    # ✅ FIRST USER = ADMIN
    is_admin = True if User.query.count() == 0 else False

    user = User(
        username=request.form['username'],
        password=hashed_password,
        is_admin=is_admin
    )

    db.session.add(user)
    db.session.commit()

    return redirect('/')

# ---------------- MOVIES ----------------
@app.route('/movies')
def movies():
    if 'user_id' not in session:
        return redirect('/')

    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/logout')
    
    # Get Filter Params
    query = request.args.get('q', '')
    lang = request.args.get('lang', '')
    genre = request.args.get('genre', '')

    movie_query = Movie.query

    if query:
        movie_query = movie_query.filter(Movie.title.contains(query) | Movie.description.contains(query))
    if lang:
        movie_query = movie_query.filter(Movie.language == lang)
    if genre:
        movie_query = movie_query.filter(Movie.genre.contains(genre))

    all_movies = movie_query.all()

    # Get filter options for UI
    languages = db.session.query(Movie.language).distinct().all()
    languages = [l[0] for l in languages if l[0]]
    
    # Common genres for filtering (can also be dynamic but static is cleaner for UI)
    all_genres = ["Action", "Drama", "Thriller", "Comedy", "Sci-Fi", "Romance", "Horror", "Animation"]

    return render_template('movies.html', 
                           movies=all_movies, 
                           user=user, 
                           languages=sorted(languages), 
                           all_genres=all_genres,
                           selected_lang=lang,
                           selected_genre=genre,
                           search_query=query)


# ---------------- CART ROUTES ----------------
@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        return redirect('/')
    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/logout')
    cart_items = CartItem.query.filter_by(user_id=user.id).all()
    total = sum(item.cost for item in cart_items)
    return render_template('cart.html', user=user, cart_items=cart_items, total=total)

@app.route('/add-to-cart/<int:id>', methods=['POST'])
def add_to_cart(id):
    if 'user_id' not in session:
        return redirect('/')
    
    movie = Movie.query.get(id)
    duration = request.form.get('duration')
    
    # Pricing logic for durations
    base_price = movie.price
    cost = base_price
    if duration == "1 Week":
        cost = int(base_price * 2.5) # Discounted week rate
    elif duration == "1 Month":
        cost = base_price * 6 # Discounted month rate

    new_item = CartItem(user_id=session['user_id'], movie_id=id, duration=duration, cost=cost)
    db.session.add(new_item)
    db.session.commit()
    return redirect('/cart')

@app.route('/remove-from-cart/<int:id>')
def remove_from_cart(id):
    if 'user_id' not in session:
        return redirect('/')
    item = CartItem.query.get(id)
    if item and item.user_id == session['user_id']:
        db.session.delete(item)
        db.session.commit()
    return redirect('/cart')

# ---------------- PAYMENT & CHECKOUT ----------------
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect('/')
    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/logout')
    cart_items = CartItem.query.filter_by(user_id=user.id).all()
    total = sum(item.cost for item in cart_items)

    if request.method == 'POST':
        # Mock payment processing
        for item in cart_items:
            movie = Movie.query.get(item.movie_id)
            if movie.available > 0:
                rental = Rental(
                    user_id=user.id, 
                    movie_id=item.movie_id, 
                    duration=item.duration, 
                    cost=item.cost
                )
                movie.available -= 1
                db.session.add(rental)
        
        # Clear cart after successful "payment"
        CartItem.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        return render_template('payment_success.html', user=user)

    return render_template('payment.html', user=user, cart_items=cart_items, total=total)


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/logout')

    rentals = Rental.query.filter_by(
        user_id=user.id,
        returned=False
    ).all()

    return render_template('dashboard.html', rentals=rentals)


# ---------------- RETURN ----------------
@app.route('/return/<int:id>')
def return_movie(id):
    if 'user_id' not in session:
        return redirect('/')

    rental = Rental.query.get(id)

    if rental:
        rental.returned = True
        rental.movie.available += 1
        db.session.commit()

    return redirect('/dashboard')


# ================= ADMIN PORTAL =================

# ---------------- ADMIN PAGE ----------------
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect('/')

    user = User.query.get(session['user_id'])

    if not user or not user.is_admin:
        return redirect('/logout' if not user else '/movies')

    movies = Movie.query.all()
    return render_template('admin.html', movies=movies)


# ---------------- DATABASE VIEW ----------------
@app.route('/admin/db-view')
def db_view():
    if 'user_id' not in session:
        return redirect('/')

    user = User.query.get(session['user_id'])

    if not user or not user.is_admin:
        return redirect('/movies')

    users = User.query.all()
    movies = Movie.query.all()
    rentals = Rental.query.all()

    return render_template('db_view.html', users=users, movies=movies, rentals=rentals)


# ---------------- TMDB SYNC ----------------
@app.route('/admin/sync')
def admin_sync():
    if 'user_id' not in session:
        return redirect('/')

    user = User.query.get(session['user_id'])

    if not user or not user.is_admin:
        return redirect('/movies')

    try:
        from tmdb_sync import sync
        sync()
        return "Sync Successful! ✅ <a href='/admin'>Back to Admin</a>"
    except Exception as e:
        return f"Sync Failed: {str(e)} ❌ <a href='/admin'>Back to Admin</a>"


# ---------------- SEED DATA ----------------
@app.route('/seed')
def seed():
    if Movie.query.count() == 0:
        movies_to_add = []
        for m in MOVIES_DATA:
            movie = Movie(
                title=m['title'],
                description=m['description'],
                genre=m['genre'],
                available=10,
                image_url=m['image_url']
            )
            movies_to_add.append(movie)
        
        db.session.add_all(movies_to_add)
        db.session.commit()
        return f"Database seeded with {len(MOVIES_DATA)} movies! ✅ <a href='/'>Go to Login</a>"
    return "Database already has data. ❌ <a href='/'>Go to Login</a>"


# ---------------- ADMIN DELETE MOVIE ----------------
@app.route('/admin/delete/<int:id>')
def admin_delete(id):
    if 'user_id' not in session:
        return redirect('/')

    user = User.query.get(session['user_id'])

    if not user or not user.is_admin:
        return "Access Denied ❌"

    movie = Movie.query.get(id)

    if movie:
        db.session.delete(movie)
        db.session.commit()

    return redirect('/admin')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)