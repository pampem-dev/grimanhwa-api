# Grimanhwa Backend

A Python Django backend API that scrapes and serves manga data from AsuraScans, providing chapter lists, descriptions, status, and alternative titles for the Grimanhwa frontend application.

##  API Endpoints

### Get All Manga (Browse)
```
GET /api/kaynscan/browse/?page={page}
```
- **Parameters**: `page` (optional, default: 1)
- **Returns**: List of manga with basic info

### Get Manga Details
```
GET /api/kaynscan/manga/?id={manga_id}
```
- **Parameters**: `manga_id` (required)
- **Returns**: 
  ```json
  {
    "chapters": [...],
    "description": "...",
    "status": "ongoing|completed|hiatus",
    "alternative_titles": [...]
  }
  ```

### Get Chapter Images
```
GET /api/kaynscan/chapter/
```
- **Parameters**: Sent in request body
- **Returns**: Chapter image URLs

## 🔗 Links

- **Frontend**: https://github.com/pampem-dev/grimanhwa

