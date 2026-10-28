from django.core.management.base import BaseCommand
from api.models import Manga
import requests
from bs4 import BeautifulSoup
import time

class Command(BaseCommand):
    help = 'Update ratings for all manga in the database'

    def handle(self, *args, **options):
        self.stdout.write("Starting rating update...")
        self.stdout.write("=" * 50)

        # Get all manga with no rating
        manga_to_update = Manga.objects.filter(rating__isnull=True)
        total = manga_to_update.count()
        total_in_db = Manga.objects.count()
        with_rating = Manga.objects.filter(rating__isnull=False).count()

        self.stdout.write(f"Total manga in DB: {total_in_db}")
        self.stdout.write(f"With rating: {with_rating} | Without rating: {total}")
        self.stdout.write(f"Updating {total} manga (limited to 150 per run)")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All manga already have ratings!"))
            return

        # Limit to 150 per run for Railway free tier
        manga_to_update = manga_to_update[:150]

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

                # Extract rating
                rating = None
                rating_selectors = [
                    'div.rating',
                    'span.rating',
                    'div[itemprop="ratingValue"]',
                    'span[itemprop="ratingValue"]',
                    'div.summary-content .rating',
                    'div.post-content .rating',
                    'div.manga-info .rating',
                    'div.rate',
                    'span.rate',
                    'div.score',
                    'span.score'
                ]

                for selector in rating_selectors:
                    rating_elem = soup.select_one(selector)
                    if rating_elem:
                        rating_text = rating_elem.get_text(strip=True)
                        # Extract number from text like "4.5" or "Rating: 4.5"
                        import re
                        match = re.search(r'(\d+\.?\d*)', rating_text)
                        if match:
                            try:
                                rating = float(match.group(1))
                                if 0 <= rating <= 10:  # Validate rating range
                                    break
                            except:
                                pass

                if rating is not None:
                    manga.rating = rating
                    manga.save()
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Rating: {rating}"))
                    updated_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"  ✗ No rating found on page"))
                    failed_count += 1

                # Add delay to avoid overwhelming the server
                time.sleep(0.5)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                failed_count += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Rating update complete!"))
        self.stdout.write(f"✓ Updated: {updated_count}")
        self.stdout.write(f"✗ Failed: {failed_count}")
        self.stdout.write(f"⏱️  Remaining manga without rating: {max(0, total - 150)}")
