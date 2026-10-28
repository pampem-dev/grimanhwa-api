import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Manga
from api.sites.kaynscan import manga_info

def update_all_chapter_counts():
    """Update chapter counts for all manga in the database (incremental approach)"""
    print("Starting incremental chapter count update...")
    print("=" * 50)

    # Get only ongoing/hiatus manga with chapter_count = 0
    # Sort by last_updated to prioritize stale manga
    # Limit to 150 per run for Railway free tier
    manga_to_update = Manga.objects.filter(
        chapter_count=0,
        status__in=['ongoing', 'hiatus', 'Unknown']
    ).order_by('last_updated')[:150]

    total = manga_to_update.count()
    total_in_db = Manga.objects.count()
    ongoing_count = Manga.objects.filter(status='ongoing').count()
    completed_count = Manga.objects.filter(status='completed').count()

    print(f"Total manga in DB: {total_in_db}")
    print(f"Ongoing: {ongoing_count} | Completed: {completed_count}")
    print(f"Updating {total} manga with chapter_count = 0 (oldest first, limited to 150)")

    if total == 0:
        print("All ongoing manga already have chapter counts!")
        return

    # Update each manga
    for i, manga in enumerate(manga_to_update, 1):
        print(f"\n[{i}/{total}] Updating: {manga.title}")
        print(f"  URL: {manga.url}")

        try:
            # Fetch manga info (this will update chapter count in database)
            result = manga_info(manga.url, force_refresh=True)

            if result and 'chapters' in result:
                chapter_count = len(result['chapters'])
                print(f"  ✓ Found {chapter_count} chapters")
            else:
                print(f"  ✗ Failed to fetch chapters")

            # Reduced delay since we're limiting to 100 manga per run
            time.sleep(0.5)

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print("\n" + "=" * 50)
    print("Incremental chapter count update complete!")

    # Show updated stats
    updated_count = Manga.objects.filter(chapter_count__gt=0).count()
    still_zero = Manga.objects.filter(chapter_count=0).count()
    print(f"Manga with chapter counts: {updated_count}")
    print(f"Manga still at 0: {still_zero}")
    print(f"ℹ️  Completed manga skipped: {completed_count}")
    print(f"⏱️  Remaining ongoing manga to process: {max(0, ongoing_count - 150)}")

if __name__ == '__main__':
    update_all_chapter_counts()
