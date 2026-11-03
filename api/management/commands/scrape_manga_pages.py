from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import Manga, Chapter, Page
from api.sites.kaynscan import chapter_pages
import time


class Command(BaseCommand):
    help = 'Scrape chapter pages for manga, prioritizing ongoing and hiatus status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=1,
            help='Number of manga to process (default: 1)'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='Ongoing,Hiatus,Completed',
            help='Comma-separated list of statuses to prioritize (default: Ongoing,Hiatus,Completed)'
        )
        parser.add_argument(
            '--manga-id',
            type=str,
            help='Specific manga URL to process (skips priority logic)'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        status_filter = options.get('status', 'Ongoing,Hiatus').split(',')
        manga_id = options.get('manga_id')

        if manga_id:
            # Process specific manga
            manga = Manga.objects.filter(url=manga_id).first()
            if not manga:
                self.stdout.write(self.style.ERROR(f'Manga not found: {manga_id}'))
                return
            manga_list = [manga]
        else:
            # Get manga by priority status
            manga_list = Manga.objects.filter(
                status__in=status_filter
            ).order_by('last_updated')[:limit]

            if not manga_list.exists():
                self.stdout.write(self.style.WARNING(f'No manga found with status: {status_filter}'))
                return

        self.stdout.write(self.style.SUCCESS(f'Processing {len(manga_list)} manga(s)...'))

        for manga in manga_list:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(self.style.SUCCESS(f'Processing: {manga.title}'))
            self.stdout.write(f'Status: {manga.status}')
            self.stdout.write(f'Chapter count: {manga.chapter_count}')
            self.stdout.write(f'{"="*60}')

            # Get all chapters for this manga
            chapters = Chapter.objects.filter(manga=manga).order_by('-number')
            total_chapters = chapters.count()
            self.stdout.write(f'Found {total_chapters} chapters')

            processed_count = 0
            skipped_count = 0
            error_count = 0

            for chapter in chapters:
                # Check if pages already exist
                existing_pages = Page.objects.filter(chapter=chapter).count()
                if existing_pages > 0:
                    self.stdout.write(f'  ✓ Chapter {chapter.number}: Already has {existing_pages} pages (skipped)')
                    skipped_count += 1
                    continue

                self.stdout.write(f'  → Scraping Chapter {chapter.number}...')
                try:
                    # Scrape pages
                    pages_data = chapter_pages(chapter.url)

                    if pages_data and len(pages_data) > 0:
                        # Save pages to database
                        for idx, page_url in enumerate(pages_data):
                            Page.objects.get_or_create(
                                chapter=chapter,
                                page_number=idx,
                                defaults={'image_url': page_url}
                            )

                        self.stdout.write(self.style.SUCCESS(f'    ✓ Saved {len(pages_data)} pages'))
                        processed_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'    ⚠ No pages found'))
                        error_count += 1

                    # Small delay to avoid overwhelming the server
                    time.sleep(0.5)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ✗ Error: {str(e)}'))
                    error_count += 1
                    continue

            # Update manga last_updated timestamp
            manga.last_updated = timezone.now()
            manga.save()

            self.stdout.write(f'\n{manga.title} complete:')
            self.stdout.write(f'  Processed: {processed_count} chapters')
            self.stdout.write(f'  Skipped: {skipped_count} chapters')
            self.stdout.write(f'  Errors: {error_count} chapters')

        self.stdout.write(self.style.SUCCESS('\n✓ All done!'))
