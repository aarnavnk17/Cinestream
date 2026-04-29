import requests
from index import app, db, Movie, Genre, Language, PricingTier

import os
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "e528bd8a8676e863cd592e38f8bb91d7")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w780"

LANG_MAP = {
    "en-US": "English",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "ml-IN": "Malayalam",
    "kn-IN": "Kannada",
    "bn-IN": "Bengali",
    "mr-IN": "Marathi",
    "pa-IN": "Punjabi",
    "gu-IN": "Gujarati"
}

BLACKLIST = ["Shanthi Appuram Nithya", "Drogam: Nadanthathu Enna?", "Anaagarigam", "Amma Ponnu"]

def setup_normalized_tables():
    # Setup Pricing Tiers
    tiers = [
        ("Premium", 299, "New Release (2024+)"),
        ("Recent", 199, "Recent Hit (2020-2023)"),
        ("Modern", 149, "Modern Essential (2010-2019)"),
        ("Vintage", 99, "Classic Vintage (Pre-2010)")
    ]
    for name, price, desc in tiers:
        if not PricingTier.query.filter_by(name=name).first():
            db.session.add(PricingTier(name=name, price=price, description=desc))
    
    # Setup Languages
    for code, name in LANG_MAP.items():
        if not Language.query.filter_by(code=code).first():
            db.session.add(Language(name=name, code=code))
    
    db.session.commit()

def get_tier_for_year(year_str):
    try:
        year = int(year_str)
        if year >= 2024: return PricingTier.query.filter_by(name="Premium").first()
        if year >= 2020: return PricingTier.query.filter_by(name="Recent").first()
        if year >= 2010: return PricingTier.query.filter_by(name="Modern").first()
        return PricingTier.query.filter_by(name="Vintage").first()
    except:
        return PricingTier.query.filter_by(name="Modern").first()

def fetch_movies(language_code, region, count=100):
    movies = []
    page = 1
    # Get all TMDB genres and ensure they exist in our DB
    genre_url = f"{BASE_URL}/genre/movie/list?api_key={TMDB_API_KEY}&language=en-US"
    tmdb_genres = requests.get(genre_url).json().get('genres', [])
    
    for tg in tmdb_genres:
        if not Genre.query.filter_by(name=tg['name']).first():
            db.session.add(Genre(name=tg['name']))
    db.session.commit()

    original_lang = language_code.split('-')[0]
    lang_obj = Language.query.filter_by(code=language_code).first()

    while len(movies) < count:
        url = f"{BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&language=en-US&region={region}&with_original_language={original_lang}&include_adult=false&sort_by=popularity.desc&page={page}"
        data = requests.get(url).json()
        results = data.get('results', [])
        if not results: break

        for item in results:
            if len(movies) >= count: break
            if item.get('adult') or not item.get('poster_path'): continue
            
            title = item.get('title')
            if any(b.lower() in title.lower() for b in BLACKLIST): continue

            release_date = item.get('release_date', '')
            year_str = release_date[:4] if release_date else "N/A"
            tier = get_tier_for_year(year_str)

            # Get genre objects
            movie_genres = []
            item_genre_ids = item.get('genre_ids', [])
            for tg in tmdb_genres:
                if tg['id'] in item_genre_ids:
                    g_obj = Genre.query.filter_by(name=tg['name']).first()
                    if g_obj: movie_genres.append(g_obj)

            movies.append({
                "title": title,
                "description": item.get('overview'),
                "release_year": year_str,
                "image_url": f"{IMAGE_BASE_URL}{item.get('poster_path')}",
                "language": lang_obj,
                "tier": tier,
                "genres": movie_genres
            })
        page += 1
    return movies

def sync():
    with app.app_context():
        print("Performing 2NF Normalized Sync...")
        # For a clean normalized state, we reset
        db.drop_all()
        db.create_all()
        
        # 1. Setup lookup tables
        setup_normalized_tables()
        
        # 2. Permanent Admin (Re-add because drop_all removed it)
        from werkzeug.security import generate_password_hash
        from models import User
        hashed_pw = generate_password_hash('admin123')
        db.session.add(User(username='admin', password=hashed_pw, is_admin=True))
        
        # 3. Sync Movies
        configs = [("en-US", "US", 70), ("hi-IN", "IN", 70), ("ta-IN", "IN", 70), ("te-IN", "IN", 70),
                   ("ml-IN", "IN", 40), ("kn-IN", "IN", 40), ("bn-IN", "IN", 40), ("mr-IN", "IN", 40),
                   ("pa-IN", "IN", 30), ("gu-IN", "IN", 30)]
        
        total = 0
        for lang_code, reg, count in configs:
            print(f"Fetching {count} {LANG_MAP[lang_code]} movies...")
            movies_data = fetch_movies(lang_code, reg, count)
            for m in movies_data:
                movie = Movie(
                    title=m['title'], description=m['description'],
                    image_url=m['image_url'], release_year=m['release_year'],
                    language=m['language'], tier=m['tier'], genres=m['genres'],
                    available=15
                )
                db.session.add(movie)
                total += 1
            db.session.commit() # Commit after each language batch
            print(f"Saved {count} movies for {LANG_MAP[lang_code]}. Total: {total}")
        
        print(f"Sync Complete! {total} movies normalized into 2NF tables.")

if __name__ == "__main__":
    sync()
