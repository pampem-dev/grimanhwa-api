import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef

from api.models import Chapter, Page
from api.sites.kaynscan import chapter_pages


class Command(BaseCommand):
    help = "Scrape chapter pages and save them to the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of chapters to process",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        chapters = Chapter.objects.annotate(
            has_pages=Exists(
                Page.objects.filter(chapter_id=OuterRef("pk"))
            )
        ).filter(
            has_pages=False
        ).order_by("pk")

        if limit is not None:
            chapters = chapters[:limit]

        total = len(chapters)
        saved_count = 0
        empty_count = 0
        failed_count = 0

        self.stdout.write(f"Chapters to scrape: {total}")

        for index, chapter in enumerate(chapters, start=1):
            self.stdout.write(
                f"[{index}/{total}] {chapter.title} - {chapter.chapter_id}"
            )

            try:
                pages = chapter_pages(chapter.chapter_id)

                if not pages:
                    empty_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            "No pages returned; existing database records were left unchanged."
                        )
                    )
                    continue

                # Save only after scraping returns valid page URLs.
                with transaction.atomic():
                    for page_number, page_url in enumerate(pages, start=1):
                        Page.objects.create(
                            chapter=chapter,
                            # Keep your existing Page model field names here.
                            page_number=page_number,
                            image_url=page_url,
                        )

                saved_count += len(pages)
                self.stdout.write(
                    self.style.SUCCESS(f"Saved {len(pages)} pages.")
                )

            except Exception as exc:
                failed_count += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed to scrape {chapter.chapter_id}: {exc}"
                    )
                )

            # Give Chromium and the target website a short break.
            time.sleep(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. Saved: {saved_count} pages | "
                f"No pages: {empty_count} chapters | "
                f"Failed: {failed_count} chapters"
            )
        )