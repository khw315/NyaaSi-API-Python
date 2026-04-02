from fastapi import FastAPI, Query, Path, HTTPException
from scraper.api import NyaaSiApi
from scraper.exceptions import NoSuchTorrentException
from scraper.models import (
    SearchRequest, Sort, Ordering, 
    NyaaCategory, SukebeiCategory, Category
)

app = FastAPI(title="Nyaa-API", description="(Unofficial) Nyaa API built with Python", version="1.0.0")

nyaa_api = NyaaSiApi.get_nyaa()
sukebei_api = NyaaSiApi.get_sukebei()

# -------------------------------------------------------------
# Category Mapping
# -------------------------------------------------------------

def map_category(cat_str: str, sub_cat_str: str, is_sukebei: bool) -> Category:
    if not cat_str:
        return None
        
    base = SukebeiCategory if is_sukebei else NyaaCategory
    
    # Simple mapping for Sukebei
    if is_sukebei:
        mappings = {
            "art": SukebeiCategory.ART,
            "real": SukebeiCategory.REAL_LIFE,
            "real_life": SukebeiCategory.REAL_LIFE
        }
        main = mappings.get(cat_str.lower())
        if not main:
            return None
        if not sub_cat_str:
            return main
            
        sub_mappings = {
            "anime": main.ANIME if hasattr(main, "ANIME") else None,
            "doujinshi": main.DOUJINSHI if hasattr(main, "DOUJINSHI") else None,
            "games": main.GAMES if hasattr(main, "GAMES") else None,
            "manga": main.MANGA if hasattr(main, "MANGA") else None,
            "pictures": main.PICTURES if hasattr(main, "PICTURES") else None,
            "photobooks": main.PHOTOBOOKS if hasattr(main, "PHOTOBOOKS") else None,
            "videos": main.VIDEOS if hasattr(main, "VIDEOS") else None
        }
        return sub_mappings.get(sub_cat_str.lower()) or main
    else:
        # Nyaa mappings
        mappings = {
            "anime": NyaaCategory.ANIME,
            "audio": NyaaCategory.AUDIO,
            "literature": NyaaCategory.LITERATURE,
            "live_action": NyaaCategory.LIVE_ACTION,
            "pictures": NyaaCategory.PICTURES,
            "software": NyaaCategory.SOFTWARE
        }
        main = mappings.get(cat_str.lower())
        if not main:
            return None
        if not sub_cat_str:
            return main
            
        # Common subcategories
        s = sub_cat_str.lower()
        if s == "raw": return main.RAW if hasattr(main, "RAW") else main
        if s == "english": return main.ENGLISH if hasattr(main, "ENGLISH") else main
        if s == "non-english": return main.NON_ENGLISH if hasattr(main, "NON_ENGLISH") else main
        if s == "lossless": return main.LOSSLESS if hasattr(main, "LOSSLESS") else main
        if s == "lossy": return main.LOSSY if hasattr(main, "LOSSY") else main
        
        return main

# -------------------------------------------------------------
# Helpers to build request
# -------------------------------------------------------------
def build_request(q: str = None, user_name: str = None, category: str = None, sub_category: str = None, 
                  sort: str = None, order: str = None, page: int = 1, is_sukebei: bool = False) -> SearchRequest:
    req = SearchRequest()
    if q:
        req.set_term(q)
    if user_name:
        req.set_user(user_name)
    if page:
        req.set_page(page)
    
    cat_obj = map_category(category, sub_category, is_sukebei)
    if cat_obj:
        req.set_category(cat_obj)
    
    if sort:
        sort_map = {
            "comments": Sort.COMMENTS,
            "size": Sort.SIZE,
            "id": Sort.DATE,
            "date": Sort.DATE,
            "seeders": Sort.SEEDERS,
            "leechers": Sort.LEECHERS,
            "downloads": Sort.DOWNLOADS
        }
        if sort.lower() in sort_map:
            req.set_sorted_by(sort_map[sort.lower()])
            
    if order:
        if order.lower() == "desc":
            req.set_ordering(Ordering.DESCENDING)
        elif order.lower() == "asc":
            req.set_ordering(Ordering.ASCENDING)
            
    return req

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@app.get("/", tags=["Home"], summary="Home", description="Home Route: Returns app details and health status.")
def home__get():
    return {
        "message": "Welcome to the (Unofficial) Nyaa API",
        "version": "1.0.0",
        "docs": "/docs",
        "license": "GPL-3.0 License"
    }

