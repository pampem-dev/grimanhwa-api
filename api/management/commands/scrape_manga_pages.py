
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from api.models import Manga, Chapter
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
            help='Comma-separated list of statuses to prioritize'
        )
        parser.add_argument(
            '--manga-id',
            type=str,
            help='Specific manga URL to process (skips priority logic)'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        status_filter = options['status'].split(',')
        manga_id = options.get('manga_id')

        if manga_id:
            manga = Manga.objects.filter(url=manga_id).first()

            if not manga:
                self.stdout.write(
                    self.style.ERROR(f'Manga not found: {manga_id}')
                )
                return

            manga_list = [manga]

        else:
            status_query = Q()

            for status in status_filter:
                status = status.strip()

                if status:
                    status_query |= Q(status__iexact=status)

            manga_list = Manga.objects.filter(
                status_query
            ).order_by('last_updated')[:limit]

            if not manga_list:
                self.stdout.write(
                    self.style.WARNING(
                        f'No manga found with status: {status_filter}'
                    )
                )
                return

        self.stdout.write(
            self.style.SUCCESS(
                f'Processing {len(manga_list)} manga(s)...'
            )
        )

        for manga in manga_list:
            self.stdout.write(f'\n{"=" * 60}')
            self.stdout.write(
                self.style.SUCCESS(f'Processing: {manga.title}')
            )
            self.stdout.write(f'Status: {manga.status}')
            self.stdout.write(f'Chapter count: {manga.chapter_count}')
            self.stdout.write(f'{"=" * 60}')

            # Only retrieve chapters that have not been scraped yet.
            chapters = Chapter.objects.filter(
                manga=manga
            ).filter(
                Q(pages__isnull=True) | Q(pages=[])
            ).order_by('-number')

            total_chapters = chapters.count()

            self.stdout.write(
                f'Chapters needing page scraping: {total_chapters}'
            )

            processed_count = 0
            skipped_count = 0
            error_count = 0

            for chapter in chapters.iterator(chunk_size=10):
                self.stdout.write(
                    f'  → Scraping Chapter {chapter.number}...'
                )

                try:
                    pages_data = chapter_pages(chapter.url)

                    if pages_data:
                        chapter.pages = pages_data
                        chapter.pages_scraped_at = timezone.now()

                        chapter.save(
                            update_fields=[
                                'pages',
                                'pages_scraped_at'
                            ]
                        )

                        self.stdout.write(
                            self.style.SUCCESS(
                                f'    ✓ Saved {len(pages_data)} pages'
                            )
                        )

                        processed_count += 1

                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                '    ⚠ No pages found'
                            )
                        )
                        error_count += 1

                    time.sleep(0.5)

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'    ✗ Error: {str(e)}'
                        )
                    )
                    error_count += 1
                    continue

            manga.last_updated = timezone.now()
            manga.save(update_fields=['last_updated'])

            self.stdout.write(f'\n{manga.title} complete:')
            self.stdout.write(f'  Processed: {processed_count} chapters')
            self.stdout.write(f'  Skipped: {skipped_count} chapters')
            self.stdout.write(f'  Errors: {error_count} chapters')

        self.stdout.write(
            self.style.SUCCESS('\n✓ All done!')
        )
