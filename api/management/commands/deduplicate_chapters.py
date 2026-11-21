from django.core.management.base import BaseCommand
from django.db.models import Count
from api.models import Chapter


class Command(BaseCommand):
    help = 'Remove duplicate chapter records (same manga, same chapter number)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--manga-id',
            type=str,
            help='Deduplicate chapters for a specific manga URL only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        manga_id = options.get('manga_id')
        dry_run = options.get('dry_run')

        # Build query - find ALL manga+chapter_number combos with duplicates
        queryset = Chapter.objects.values('manga', 'number').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        if manga_id:
            queryset = queryset.filter(manga__url=manga_id)

        duplicates = list(queryset)

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate chapters found'))
            return

        self.stdout.write(f'Found {len(duplicates)} manga+chapter combos with duplicate empty chapters')

        total_deleted = 0

        for dup in duplicates:
            manga_id = dup['manga']
            chapter_number = dup['number']
            count = dup['count']

            # Get all chapters for this manga+number combination
            all_chapters = Chapter.objects.filter(manga_id=manga_id, number=chapter_number).order_by('-created_at')

            # Separate chapters with pages vs without pages
            chapters_with_pages = all_chapters.exclude(pages=[])
            chapters_without_pages = all_chapters.filter(pages=[])

            if not chapters_without_pages.exists():
                continue

            self.stdout.write(f'\nManga ID: {manga_id}, Chapter {chapter_number}:')
            self.stdout.write(f'  Chapters with pages: {chapters_with_pages.count()}')
            self.stdout.write(f'  Chapters without pages: {chapters_without_pages.count()}')

            # If there's a chapter with pages, delete all without pages
            if chapters_with_pages.exists():
                to_keep = chapters_with_pages.first()
                to_delete = chapters_without_pages
                self.stdout.write(f'  Keeping chapter with pages (ID: {to_keep.id})')
            else:
                # All have no pages - keep the most recent one
                to_keep = all_chapters.first()
                to_delete = all_chapters.exclude(id=to_keep.id)
                self.stdout.write(f'  All have no pages - keeping most recent (ID: {to_keep.id})')

            self.stdout.write(f'  Deleting {to_delete.count()} duplicate chapters')

            if dry_run:
                self.stdout.write(f'  [DRY RUN] Would delete {to_delete.count()} duplicates')
            else:
                # Delete duplicates
                deleted_count, _ = to_delete.delete()
                total_deleted += deleted_count
                self.stdout.write(self.style.SUCCESS(f'  ✓ Deleted {deleted_count} duplicates'))

        if dry_run:
            self.stdout.write(f'\n[DRY RUN] Total that would be deleted: {sum(d["count"] - 1 for d in duplicates)}')
        else:
            self.stdout.write(self.style.SUCCESS(f'\nTotal deleted: {total_deleted} duplicate chapters'))
