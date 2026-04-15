import json
import requests
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
from django.utils import timezone

User = get_user_model()

# Import scraper functions
from .sites.kaynscan import chapter_pages as kaynscan_chapter_pages
from .sites.kaynscan import search as kaynscan_search_func
from .sites.kaynscan import manga_info as kaynscan_manga_info_func
from .sites.kaynscan import browse_all_manga as kaynscan_browse_func
from .sites.kaynscan import get_all_browse_manga as kaynscan_get_all_browse_func
from .sites.kaynscan import clear_chapter_cache

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
        # Force refresh to get all chapters with new batch loading
        force_refresh = request.GET.get('refresh', 'false').lower() == 'true'
        chapters = kaynscan_manga_info_func(manga_id, force_refresh=force_refresh)
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
    force_refresh = request.GET.get("force_refresh", "false").lower() == "true"
    if not manga_id:
        return Response({"error": "Missing id parameter"}, status=400)

    try:
        chapters = kaynscan_manga_info_func(manga_id, force_refresh=force_refresh)
        return Response(chapters)
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

@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def clear_cache_view(request):
    """Clear chapter cache and end-of-chapter tracking"""
    try:
        clear_chapter_cache()
        return Response({"message": "Cache cleared successfully"})
    except Exception as e:
        return Response({"error": "Failed to clear cache", "details": str(e)}, status=500)

