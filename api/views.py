import json
import requests
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse

# Import scraper functions
from .sites.kaynscan import chapter_pages as kaynscan_chapter_pages
from .sites.kaynscan import search as kaynscan_search_func
from .sites.kaynscan import manga_info as kaynscan_manga_info_func
from .sites.kaynscan import browse_all_manga as kaynscan_browse_func
from .sites.kaynscan import get_all_browse_manga as kaynscan_get_all_browse_func

SCRAPER_TIMEOUT = 30

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def search(request):
    query = request.GET.get("q")
    page = request.GET.get("page", 1)
    if not query:
        return Response({"manga": []})

    try:
        data = kaynscan_search_func(query, page)
        return Response(data)
    except Exception as e:
        return Response({"error": "Scraper failed", "details": str(e)}, status=503)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def manhwa(request):
    manga_id = request.GET.get("id")
    if not manga_id:
        return Response({"error": "Missing id parameter"}, status=400)

    try:
        chapters = kaynscan_manga_info_func(manga_id)
        return Response({"chapters": chapters})
    except Exception as e:
        return Response({"error": "Scraper failed", "details": str(e)}, status=503)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def chapters(request, manga_id):
    try:
        chapters = kaynscan_manga_info_func(manga_id)
        return Response({"chapters": chapters})
    except Exception as e:
        return Response({"error": "Scraper failed", "details": str(e)}, status=503)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def pages(request, manga_id, chapter_id):
    try:
        pages = kaynscan_chapter_pages(f"{manga_id}/{chapter_id}")
        return Response({"pages": pages})
    except Exception as e:
        return Response({"error": "Scraper failed", "details": str(e)}, status=503)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def proxy_image(request):
    """Proxy image requests to avoid CORS/ORB issues."""
    img_url = request.GET.get("url")
    if not img_url:
        return Response({"error": "Missing url parameter"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        r = requests.get(img_url, timeout=10, stream=True)
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "image/jpeg")
        response = HttpResponse(r.content, content_type=content_type)
        # Allow cross-origin
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    except Exception as e:
        return Response({"error": f"Proxy failed: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def kaynscan_search(request):
    """Search for manga on Kaynscan"""
    query = request.GET.get("q")
    page = request.GET.get("page", 1)
    if not query:
        return Response({"manga": []})

    try:
        data = kaynscan_search_func(query, page)
        return Response(data)
    except Exception as e:
        return Response({"error": "Scraper failed", "details": str(e)}, status=503)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def kaynscan_manga_info_view(request):
    """Get manga info from Kaynscan"""
    manga_id = request.GET.get("id")
    if not manga_id:
        return Response({"error": "Missing id parameter"}, status=400)

    try:
        chapters = kaynscan_manga_info_func(manga_id)
        return Response({"chapters": chapters})
    except Exception as e:
        return Response({"error": "Scraper failed", "details": str(e)}, status=503)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def kaynscan_chapter_pages_view(request, chapter_id):
    """Get chapter pages from Kaynscan"""
    try:
        pages = kaynscan_chapter_pages(chapter_id)
        return Response({"pages": pages})
    except Exception as e:
        return Response({"error": "Scraper failed", "details": str(e)}, status=503)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def browse_manga(request):
    """Browse manga from AsuraScans with pagination"""
    page = request.GET.get("page", 1)
    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1
    
    try:
        data = kaynscan_browse_func(page)
        return Response(data)
    except Exception as e:
        return Response({"error": "Scraper failed", "details": str(e)}, status=503)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def browse_all_manga(request):
    """Get all manga from all browse pages"""
    try:
        data = kaynscan_get_all_browse_func()
        return Response(data)
    except Exception as e:
        return Response({"error": "Scraper failed", "details": str(e)}, status=503)
