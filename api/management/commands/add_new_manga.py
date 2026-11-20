from django.core.management.base import BaseCommand
from api.sites.kaynscan import get_all_browse_manga


class Command(BaseCommand):
    help = 'Add new manga to database without updating existing ones'

    def handle(self, *args, **options):
        self.stdout.write('Scraping all manga from browse pages (create only mode)...')
        self.stdout.write('This will only add NEW manga, existing manga will not be updated.')
        
        # Call with save_to_db=True, create_only=True
        result = get_all_browse_manga(save_to_db=True, create_only=True)
        
        if result:
            self.stdout.write(self.style.SUCCESS(f'Done! Total manga found: {result.get("total_manga", 0)}'))
        else:
            self.stdout.write(self.style.ERROR('Failed to scrape manga'))