@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def user_login(request):
    """Login endpoint using CustomUser model"""
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=400)

    try:
        # Authenticate directly with email (since USERNAME_FIELD = 'email')
        user = authenticate(request=request, username=email, password=password)

        if user is not None:
            # Check if user is active
            if not user.is_active:
                return Response({"error": "Account is deactivated"}, status=403)

            # Update last_login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            # Get or create token
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            })
        else:
            return Response({"error": "Invalid credentials"}, status=401)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def user_signup(request):
    """Signup endpoint using CustomUser model"""
    email = request.data.get("email")
    password = request.data.get("password")
    confirm_password = request.data.get("confirm_password")

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=400)

    if password != confirm_password:
        return Response({"error": "Passwords do not match"}, status=400)

    if len(password) < 8:
        return Response({"error": "Password must be at least 8 characters"}, status=400)

    try:
        # Check if user with email already exists
        if User.objects.filter(email=email).exists():
            return Response({"error": "User with this email already exists"}, status=400)

        # Create username from email (before @)
        username = email.split('@')[0]
        # Make sure username is unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True
        )

        # Assign to Readers group with permissions
        from .models import setup_groups_and_permissions
        readers_group, _ = setup_groups_and_permissions()
        user.groups.add(readers_group)

        # Create token
        token = Token.objects.create(user=user)

        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        }, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """Get user reading statistics"""
    user = request.user
    return Response({
        "total_read": user.total_read,
        "last_read": user.last_read_date,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "library_size": len(user.library) if user.library else 0,
        "reading_streak": user.reading_streak,
        "reading_days": user.reading_days if user.reading_days else []
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_to_reading_history(request):
    """Add manga to reading history"""
    user = request.user
    manga_data = request.data

    # Add to reading history
    if not user.reading_history:
        user.reading_history = []

    # Check if already in history
    manga_id = manga_data.get('manga_id')
    existing_index = None
    for i, item in enumerate(user.reading_history):
        if item.get('manga_id') == manga_id:
            existing_index = i
            break

    if existing_index is not None:
        # Update existing entry
        user.reading_history[existing_index] = {
            **user.reading_history[existing_index],
            **manga_data,
            'last_read': timezone.now().isoformat()
        }
    else:
        # Add new entry
        user.reading_history.append({
            **manga_data,
            'added_at': timezone.now().isoformat(),
            'last_read': timezone.now().isoformat()
        })

    # Update last_read_at
    user.last_read_at = timezone.now()
    user.save()

    return Response({
        "message": "Added to reading history",
        "total_read": user.total_read
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_reading_history(request):
    """Get user's reading history"""
    user = request.user
    return Response({
        "history": user.reading_history,
        "total_read": user.total_read
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_to_library(request):
    """Add manga to library"""
    user = request.user
    manga_id = request.data.get('manga_id')

    if not manga_id:
        return Response({"error": "manga_id is required"}, status=400)

    if not user.library:
        user.library = []

    if manga_id not in user.library:
        user.library.append(manga_id)
        user.save()
        return Response({
            "message": "Added to library",
            "library_size": len(user.library)
        })
    else:
        return Response({"message": "Already in library"}, status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_library(request):
    """Get user's library"""
    user = request.user
    return Response({
        "library": user.library,
        "library_size": len(user.library)
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_user_data(request):
    """Sync user's reading history and library from localStorage to database"""
    user = request.user
    history = request.data.get('history', [])
    library = request.data.get('library', [])

    # Merge history - avoid duplicates by mangaId (camelCase from frontend)
    if not user.reading_history:
        user.reading_history = []

    existing_manga_ids = {item.get('mangaId') or item.get('manga_id') for item in user.reading_history}
    new_history = []

    for item in history:
        manga_id = item.get('mangaId') or item.get('manga_id')
        if manga_id and manga_id not in existing_manga_ids:
            new_history.append(item)
            existing_manga_ids.add(manga_id)

    user.reading_history.extend(new_history)

    # Merge library - store full objects instead of just IDs
    if not user.library:
        user.library = []

    # Get IDs from incoming library
    incoming_ids = set()
    for item in library:
        if isinstance(item, dict):
            manga_id = item.get('id')
            if manga_id:
                incoming_ids.add(str(manga_id))
        elif isinstance(item, str):
            incoming_ids.add(item)

    # Remove items from database that are not in incoming library
    user.library = [
        lib_item for lib_item in user.library
        if str(lib_item.get('id') if isinstance(lib_item, dict) else lib_item) in incoming_ids
    ]

    # Add/update items from incoming library
    for item in library:
        # Store full manga objects
        if isinstance(item, dict):
            manga_id = item.get('id')
            if manga_id:
                # Check if already exists by id
                existing_index = None
                for i, existing in enumerate(user.library):
                    if isinstance(existing, dict) and existing.get('id') == manga_id:
                        existing_index = i
                        break

                if existing_index is not None:
                    # Update existing
                    user.library[existing_index] = item
                else:
                    # Add new
                    user.library.append(item)
        elif isinstance(item, str):
            # Handle legacy string IDs - wrap in object
            if item not in [str(lib_item.get('id')) if isinstance(lib_item, dict) else str(lib_item) for lib_item in user.library]:
                user.library.append({'id': item})

    # Update last_read_at if there's history
    if user.reading_history:
        # Find the most recent last_read timestamp
        latest_read = None
        for item in user.reading_history:
            last_read = item.get('lastReadAt') or item.get('last_read')
            if last_read:
                if latest_read is None or last_read > latest_read:
                    latest_read = last_read

        if latest_read:
            from datetime import datetime
            if isinstance(latest_read, str):
                user.last_read_at = datetime.fromisoformat(latest_read.replace('Z', '+00:00'))
            else:
                user.last_read_at = datetime.fromtimestamp(latest_read / 1000)

    # Update total_read_count
    user.total_read_count = len(user.reading_history)

    # Calculate reading streak
    from datetime import datetime, timedelta
    if user.reading_history:
        # Get unique reading dates from history
        dates = []
        for item in user.reading_history:
            last_read = item.get('lastReadAt') or item.get('last_read')
            if last_read:
                if isinstance(last_read, str):
                    date = datetime.fromisoformat(last_read.replace('Z', '+00:00'))
                else:
                    date = datetime.fromtimestamp(last_read / 1000)
                date_str = date.date().isoformat()
                if date_str not in dates:
                    dates.append(date_str)
        
        dates.sort()
        user.reading_days = dates

        # Calculate current streak
        today = datetime.now().date()
        current_streak = 0
        check_date = today
        
        for i in range(365):
            date_str = check_date.isoformat()
            if date_str in dates:
                current_streak += 1
                check_date -= timedelta(days=1)
            elif i == 0:
                # If today hasn't been read yet, check yesterday
                check_date -= timedelta(days=1)
                yesterday_str = check_date.isoformat()
                if yesterday_str in dates:
                    check_date -= timedelta(days=1)
                    continue
                break
            else:
                break
        
        user.reading_streak = current_streak
        user.last_streak_update = datetime.now()

    user.save()

    return Response({
        "message": "Sync successful",
        "history_added": len(new_history),
        "library_added": len([item for item in library if isinstance(item, dict) and item.get('id') not in [lib_item.get('id') if isinstance(lib_item, dict) else None for lib_item in user.library]]),
        "total_history": len(user.reading_history),
        "total_library": len(user.library),
        "total_read": user.total_read_count,
        "reading_streak": user.reading_streak
    })
