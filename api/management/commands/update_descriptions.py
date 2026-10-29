from django.core.management.base import BaseCommand
from api.models import Manga
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Update descriptions for all manga in the database'

    def handle(self, *args, **options):
        self.stdout.write("Starting description update...")
        self.stdout.write("=" * 50)

        # Get manga that have empty or missing descriptions
        # Or haven't been updated in the last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        manga_to_update = Manga.objects.filter(
            last_updated__lt=seven_days_ago
        ) | Manga.objects.filter(
            description__isnull=True
        ) | Manga.objects.filter(
            description=''
        )

        # Remove duplicates and sort
        manga_to_update = manga_to_update.distinct().order_by('last_updated')
        total = manga_to_update.count()
        total_in_db = Manga.objects.count()
        has_description_count = Manga.objects.exclude(description__isnull=True).exclude(description='').count()

        self.stdout.write(f"Total manga in DB: {total_in_db}")
        self.stdout.write(f"Has description: {has_description_count} | Needs update: {total}")
        self.stdout.write(f"Updating {total} manga (limited to 200 per run)")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All manga have descriptions!"))
            return

        # Limit to 200 per run for Railway free tier
        manga_to_update = manga_to_update[:200]

        updated_count = 0
        failed_count = 0

        # Update each manga
        for i, manga in enumerate(manga_to_update, 1):
            self.stdout.write(f"\n[{i}/{len(manga_to_update)}] Updating: {manga.title}")

            try:
                # Fetch the manga page
                response = requests.get(manga.url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                })

                if response.status_code != 200:
                    self.stdout.write(self.style.WARNING(f"  ✗ Failed to fetch page (status {response.status_code})"))
                    failed_count += 1
                    time.sleep(0.5)
                    continue

                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract description - try multiple strategies
                description = ""

                # Strategy 1: Common description selectors
                description_selectors = [
                    'div.prose.prose-invert',
                    'div.text-sm.lg\\:text-base.font-light.text-white\\/80',
                    'div.mt-3.relative',
                    'p:nth-of-type(2)',
                    'div.summary__content',
                    'div.entry-content',
                    'div.post-content',
                    'div.manga-summary',
                    'div.summary',
                    'p.summary',
                    'div.description',
                    'div.wpb_wrapper',
                    'div.summary-content',
                    'div.manga-desc',
                    'div.story-summary',
                    'div.main-summary',
                    'article.post-content',
                    'div.content-area',
                    'div.wp-block-group__content',
                    'div.manga-excerpt',
                    'div.series-summary'
                ]

                for selector in description_selectors:
                    desc_elem = soup.select_one(selector)
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                        if description and len(description) > 10:  # Ensure it's not just whitespace or too short
                            break

                # Strategy 2: Look for description in meta tags
                if not description or len(description) < 10:
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    if meta_desc and meta_desc.get('content'):
                        description = meta_desc.get('content')

                # Strategy 3: Look for any paragraph with substantial text
                if not description or len(description) < 10:
                    for p in soup.find_all('p'):
                        text = p.get_text(strip=True)
                        if len(text) > 50:  # Only consider substantial paragraphs
                            description = text
                            break

                if description and len(description) > 10:
                    # Truncate if too long (max 5000 chars as per model)
                    if len(description) > 5000:
                        description = description[:5000]

                    manga.description = description
                    manga.save()
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Description: {len(description)} chars"))
                    updated_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"  ✗ No description found on page"))
                    failed_count += 1

                # Reduced delay since we're doing 200 per run
                time.sleep(0.5)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                failed_count += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Description update complete!"))
        self.stdout.write(f"✓ Updated: {updated_count}")
        self.stdout.write(f"✗ Failed: {failed_count}")
        self.stdout.write(f"⏱️  Remaining manga to update: {max(0, total - 200)}")
