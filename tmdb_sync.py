import requests
from app import app, db, Movie

TMDB_API_KEY = "e528bd8a8676e863cd592e38f8bb91d7"
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

BLACKLIST = [
    "Shanthi Appuram Nithya", 
    "Drogam: Nadanthathu Enna?", 
    "Anaagariyam", 
    "Anaagarigam",
    "Nithya",
    "Shanthi",
    "Drogam",
    "Amma Ponnu"
]

def calculate_price(year_str):
    try:
        year = int(year_str)
        if year >= 2024:
            return 299 # Premium New Release
        elif year >= 2020:
            return 199 # Blockbuster Recent
        elif year >= 2010:
            return 149 # Modern Essential
        else:
            return 99  # Classic Vintage
    except:
        return 179 # Default Premium price

def fetch_movies(language_code, region, count=100):
    movies = []
    page = 1
    genre_url = f"{BASE_URL}/genre/movie/list?api_key={TMDB_API_KEY}&language=en-US"
    genres_resp = requests.get(genre_url).json()
    genre_map = {g['id']: g['name'] for g in genres_resp.get('genres', [])}

    original_lang = language_code.split('-')[0]

    while len(movies) < count:
        url = (f"{BASE_URL}/discover/movie?api_key={TMDB_API_KEY}"
               f"&language=en-US" 
               f"&region={region}"
               f"&with_original_language={original_lang}"
               f"&include_adult=false" 
               f"&sort_by=popularity.desc"
               f"&page={page}")
        
        response = requests.get(url)
        if response.status_code != 200:
            break
        
        data = response.json()
        results = data.get('results', [])
        if not results:
            break

        for item in results:
            if len(movies) >= count:
                break
            
            if item.get('adult'):
                continue
                
            title = item.get('title')
            if any(b.lower() in title.lower() for b in BLACKLIST):
                continue

            if not item.get('poster_path'):
                continue
                
            movie_genres = [genre_map.get(gid) for gid in item.get('genre_ids', []) if genre_map.get(gid)]
            genre_str = ", ".join(movie_genres) if movie_genres else "Drama"

            release_date = item.get('release_date', '')
            year_str = release_date[:4] if release_date else "N/A"
            price = calculate_price(year_str)

            movies.append({
                "title": title,
                "description": item.get('overview'),
                "genre": genre_str,
                "language": LANG_MAP.get(language_code, "Other"),
                "release_year": year_str,
                "price": price,
                "image_url": f"{IMAGE_BASE_URL}{item.get('poster_path')}",
                "available": 15
            })
        page += 1
        
        if page > 5 and len(movies) < count:
            url = (f"{BASE_URL}/discover/movie?api_key={TMDB_API_KEY}"
                   f"&language=en-US" 
                   f"&region={region}"
                   f"&with_original_language={original_lang}"
                   f"&include_adult=false"
                   f"&sort_by=vote_count.desc"
                   f"&page={page - 5}")
            
    return movies

def sync():
    with app.app_context():
        print("Recreating database schema with Pricing logic...")
        db.drop_all()
        db.create_all()
        
        configs = [
            ("en-US", "US", 70),
            ("hi-IN", "IN", 70),
            ("ta-IN", "IN", 70),
            ("te-IN", "IN", 70),
            ("ml-IN", "IN", 40),
            ("kn-IN", "IN", 40),
            ("bn-IN", "IN", 40),
            ("mr-IN", "IN", 40),
            ("pa-IN", "IN", 30),
            ("gu-IN", "IN", 30)
        ]
        
        total_synced = 0
        for lang, reg, count in configs:
            lang_name = LANG_MAP.get(lang)
            print(f"Syncing {lang_name} movies with pricing...")
            movies_data = fetch_movies(lang, reg, count)
            
            for m_data in movies_data:
                exists = Movie.query.filter_by(title=m_data['title']).first()
                if not exists:
                    movie = Movie(
                        title=m_data['title'],
                        description=m_data['description'],
                        genre=m_data['genre'],
                        language=m_data['language'],
                        release_year=m_data['release_year'],
                        price=m_data['price'],
                        image_url=m_data['image_url'],
                        available=m_data['available']
                    )
                    db.session.add(movie)
                    total_synced += 1
        
        db.session.commit()
        print(f"Successfully synced {total_synced} movies with tiered pricing!")

if __name__ == "__main__":
    sync()