@app.get("/nyaa", tags=["Search"], summary="Nyaa Category Search", operation_id="nyaa_category_search_nyaa_get")
def search_nyaa(
    q: str = Query(None, description="The search query for torrents.", examples=["sword art online"]),
    category: str = Query(None, description="Filter torrents by category (e.g., anime, audio, literature, pictures, software).", examples=["anime"]),
    sub_category: str = Query(None, description="Filter torrents by subcategory (e.g., english, raw, non-english).", examples=["english"]),
    sort: str = Query(None, description="Sort torrents by a particular attribute (comments, size, date, seeders, leechers, downloads).", examples=["seeders"]),
    order: str = Query(None, description="Order in which torrents should be sorted (asc or desc).", examples=["desc"]),
    page: int = Query(1, description="Page number for pagination.", ge=1, examples=[1])
):
    """Search nyaa.si and return results as JSON"""
    req = build_request(q=q, category=category, sub_category=sub_category, sort=sort, order=order, page=page, is_sukebei=False)
    results = nyaa_api.search(req)
    return results.to_dict()

@app.get("/sukebei", tags=["Search"], summary="Sukebei Category Search", operation_id="sukebei_category_search_sukebei_get")
def search_sukebei(
    q: str = Query(None, description="The search query for torrents.", examples=["MIDA-512"]),
    category: str = Query(None, description="Filter torrents by category (e.g., art, real).", examples=["real"]),
    sub_category: str = Query(None, description="Filter torrents by subcategory (e.g., anime, doujinshi, games, manga, pictures, photobooks, videos).", examples=["videos"]),
    sort: str = Query(None, description="Sort torrents by a particular attribute (comments, size, date, seeders, leechers, downloads).", examples=["downloads"]),
    order: str = Query(None, description="Order in which torrents should be sorted (asc or desc).", examples=["desc"]),
    page: int = Query(1, description="Page number for pagination.", ge=1, examples=[1])
):
    """Search sukebei.nyaa.si and return results as JSON"""
    req = build_request(q=q, category=category, sub_category=sub_category, sort=sort, order=order, page=page, is_sukebei=True)
    results = sukebei_api.search(req)
    return results.to_dict()

@app.get("/nyaa/id/{torrent_id}", tags=["ID Search"], summary="Nyaa Id Search", operation_id="nyaa_id_search_nyaa_id__torrent_id__get")
def get_nyaa_id(torrent_id: int = Path(..., title="Torrent Id", description="The unique numeric ID of the torrent on nyaa.si.", examples=[12345])):
    """Fetch full details (description, information, file list, comments) for a specific Nyaa torrent."""
    try:
        info = nyaa_api.get_torrent_info(torrent_id)
        return info.to_dict()
    except NoSuchTorrentException:
        raise HTTPException(status_code=404, detail="Torrent not found")

@app.get("/sukebei/id/{torrent_id}", tags=["ID Search"], summary="Sukebei Id Search", operation_id="sukebei_id_search_sukebei_id__torrent_id__get")
def get_sukebei_id(torrent_id: int = Path(..., title="Torrent Id", description="The unique numeric ID of the torrent on sukebei.nyaa.si.", examples=[4505820])):
    """Fetch full details (description, information, file list, comments) for a specific Sukebei torrent."""
    try:
        info = sukebei_api.get_torrent_info(torrent_id)
        return info.to_dict()
    except NoSuchTorrentException:
        raise HTTPException(status_code=404, detail="Torrent not found")

@app.get("/nyaa/user/{user_name}", tags=["User Search"], summary="Nyaa User Search", operation_id="nyaa_user_search_nyaa_user__user_name__get")
def search_nyaa_user(
    user_name: str = Path(..., title="User Name", description="The Nyaa user name whose uploads you want to search.", examples=["HorribleSubs"]),
    q: str = Query(None, description="The search query for torrents."),
    category: str = Query(None, description="Filter torrents by category."),
    sub_category: str = Query(None, description="Filter torrents by subcategory."),
    sort: str = Query(None, description="Sort torrents by attribute."),
    order: str = Query(None, description="Sorting order."),
    page: int = Query(1, description="Page number.", ge=1)
):
    """Search for torrents uploaded by a specific user on nyaa.si."""
    req = build_request(q=q, user_name=user_name, category=category, sub_category=sub_category, sort=sort, order=order, page=page, is_sukebei=False)
    results = nyaa_api.search(req)
    return results.to_dict()

@app.get("/sukebei/user/{user_name}", tags=["User Search"], summary="Sukebei User Search", operation_id="sukebei_user_search_sukebei_user__user_name__get")
def search_sukebei_user(
    user_name: str = Path(..., title="User Name", description="The Sukebei user name whose uploads you want to search.", examples=["offkab"]),
    q: str = Query(None, description="The search query for torrents."),
    category: str = Query(None, description="Filter torrents by category."),
    sub_category: str = Query(None, description="Filter torrents by subcategory."),
    sort: str = Query(None, description="Sort torrents by attribute."),
    order: str = Query(None, description="Sorting order."),
    page: int = Query(1, description="Page number.", ge=1)
):
    """Search for torrents uploaded by a specific user on sukebei.nyaa.si."""
    req = build_request(q=q, user_name=user_name, category=category, sub_category=sub_category, sort=sort, order=order, page=page, is_sukebei=True)
    results = sukebei_api.search(req)
    return results.to_dict()
