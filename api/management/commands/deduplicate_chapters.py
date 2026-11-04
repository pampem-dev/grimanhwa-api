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

        # Build query
        queryset = Chapter.objects.values('manga', 'number').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        if manga_id:
            queryset = queryset.filter(manga__url=manga_id)

        duplicates = list(queryset)

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate chapters found'))
            return

        self.stdout.write(f'Found {len(duplicates)} manga with duplicate chapters')

        total_deleted = 0

        for dup in duplicates:
            manga_id = dup['manga']
            chapter_number = dup['number']
            count = dup['count']

            # Get all chapters for this manga+number combination
            chapters = Chapter.objects.filter(manga_id=manga_id, number=chapter_number).order_by('-created_at')

            self.stdout.write(f'\nManga ID: {manga_id}, Chapter {chapter_number} ({count} duplicates):')
            for ch in chapters:
                pages_info = f"has {len(ch.pages)} pages" if ch.pages else "no pages"
                self.stdout.write(f'  - ID: {ch.id}, URL: {ch.chapter_id}, Created: {ch.created_at}, {pages_info}')

            # Keep the most recent one (first in list)
            to_keep = chapters.first()
            # Delete all except the one we're keeping
            to_delete = chapters.exclude(id=to_keep.id)

            if dry_run:
                self.stdout.write(f'  [DRY RUN] Would delete {to_delete.count()} duplicates, keeping ID {to_keep.id}')
            else:
                # Delete duplicates
                deleted_count, _ = to_delete.delete()
                total_deleted += deleted_count
                self.stdout.write(self.style.SUCCESS(f'  ✓ Deleted {deleted_count} duplicates, kept ID {to_keep.id}'))

        if dry_run:
            self.stdout.write(f'\n[DRY RUN] Total that would be deleted: {sum(d["count"] - 1 for d in duplicates)}')
        else:
            self.stdout.write(self.style.SUCCESS(f'\nTotal deleted: {total_deleted} duplicate chapters'))
