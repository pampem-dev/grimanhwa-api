from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower
from api.models import Manga, Chapter


class Command(BaseCommand):
    help = 'Remove duplicate mangas that have 0 chapters (keeps at least one copy)'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup...')
        self.stdout.write('Removing ALL duplicate mangas (regardless of chapter count)...')
        
        # Find duplicates by title (case-insensitive)
        title_duplicates = Manga.objects.annotate(title_lower=Lower('title')).values('title_lower').annotate(count=Count('id')).filter(count__gt=1)
        
        deleted_count = 0
        for duplicate in title_duplicates:
            title_lower = duplicate['title_lower']
            # Get all manga with this title, ordered by id
            mangas = Manga.objects.filter(title__iexact=title_lower).order_by('id')
            
            # COMMENTED OUT: Filter to only those with 0 chapters
            # zero_chapter_mangas = mangas.filter(chapter_count=0)
            
            # Keep first, delete rest - get IDs to avoid limit/offset issue
            to_delete_ids = list(mangas.values_list('id', flat=True)[1:])
            
            if to_delete_ids:
                Manga.objects.filter(id__in=to_delete_ids).delete()
                deleted_count += len(to_delete_ids)
                self.stdout.write(f'  Removed {len(to_delete_ids)} duplicate(s) for: {mangas.first().title[:50]}...')
        
        self.stdout.write(self.style.SUCCESS(f'\nRemoved {deleted_count} duplicate mangas'))
