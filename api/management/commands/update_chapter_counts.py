from django.core.management.base import BaseCommand
from api.models import Manga
from api.sites.kaynscan import lightweight_manga_update
import time

class Command(BaseCommand):
    help = 'Update chapter counts, status, and fetch new chapters for all manga'

    def handle(self, *args, **options):
        self.stdout.write("Starting incremental chapter update (ongoing/hiatus only)...")
        self.stdout.write("=" * 50)

        # Get only ongoing and hiatus manga (skip completed ones)
        # Sort by last_updated to prioritize stale manga
        # Limit to 150 per run to stay within Railway free tier limits
        all_manga = Manga.objects.filter(
            status__in=['ongoing', 'hiatus', 'Unknown']
        ).order_by('last_updated')[:150]

        total = all_manga.count()
        total_in_db = Manga.objects.count()
        ongoing_count = Manga.objects.filter(status='ongoing').count()
        completed_count = Manga.objects.filter(status='completed').count()

        self.stdout.write(f"Total manga in DB: {total_in_db}")
        self.stdout.write(f"Ongoing: {ongoing_count} | Completed: {completed_count}")
        self.stdout.write(f"Updating {total} manga (oldest first, limited to 150)")

        if total == 0:
            self.stdout.write(self.style.WARNING("No ongoing manga to update!"))
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

                # Reduced delay since we're limiting to 100 manga per run
                time.sleep(0.5)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                failed_count += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Incremental update complete!"))
        self.stdout.write(f"✓ Updated: {updated_count}/{total}")
        self.stdout.write(f"✗ Failed: {failed_count}")
        self.stdout.write(f"📖 New chapters fetched: {total_new_chapters}")
        self.stdout.write(f"⏱️  Remaining ongoing manga: {max(0, ongoing_count - 150)}")
        self.stdout.write(f"ℹ️  Completed manga skipped: {completed_count}")
