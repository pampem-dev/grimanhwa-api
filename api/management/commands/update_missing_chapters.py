from django.core.management.base import BaseCommand
from api.models import Manga
from api.sites.kaynscan import lightweight_manga_update
import time

class Command(BaseCommand):
    help = 'Update chapter counts only for manga with chapter_count = 0 (for initial setup)'

    def handle(self, *args, **options):
        self.stdout.write("Starting chapter update for manga with chapter_count = 0 (incremental)...")
        self.stdout.write("=" * 50)

        # Get only manga with chapter_count = 0
        # Sort by last_updated to prioritize stale manga
        # Limit to 150 per run for Railway free tier
        manga_to_update = Manga.objects.filter(
            chapter_count=0
        ).order_by('last_updated')[:150]

        total = manga_to_update.count()
        total_zero = Manga.objects.filter(chapter_count=0).count()
        self.stdout.write(f"Found {total_zero} manga with chapter_count = 0 (updating {total} this run, max 150)")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All manga already have chapter counts!"))
            return

        updated_count = 0
        failed_count = 0
        total_new_chapters = 0

        # Update each manga
        for i, manga in enumerate(manga_to_update, 1):
            self.stdout.write(f"\n[{i}/{total}] Updating: {manga.title}")

            try:
                # Lightweight update - fetches new chapters only
                chapter_count, status, new_chapters = lightweight_manga_update(manga.url, manga)

                if chapter_count is not None:
                    manga.chapter_count = chapter_count
                    manga.status = status
                    manga.save()

                    if new_chapters > 0:
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Total: {chapter_count} chapters, +{new_chapters} new, Status: {status}"))
                        total_new_chapters += new_chapters
                    else:
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Total: {chapter_count} chapters, Status: {status}"))
                    updated_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"  ✗ Failed to fetch"))
                    failed_count += 1

                # Add delay to avoid overwhelming the server
                time.sleep(0.2)  # Faster for initial setup

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                failed_count += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Incremental update complete!"))
        self.stdout.write(f"✓ Updated: {updated_count}/{total}")
        self.stdout.write(f"✗ Failed: {failed_count}")
        self.stdout.write(f"📖 New chapters fetched: {total_new_chapters}")
        self.stdout.write(f"⏱️  Remaining manga with chapter_count = 0: {max(0, total_zero - 150)}")
