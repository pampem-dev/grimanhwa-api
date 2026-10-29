from django.core.management.base import BaseCommand
from api.models import Chapter, Page
from api.sites.kaynscan import chapter_pages
import time

class Command(BaseCommand):
    help = 'Scrape page URLs for chapters and save to database'

    def handle(self, *args, **options):
        self.stdout.write("Starting page URL scraping...")
        self.stdout.write("=" * 50)

        # Get chapters that don't have pages yet
        chapters_to_scrape = Chapter.objects.all()
        total = chapters_to_scrape.count()
        total_chapters = Chapter.objects.count()

        self.stdout.write(f"Total chapters in DB: {total_chapters}")
        self.stdout.write(f"Chapters to scrape: {total}")
        self.stdout.write("Note: This will re-scrape all chapters to ensure pages are up to date")

        if total == 0:
            self.stdout.write(self.style.WARNING("No chapters found in database"))
            return

        scraped_count = 0
        failed_count = 0
        total_pages_saved = 0

        # Limit to avoid overwhelming the server
        limit = 50
        chapters_to_scrape = chapters_to_scrape[:limit]

        for i, chapter in enumerate(chapters_to_scrape, 1):
            self.stdout.write(f"\n[{i}/{limit}] Scraping: {chapter.manga.title} - Chapter {chapter.number}")

            try:
                # Use existing scraping function to get page URLs
                pages = chapter_pages(chapter.chapter_id)

                if pages and len(pages) > 0:
                    # Delete existing pages for this chapter
                    Page.objects.filter(chapter=chapter).delete()

                    # Save new pages
                    page_number = 1
                    for page_url in pages:
                        Page.objects.create(
                            chapter=chapter,
                            page_number=page_number,
                            image_url=page_url
                        )
                        page_number += 1

                    total_pages_saved += len(pages)
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Saved {len(pages)} pages"))
                    scraped_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"  ✗ No pages found"))
                    failed_count += 1

                # Delay between chapters to avoid overwhelming the server
                time.sleep(1)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                failed_count += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Scraping complete!"))
        self.stdout.write(f"✓ Chapters scraped: {scraped_count}")
        self.stdout.write(f"✗ Failed: {failed_count}")
        self.stdout.write(f"📖 Total pages saved: {total_pages_saved}")
        self.stdout.write(f"ℹ️  Remaining chapters: {max(0, total_chapters - limit)}")
        self.stdout.write("\nNote: Run this command again to scrape the remaining chapters")
