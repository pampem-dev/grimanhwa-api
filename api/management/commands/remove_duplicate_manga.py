from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower
from api.models import Manga, Chapter


class Command(BaseCommand):
    help = 'Remove duplicate mangas that have 0 chapters (keeps at least one copy)'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup...')
        self.stdout.write('Removing manga that are BOTH duplicates AND have 0 chapters...')
        
        # Find duplicates by title (case-insensitive)
        title_duplicates = Manga.objects.annotate(title_lower=Lower('title')).values('title_lower').annotate(count=Count('id')).filter(count__gt=1)
        
        deleted_count = 0
        for duplicate in title_duplicates:
            title_lower = duplicate['title_lower']
            # Get all manga with this title, ordered by id
            mangas = Manga.objects.filter(title__iexact=title_lower).order_by('id')
            
            # Filter to only those with 0 chapters
            zero_chapter_mangas = mangas.filter(chapter_count=0)
            
            # If all have 0 chapters, keep the first one
            if zero_chapter_mangas.count() == mangas.count():
                to_delete = zero_chapter_mangas[1:]  # Keep first, delete rest
            else:
                # Only delete the zero-chapter ones (keep the ones with chapters)
                to_delete = zero_chapter_mangas
            
            count = to_delete.count()
            if count > 0:
                to_delete.delete()
                deleted_count += count
                self.stdout.write(f'  Removed {count} duplicate(s) with 0 chapters for: {mangas.first().title[:50]}...')
        
        self.stdout.write(self.style.SUCCESS(f'\nRemoved {deleted_count} manga that were duplicates AND had 0 chapters'))
