from django.core.management.base import BaseCommand
from api.models import Manga
from api.sites.kaynscan import lightweight_manga_update
import time

class Command(BaseCommand):
    help = 'Update chapter counts, status, and fetch new chapters for all manga'

    def handle(self, *args, **options):
        self.stdout.write("Starting chapter update (fetching new chapters only)...")
        self.stdout.write("=" * 50)

        # Get all manga
        all_manga = Manga.objects.all()
        total = all_manga.count()
        self.stdout.write(f"Found {total} manga to update")

        if total == 0:
            self.stdout.write(self.style.WARNING("No manga found in database!"))
            return

        updated_count = 0
        failed_count = 0
        total_new_chapters = 0

        # Update each manga
        for i, manga in enumerate(all_manga, 1):
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
                time.sleep(1)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                failed_count += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Update complete!"))
        self.stdout.write(f"✓ Updated: {updated_count}")
        self.stdout.write(f"✗ Failed: {failed_count}")
        self.stdout.write(f"📖 New chapters fetched: {total_new_chapters}")
