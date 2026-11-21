from django.core.management.base import BaseCommand
from django.db.models import Count
from api.models import Chapter
from api.sites.kaynscan import chapter_url_key


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

        # Find ALL manga+chapter_number combos with duplicates
        queryset = Chapter.objects.values('manga', 'number').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        if manga_id:
            queryset = queryset.filter(manga__url=manga_id)

        duplicates = list(queryset)

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate chapters found'))
            return

        self.stdout.write(f'Found {len(duplicates)} manga+chapter combos with duplicates')

        total_deleted = 0
        groups_processed = 0

        for dup in duplicates:
            manga_id_val = dup['manga']
            chapter_number = dup['number']

            all_chapters = list(
                Chapter.objects.filter(manga_id=manga_id_val, number=chapter_number)
                .order_by('-created_at')
            )

            with_pages = [c for c in all_chapters if c.pages]
            without_pages = [c for c in all_chapters if not c.pages]

            to_delete_ids = []
            keep_reason = ''

            if with_pages:
                # Group chapters-with-pages by stable URL key.
                # Same key = same chapter under different manga slugs -> keep best copy.
                # Different keys = possibly different chapters sharing a number -> keep all.
                by_key = {}
                for c in with_pages:
                    k = chapter_url_key(c.url or c.chapter_id)
                    by_key.setdefault(k, []).append(c)

                kept_ids = set()
                for key, group in by_key.items():
                    # Keep the copy with most pages, tie-break newest
                    keeper = max(group, key=lambda c: (len(c.pages), c.created_at))
                    kept_ids.add(keeper.id)
                    to_delete_ids.extend(c.id for c in group if c.id != keeper.id)

                # Delete all empty-page chapters in this group
                to_delete_ids.extend(c.id for c in without_pages)

                keep_reason = f'keeping {len(kept_ids)} copy(ies) with pages'
            else:
                # All empty - keep newest per URL key (different keys may be different chapters)
                by_key = {}
                for c in without_pages:
                    k = chapter_url_key(c.url or c.chapter_id)
                    by_key.setdefault(k, []).append(c)

                kept_ids = set()
                for key, group in by_key.items():
                    keeper = max(group, key=lambda c: c.created_at)
                    kept_ids.add(keeper.id)
                    to_delete_ids.extend(c.id for c in group if c.id != keeper.id)

                keep_reason = f'all empty - keeping {len(kept_ids)} newest'

            if not to_delete_ids:
                continue

            groups_processed += 1
            self.stdout.write(f'\nManga ID: {manga_id_val}, Chapter {chapter_number}:')
            self.stdout.write(f'  Total copies: {len(all_chapters)} ({len(with_pages)} with pages, {len(without_pages)} empty)')
            self.stdout.write(f'  {keep_reason}, deleting {len(to_delete_ids)}')

            if dry_run:
                self.stdout.write(f'  [DRY RUN] Would delete {len(to_delete_ids)} duplicates')
            else:
                deleted_count, _ = Chapter.objects.filter(id__in=to_delete_ids).delete()
                total_deleted += deleted_count
                self.stdout.write(self.style.SUCCESS(f'  Deleted {deleted_count} duplicates'))

        if dry_run:
            self.stdout.write(f'\n[DRY RUN] Groups affected: {groups_processed}')
        else:
            self.stdout.write(self.style.SUCCESS(f'\nTotal deleted: {total_deleted} duplicate chapters across {groups_processed} groups'))
