from flask import Flask, request, jsonify
import google.generativeai as genai
import requests
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)
# --- API Keys ---
TMDB_API_KEY = "a4a5a039e8224a86d2f82222f8b2f52c"
GENAI_API_KEY = "AIzaSyAVVwiavHqonUYDgn_WBAlzpO-y4N43Ay4"  # 👈 Replace with your key

# --- Configure Gemini ---
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# --- TMDB API FUNCTIONS ---

def search_movies(query: str, year: str = None):
    """Search for movies by title"""
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        'api_key': TMDB_API_KEY,
        'query': query,
        'year': year
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            movies = []
            for movie in data['results'][:3]:
                movies.append({
                    'title': movie.get('title', 'N/A'),
                    'release_date': movie.get('release_date', 'N/A'),
                    'overview': movie.get('overview', 'No description available'),
                    'rating': movie.get('vote_average', 'N/A')
                })
            return movies
        return "No movies found"
    return f"Error searching movies: {response.status_code}"

def get_movie_details(movie_id: int):
    """Get detailed information about a specific movie"""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {'api_key': TMDB_API_KEY}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        movie = response.json()
        return {
            'title': movie.get('title', 'N/A'),
            'release_date': movie.get('release_date', 'N/A'),
            'runtime': movie.get('runtime', 'N/A'),
            'genres': [genre['name'] for genre in movie.get('genres', [])],
            'rating': movie.get('vote_average', 'N/A'),
            'overview': movie.get('overview', 'No description available'),
            'budget': movie.get('budget', 'N/A'),
            'revenue': movie.get('revenue', 'N/A')
        }
    return f"Error fetching movie details: {response.status_code}"

def get_popular_movies(genre: str = None):
    """Get currently popular movies, optionally filtered by genre"""
    url = "https://api.themoviedb.org/3/movie/popular"
    params = {'api_key': TMDB_API_KEY}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        movies = []

        for movie in data['results'][:5]:
            if genre:
                details = get_movie_details(movie['id'])
                if genre.lower() in [g.lower() for g in details.get('genres', [])]:
                    movies.append({
                        'title': movie.get('title', 'N/A'),
                        'release_date': movie.get('release_date', 'N/A'),
                        'rating': movie.get('vote_average', 'N/A')
                    })
            else:
                movies.append({
                    'title': movie.get('title', 'N/A'),
                    'release_date': movie.get('release_date', 'N/A'),
                    'rating': movie.get('vote_average', 'N/A')
                })
        return movies if movies else "No popular movies found"
    return f"Error fetching popular movies: {response.status_code}"

def get_movie_recommendations(movie_title: str):
    """Get movie recommendations based on a title"""
    movie_id = search_movie_id(movie_title)
    if not movie_id:
        return "Movie not found"

    url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations"
    params = {'api_key': TMDB_API_KEY}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        recommendations = []
        for movie in data['results'][:5]:
            recommendations.append({
                'title': movie.get('title', 'N/A'),
                'release_date': movie.get('release_date', 'N/A'),
                'rating': movie.get('vote_average', 'N/A'),
                'overview': movie.get('overview', 'No description available')[:200] + "..."
            })
        return recommendations
    return f"Error fetching recommendations: {response.status_code}"

def search_movie_id(movie_title: str):
    """Helper function to get movie ID"""
    url = "https://api.themoviedb.org/3/search/movie"
    params = {'api_key': TMDB_API_KEY, 'query': movie_title}
    response = requests.get(url, params=params)
    if response.status_code == 200 and response.json()['results']:
        return response.json()['results'][0]['id']
    return None


# --- FLASK ROUTES ---

@app.route("/")
def home():
    return "🎬 Movie Chatbot Flask API is running!"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("query", "")

    if not user_input:
        return jsonify({"error": "Missing 'query' field"}), 400

    try:
        # Ask Gemini for a response
        response = model.generate_content(user_input)
        reply = response.text

        # You can optionally parse keywords to trigger TMDB functions
        if "popular movies" in user_input.lower():
            tmdb_data = get_popular_movies()
            return jsonify({"reply": reply, "popular_movies": tmdb_data})
        elif "recommend" in user_input.lower():
            title = user_input.replace("recommend", "").strip()
            tmdb_data = get_movie_recommendations(title)
            return jsonify({"reply": reply, "recommendations": tmdb_data})

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- RUN APP LOCALLY ---
if __name__ == "__main__":
    app.run(debug=True)
