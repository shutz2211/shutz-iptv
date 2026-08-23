def ejecutar_scraper():
    print("[+] Iniciando raspado de Cuevana...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    BASE_URL = "https://cuevana3i.bio"
    
    for page in range(1, 6):
        url = f"{BASE_URL}/peliculas/page/{page}/"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                print(f"[-] Status {res.status_code} en página {page}")
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            items = soup.select("ul.Posters li, article.item, .TPost li")
            
            peli_list = []
            for item in items:
                title_elem = item.select_one(".Title, h2, .entry-title")
                link_elem = item.select_one("a")
                img_elem = item.select_one("img")
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link = link_elem.get("href", "")
                    img = img_elem.get("data-src") or img_elem.get("src", "") if img_elem else ""
                    
                    if link and not link.startswith("http"):
                        link = BASE_URL + link
                        
                    peli = {
                        "title": title,
                        "url": link,
                        "poster": img
                    }
                    
                    movies_collection.update_one({"url": link}, {"$set": peli}, upsert=True)
                    peli_list.append(peli)
                    
            print(f"[+] Página {page} procesada (+{len(peli_list)} películas).")
        except Exception as e:
            print(f"[-] Error en página {page}: {e}")
