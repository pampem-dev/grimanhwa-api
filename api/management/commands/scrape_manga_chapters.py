from django.core.management.base import BaseCommand
from api.models import Manga, Chapter
from api.sites.kaynscan import manga_info as kaynscan_manga_info
from api.sites.kaynscan import save_chapters_to_db


class Command(BaseCommand):
    help = 'Scrape chapters for a specific manga from the website'

    def add_arguments(self, parser):
        parser.add_argument(
            '--manga-id',
            type=str,
            required=True,
            help='Manga URL to scrape chapters for'
        )
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            help='Force refresh from website (ignore cache)'
        )

    def handle(self, *args, **options):
        manga_id = options.get('manga_id')
        force_refresh = options.get('force_refresh')

        self.stdout.write(f'Scraping chapters for: {manga_id}')

        try:
            # Get manga from database
            manga = Manga.objects.get(url=manga_id)
            self.stdout.write(f'Found manga: {manga.title}')
        except Manga.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Manga not found: {manga_id}'))
            return

        # Scrape chapters from website
        self.stdout.write('Fetching chapters from website...')
        try:
            chapters_data = kaynscan_manga_info(manga_id, force_refresh=force_refresh)

            if not chapters_data:
                self.stdout.write(self.style.WARNING('No chapters found on website'))
                return

            self.stdout.write(f'Found {len(chapters_data)} chapters on website')

            # Save chapters to database
            self.stdout.write('Saving chapters to database...')
            save_chapters_to_db(manga, chapters_data)

            # Count chapters in database
            chapter_count = Chapter.objects.filter(manga=manga).count()
            self.stdout.write(self.style.SUCCESS(f'✓ Saved {chapter_count} chapters to database'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error scraping chapters: {str(e)}'))
            raise
