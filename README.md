# NyaaSi-API-Python (Python Port + REST API)

A high-performance, **pure-Python** rewrite of the [Java NyaaSi-API](https://github.com/aki-ks/NyaaSi-API). This project provides a robust, containerized REST API that mirrors the [Nyaa-API](https://github.com/Vivek-Kolhe/Nyaa-API) structure while offering faster execution and native Python async potential.

Scrapes **https://nyaa.si/** and **https://sukebei.nyaa.si/** directly.

---

### Features

- **Dual Scraper Support**: Seamlessly search both [nyaa.si](https://nyaa.si/) and [sukebei.nyaa.si](https://sukebei.nyaa.si/).
- **Full REST Implementation**: Includes search, user uploads, and detailed torrent lookups.
- **Standardized Output**: Returns consistent JSON schemas for easy integration: `{"count": X, "data": [...]}`.
- **Interactive Documentation**: Built-in Swagger UI and Redoc support via FastAPI.
- **Microservice Ready**: Containerized with Docker and Docker Compose.

---

### Getting Started

#### Docker (Recommended)
The easiest way to get the API up and running is via Docker Compose.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/Sukebei-API-Python.git
   cd Sukebei-API-Python
   ```
2. **Start the service**:
   ```bash
   docker-compose up -d
   ```
3. **Access the API**:
   - **Documentation**: [http://localhost:8383/docs](http://localhost:8383/docs)
   - **Base URL**: `http://localhost:8383`

#### Local Setup
If you prefer to run it manually without Docker:

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```bash
   # Using uvicorn directly
   python -m uvicorn main:app --host 0.0.0.0 --port 8383
   ```

---

### API Reference

#### Search
`GET /nyaa` or `GET /sukebei`

| Parameter | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `q` | `str` | The search query string. | `Sword Art Online` |
| `category` | `str` | Main category filter (see Taxonomy table). | `anime` |
| `sub_category` | `str` | Detailed subcategory filter. | `english` |
| `sort` | `str` | Sort by: `comments`, `size`, `date`, `seeders`, `leechers`, `downloads`. | `seeders` |
| `order` | `str` | Sorting order: `asc` or `desc`. | `desc` |
| `page` | `int` | Pagination page number. | `1` |

#### Torrent Lookup
`GET /nyaa/id/{torrent_id}` or `GET /sukebei/id/{torrent_id}`

Fetches full details including description, magnet link, hash, and file structure.

#### User Search
`GET /nyaa/user/{user_name}` or `GET /sukebei/user/{user_name}`

Search for torrents uploaded by a specific user. Supports the same query parameters as the global search.

---

### Taxonomy Reference

| Site | Categories | Subcategories |
| :--- | :--- | :--- |
| **Nyaa** | `anime`, `audio`, `literature`, `live_action`, `pictures`, `software` | `english`, `raw`, `non-english`, `lossless`, `lossy` |
| **Sukebei** | `art`, `real` | `anime`, `doujinshi`, `games`, `manga`, `pictures`, `photobooks`, `videos` |

---

### Disclaimer
This project is for educational and research purposes only. The API solely scrapes publicly available metadata from third-party websites and does **not** host, store, or distribute any torrent files or copyrighted content itself.

---

### License
[GPL-3.0 License](LICENSE)