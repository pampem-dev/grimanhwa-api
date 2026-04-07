from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search),
    path('manhwa/', views.manhwa),
    path('manga/<str:manga_id>/', views.chapters),
    path('chapter/<path:manga_id>/<path:chapter_id>/', views.pages),
    path('proxy-image/', views.proxy_image),
    path('kaynscan/search/', views.kaynscan_search),
    path('kaynscan/manga/', views.kaynscan_manga_info_view),
    path('kaynscan/chapter/<path:chapter_id>/', views.kaynscan_chapter_pages_view),
    path('kaynscan/browse/', views.browse_manga),
    path('kaynscan/browse-all/', views.browse_all_manga),
    path('kaynscan/clear-cache/', views.clear_cache_view),
]