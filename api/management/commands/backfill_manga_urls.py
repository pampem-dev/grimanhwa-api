from django.core.management.base import BaseCommand
from api.models import Manga, Chapter
import re

class Command(BaseCommand):
    help = 'Backfill manga URLs from chapter URLs for manga with missing URLs'

    def handle(self, *args, **options):
        self.stdout.write("Starting manga URL backfill...")
        self.stdout.write("=" * 50)

        # Get manga with empty or missing URLs
        manga_to_update = Manga.objects.filter(url__isnull=True) | Manga.objects.filter(url='')
        total = manga_to_update.count()
        total_manga = Manga.objects.count()

        self.stdout.write(f"Total manga in DB: {total_manga}")
        self.stdout.write(f"Manga needing URL update: {total}")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All manga have URLs!"))
            return

        updated_count = 0
        failed_count = 0

        for manga in manga_to_update:
            try:
                # Get chapters for this manga
                chapters = Chapter.objects.filter(manga=manga)
                
                if chapters.exists():
                    # Extract manga URL from the first chapter's URL
                    first_chapter = chapters.first()
                    chapter_url = first_chapter.url or first_chapter.chapter_id
                    
                    if chapter_url:
                        # Extract manga URL from chapter URL
                        # Format: https://asurascans.com/comics/manga-name/chapter/123
                        # We want: https://asurascans.com/comics/manga-name
                        manga_url = self.extract_manga_url(chapter_url)
                        
                        if manga_url:
                            manga.url = manga_url
                            manga.save()
                            self.stdout.write(self.style.SUCCESS(f"  ✓ Updated {manga.title}: {manga_url}"))
                            updated_count += 1
                        else:
                            self.stdout.write(self.style.WARNING(f"  ✗ Could not extract URL from chapter: {chapter_url}"))
                            failed_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"  ✗ Chapter has no URL"))
                        failed_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"  ✗ No chapters found for {manga.title}"))
                    failed_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                failed_count += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Backfill complete!"))
        self.stdout.write(f"✓ Updated: {updated_count}")
        self.stdout.write(f"✗ Failed: {failed_count}")

    def extract_manga_url(self, chapter_url):
        """Extract manga URL from chapter URL"""
        if not chapter_url:
            return None

        # Remove chapter/123 from the URL
        # Examples:
        # https://asurascans.com/comics/manga-name/chapter/123 -> https://asurascans.com/comics/manga-name
        # https://asurascans.com/comics/manga-name/chapter-123 -> https://asurascans.com/comics/manga-name
        
        # Remove trailing slash
        chapter_url = chapter_url.rstrip('/')
        
        # Find /chapter/ and remove everything after it
        if '/chapter/' in chapter_url:
            manga_url = chapter_url.split('/chapter/')[0]
            return manga_url
        
        # Find /chapter- and remove everything after it
        if '/chapter-' in chapter_url:
            manga_url = chapter_url.split('/chapter-')[0]
            return manga_url
        
        # Fallback: try to extract using regex
        match = re.match(r'(https?://[^/]+/comics/[^/]+)', chapter_url)
        if match:
            return match.group(1)
        
        return None
