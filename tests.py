from django.core.management import call_command
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase


class MigrationIntegrityTests(TestCase):
    """Regressões para o histórico de migrações do app."""

    def test_agenda_app_has_single_migration_leaf(self):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        leaves = loader.graph.leaf_nodes("agenda_app")
        self.assertEqual(
            leaves,
            [("agenda_app", "0001_add_portalsecure")],
            "agenda_app não deve voltar a ter duas folhas de migração",
        )

    def test_migrations_are_consistent(self):
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)
