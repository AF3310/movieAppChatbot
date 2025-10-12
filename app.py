from flask import Flask, request, jsonify
import requests
import json
from flask_cors import CORS
from google.genai import Client, types # Using the correct Client and types import

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# --- API Keys ---
# NOTE: Replace 'AIzaSy...' with your actual key if you run this outside of a secured environment.
TMDB_API_KEY = "a4a5a039e8224a86d2f82222f8b2f52c"
GENAI_API_KEY = "AIzaSyAVVwiavHqonUYDgn_WBAlzpO-y4N43Ay4"

# --- Configure Gemini with new SDK ---
client = Client(api_key=GENAI_API_KEY)


# --- TMDB API FUNCTIONS ---

def search_movies(query: str, year: str = None):
    """Search for movies by title and optional release year. Returns title, release date, overview, and rating for up to 3 results."""
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
        return f"No movies found for '{query}'"
    return f"Error searching movies: {response.status_code}"

def get_movie_details(movie_id: int):
    """
    Get detailed information about a specific movie using its ID. 
    NOTE: This function is complex for single-turn chat and is not enabled for function calling, 
    but kept for reference/future use.
    """
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
    """Get the top 5 currently popular movies, optionally filtering by genre."""
    url = "https://api.themoviedb.org/3/movie/popular"
    params = {'api_key': TMDB_API_KEY}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        movies = []
        
        # Only fetch the first 10 for quick processing, then filter down to 5
        results_to_process = data['results'][:10] 

        for movie in results_to_process:
            # If a genre filter is provided, we must get full details to check genres
            if genre and movies and len(movies) >= 5: 
                break # Stop if we already have 5 results

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
        
        final_movies = movies[:5]
        return final_movies if final_movies else f"No popular movies found for genre '{genre}'"
    return f"Error fetching popular movies: {response.status_code}"

def get_movie_recommendations(movie_title: str):
    """Get movie recommendations based on a specific movie title. Returns title, release date, rating, and a short overview for up to 5 recommendations."""
    movie_id = search_movie_id(movie_title)
    if not movie_id:
        return f"Movie '{movie_title}' not found in the database for recommendations."

    url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations"
    params = {'api_key': TMDB_API_KEY}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        recommendations = []
        for movie in data['results'][:5]:
            recommendations.append({
                'title': movie.get('title', 'N/A'),
                'id': movie.get('id', 'N/A'),
                'key': movie.get('id', 'N/A'),
                'release_date': movie.get('release_date', 'N/A'),
                'rating': movie.get('vote_average', 'N/A'),
                'poster_path': movie.get('poster_path', 'N/A'),
                'overview': movie.get('overview', 'No description available')[:200] + "..."
            })
        return recommendations
    return f"Error fetching recommendations: {response.status_code}"

def search_movie_id(movie_title: str):
    """Helper function to get movie ID based on title."""
    url = "https://api.themoviedb.org/3/search/movie"
    params = {'api_key': TMDB_API_KEY, 'query': movie_title}
    response = requests.get(url, params=params)
    if response.status_code == 200 and response.json()['results']:
        return response.json()['results'][0]['id']
    return None

# --- Function Map and Tool Definitions for Gemini ---

# Map the function names (as strings) to the actual Python callables
# --- Function Map and Tool Definitions for Gemini ---

# Map the function names (as strings) to the actual Python callables
FUNCTION_MAP = {
    'search_movies': search_movies,
    'get_popular_movies': get_popular_movies,
    'get_movie_recommendations': get_movie_recommendations,
}

# Define the tools the model can use with proper function declarations
tmdb_tools = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name='search_movies',
                description='Search for movies by title and optional release year. Returns title, release date, overview, and rating for up to 3 results.',
                parameters={
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': 'The movie title to search for'
                        },
                        'year': {
                            'type': 'string',
                            'description': 'Optional release year to filter results'
                        }
                    },
                    'required': ['query']
                }
            ),
            types.FunctionDeclaration(
                name='get_popular_movies',
                description='Get the top 5 currently popular movies, optionally filtering by genre.',
                parameters={
                    'type': 'object',
                    'properties': {
                        'genre': {
                            'type': 'string',
                            'description': 'Optional genre to filter popular movies (e.g., Action, Comedy, Drama)'
                        }
                    }
                }
            ),
            types.FunctionDeclaration(
                name='get_movie_recommendations',
                description='Get movie recommendations based on a specific movie title. Returns title, release date, rating, and a short overview for up to 5 recommendations.',
                parameters={
                    'type': 'object',
                    'properties': {
                        'movie_title': {
                            'type': 'string',
                            'description': 'The movie title to base recommendations on'
                        }
                    },
                    'required': ['movie_title']
                }
            )
        ]
    )
]
# --- FLASK ROUTES ---

@app.route("/")
def home():
    return "🎬 Movie Chatbot Flask API is running! Use the /chat endpoint to talk to the bot."

@app.route("/chat", methods=["POST"])
def chat():
    
    data = request.get_json()
    user_input = data.get("query", "")

    if not user_input:
        return jsonify({"error": "Missing 'query' field"}), 400

    try:
        print(f"--- Received query: {user_input} ---")

        # 1. First Turn: Send user query to the model with tools enabled
        initial_response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=user_input,
            config=types.GenerateContentConfig(tools=tmdb_tools)
        )

        # Check if the model requested a function call
        if initial_response.function_calls:
            print(f"Model requested {len(initial_response.function_calls)} function call(s).")
            function_responses = []
            tmdb_data = None # Store the data from the first successful function call

            for function_call in initial_response.function_calls:
                function_name = function_call.name
                args = dict(function_call.args)

                if function_name in FUNCTION_MAP:
                    print(f"Executing function: {function_name} with args: {args}")
                    
                    # Execute the actual Python function
                    function_to_call = FUNCTION_MAP[function_name]
                    function_output = function_to_call(**args)
                    
                    tmdb_data = function_output # Store the data
                    print(tmdb_data, " TMDB DATA RETURNED")
                    # Prepare the response part for the model
                    function_responses.append(types.Part.from_function_response(
                        name=function_name,
                        response={"result": function_output}
                    ))
                else:
                    print(f"Error: Unknown function requested: {function_name}")
                    function_responses.append(types.Part.from_function_response(
                        name=function_name,
                        response={"result": f"Error: Unknown function {function_name}"}
                    ))

            # 2. Second Turn: Send the function results back to the model
            print("Sending function results back to the model for final text response.")
            
            # Create a history for the second turn
            print(function_responses, " rsponse from api")
            chat_history = [
                types.Content(role="user", parts=[types.Part.from_text(text=user_input)]),
                types.Content(role="model", parts=initial_response.parts), # Model's function call request
                types.Content(role="tool", parts=function_responses) # Tool's response (data)
            ]
            
            final_response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=chat_history
            )
            
            final_reply = final_response.text
            
            print(f"--- Final reply: {final_reply[:50]}... ---")
    # final_reply= "testing api"
    # tmdb_data=get_movie_recommendations(user_input)
    # print(tmdb_data[4])
            # Return the model's formatted text reply and the raw data
            return jsonify({"reply": final_reply, "data": tmdb_data})
        
        else:
            # 3. No function call, return the model's text response directly
            print("Model generated direct text response (no tool needed).")
            return jsonify({"reply": initial_response.text, "data": None})

    except Exception as e:
        import traceback
        print("Chat endpoint exception:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- RUN APP LOCALLY ---
if __name__ == "__main__":
    app.run(debug=True)

