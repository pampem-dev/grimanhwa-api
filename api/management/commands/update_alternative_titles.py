from django.core.management.base import BaseCommand
from api.models import Manga
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import re

class Command(BaseCommand):
    help = 'Update alternative titles for all manga in the database'

    def handle(self, *args, **options):
        self.stdout.write("Starting alternative titles update...")
        self.stdout.write("=" * 50)

        # Get manga that have empty or missing alternative titles
        # Or haven't been updated in the last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        manga_to_update = Manga.objects.filter(
            last_updated__lt=seven_days_ago
        ) | Manga.objects.filter(
            alternative_titles__isnull=True
        ) | Manga.objects.filter(
            alternative_titles=[]
        )

        # Remove duplicates and sort
        manga_to_update = manga_to_update.distinct().order_by('last_updated')
        total = manga_to_update.count()
        total_in_db = Manga.objects.count()
        has_alt_titles_count = Manga.objects.exclude(alternative_titles__isnull=True).exclude(alternative_titles=[]).count()

        self.stdout.write(f"Total manga in DB: {total_in_db}")
        self.stdout.write(f"Has alternative titles: {has_alt_titles_count} | Needs update: {total}")
        self.stdout.write(f"Updating {total} manga (limited to 200 per run)")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All manga have alternative titles!"))
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

                # Extract alternative titles - try multiple strategies
                alternative_titles = []

                # Strategy 1: Look for alternative titles in specific selectors
                alt_title_selectors = [
                    'div.flex.items-start.gap-3.mt-3.text-xs',
                    'div.manga-alt-titles',
                    'div.alternative-titles',
                    'div.other-titles',
                    'div.alternative-titles-wrapper',
                    'div.alt-titles',
                    'div.manga-alternatives',
                    'div.series-alternatives',
                    'div.aka',
                    'div.aka-titles'
                ]

                for selector in alt_title_selectors:
                    alt_elem = soup.select_one(selector)
                    if alt_elem:
                        alt_text = alt_elem.get_text(strip=True)
                        # Split by bullet points or common separators
                        titles = re.split(r'[•,;|/]', alt_text)
                        titles = [t.strip() for t in titles if t.strip() and len(t.strip()) > 2]
                        if titles and len(titles) > 1:  # More than one title found
                            alternative_titles = titles
                            break

                # Strategy 2: Look for "AKA" or "Also Known As" patterns in the page
                if not alternative_titles:
                    for elem in soup.find_all(string=re.compile(r'(aka|also known as|alternative|other names)', re.I)):
                        parent = elem.parent
                        if parent:
                            parent_text = parent.get_text(strip=True)
                            # Try to extract titles from the parent text
                            titles = re.split(r'[•,;|/]', parent_text)
                            titles = [t.strip() for t in titles if t.strip() and len(t.strip()) > 2]
                            # Filter out the "AKA" or "Also Known As" text itself
                            titles = [t for t in titles if not re.search(r'(aka|also known as|alternative|other names)', t, re.I)]
                            if titles and len(titles) > 0:
                                alternative_titles = titles
                                break

                # Strategy 3: Look for meta tags with alternative titles
                if not alternative_titles:
                    meta_alt = soup.find('meta', attrs={'name': 'alternative-title'})
                    if meta_alt and meta_alt.get('content'):
                        titles = re.split(r'[•,;|/]', meta_alt.get('content'))
                        alternative_titles = [t.strip() for t in titles if t.strip() and len(t.strip()) > 2]

                # Strategy 4: Look for any div/span with class containing "alt" or "alternative"
                if not alternative_titles:
                    for elem in soup.find_all(class_=re.compile(r'alt|alternative', re.I)):
                        text = elem.get_text(strip=True)
                        if len(text) > 10 and len(text) < 200:  # Reasonable length
                            titles = re.split(r'[•,;|/]', text)
                            titles = [t.strip() for t in titles if t.strip() and len(t.strip()) > 2]
                            if titles and len(titles) > 1:
                                alternative_titles = titles
                                break

                if alternative_titles and len(alternative_titles) > 0:
                    # Remove duplicates and filter out the main title
                    main_title_lower = manga.title.lower().strip()
                    alternative_titles = list(set(alternative_titles))
                    alternative_titles = [t for t in alternative_titles if t.lower().strip() != main_title_lower]

                    if alternative_titles:
                        manga.alternative_titles = alternative_titles
                        manga.save()
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Found {len(alternative_titles)} alternative titles"))
                        updated_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"  ✗ No unique alternative titles found"))
                        failed_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"  ✗ No alternative titles found on page"))
                    failed_count += 1

                # Reduced delay since we're doing 200 per run
                time.sleep(0.5)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                failed_count += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Alternative titles update complete!"))
        self.stdout.write(f"✓ Updated: {updated_count}")
        self.stdout.write(f"✗ Failed: {failed_count}")
        self.stdout.write(f"⏱️  Remaining manga to update: {max(0, total - 200)}")
