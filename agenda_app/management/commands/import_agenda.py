import json
from pathlib import Path
from django.core.management.base import BaseCommand
from agenda_app.models import AgendaItem

class Command(BaseCommand):
    help = 'Imports agenda items from agenda_details.json into SQLite database'

    def handle(self, *args, **options):
        json_path = Path('/home/vboxuser/agenda/agenda_details.json')
        if not json_path.exists():
            self.stdout.write(self.style.ERROR('agenda_details.json not found!'))
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        imported_count = 0
        updated_count = 0

        for ext_id, item_data in data.items():
            date = item_data.get('date', '')
            title = item_data.get('title', '')
            description = item_data.get('description', '')
            download_url = item_data.get('download_url', '')
            completed = item_data.get('completed', False)

            obj, created = AgendaItem.objects.update_or_create(
                external_id=ext_id,
                defaults={
                    'date': date,
                    'title': title,
                    'description': description,
                    'download_url': download_url if download_url else None,
                    'completed': completed,
                }
            )
            if created:
                imported_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {imported_count} new items and updated {updated_count} existing items.'))
