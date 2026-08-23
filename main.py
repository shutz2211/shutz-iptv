from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

app = FastAPI()

# Permitir conexiones desde Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@app.get("/catalog")
def get_catalog():
    """Rasca la lista de películas/series o devuelve un catálogo demo si no hay resultados."""
    try:
        url = "https://vidsrc.to"
        response = requests.get(url, headers=HEADERS, timeout=5)
        
        if response.status_code != 200:
            return get_fallback_catalog()

        soup = BeautifulSoup(response.text, 'html.parser')
        catalog = []
        items = soup.select('.card, .item, .movie-item')

        for item in items[:15]:
            title_el = item.select_one('.title, h2, h3, .name')
            img_el = item.select_one('img')

            if title_el and img_el:
                title = title_el.get_text(strip=True)
                poster = img_el.get('src') or img_el.get('data-src') or ''
                
                if poster.startswith('/'):
                    poster = f"https://vidsrc.to{poster}"

                catalog.append({
                    "title": title,
                    "type": "movie",
                    "poster": poster,
                    "stream_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                    "headers": {
                        "User-Agent": HEADERS["User-Agent"],
                        "Referer": url
                    }
                })

        return catalog if catalog else get_fallback_catalog()

    except Exception as e:
        print(f"Error en scraping: {e}")
        return get_fallback_catalog()


def get_fallback_catalog():
    return [
        {
            "title": "Big Buck Bunny (Demo HLS)",
            "type": "movie",
            "poster": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_buck_bunny_poster_big.jpg/800px-Big_buck_bunny_poster_big.jpg",
            "stream_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
            "headers": {"User-Agent": "Mozilla/5.0"}
        },
        {
            "title": "Sintel (Demo HLS)",
            "type": "movie",
            "poster": "https://upload.wikimedia.org/wikipedia/commons/Sintel_poster.jpg",
            "stream_url": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8",
            "headers": {"User-Agent": "Mozilla/5.0"}
        }
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)