import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

# API pública de TMDB para traer tendencias/populares en español latino
TMDB_POPULAR_URL = "https://api.themoviedb.org/3/movie/popular?api_key=15d2fd480aa7a47cf35870167339d765&language=es-MX&page=1"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

@app.get("/catalog")
def get_catalog():
    try:
        res = requests.get(TMDB_POPULAR_URL, headers=HEADERS, timeout=8)
        if res.status_code != 200:
            return get_fallback_catalog()

        data = res.json()
        results = data.get("results", [])
        catalog = []

        for movie in results[:20]:
            title = movie.get("title") or movie.get("original_title")
            poster_path = movie.get("poster_path")
            movie_id = movie.get("id")

            if not title or not movie_id:
                continue

            poster = f"{IMAGE_BASE_URL}{poster_path}" if poster_path else ""

            # Reproductor de embed que sirve la película automáticamente por TMDB ID
            stream_url = f"https://vidsrc.cc/v2/embed/movie/{movie_id}?autoPlay=false"

            catalog.append({
                "title": title,
                "type": "movie",
                "poster": poster,
                "stream_url": stream_url,
                "headers": {
                    "User-Agent": HEADERS["User-Agent"]
                }
            })

        return catalog if catalog else get_fallback_catalog()

    except Exception as e:
        print(f"Error cargando catálogo: {e}")
        return get_fallback_catalog()

def get_fallback_catalog():
    return [
        {
            "title": "Big Buck Bunny (Demo HLS)",
            "type": "movie",
            "poster": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_buck_bunny_poster_big.jpg/800px-Big_buck_bunny_poster_big.jpg",
            "stream_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
            "headers": {"User-Agent": HEADERS["User-Agent"]}
        }
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
