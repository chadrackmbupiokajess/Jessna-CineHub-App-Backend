"""
Importe une liste de chaînes M3U (ex: Free-TV) dans "TV en direct".

    python manage.py import_live_tv jessna-live-tv.m3u
    python manage.py import_live_tv https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8
    python manage.py import_live_tv liste.m3u --source "Mon partenaire"
    python manage.py import_live_tv liste.m3u --all-categories

Seules les chaînes gratuites et officielles jouables sont gardées (voir
appli/live_tv_m3u.py). Rien n'est supprimé.
"""
import urllib.request

from django.core.management.base import BaseCommand, CommandError

from appli.live_tv_m3u import MAIN_CATEGORIES, import_channels


class Command(BaseCommand):
    help = "Importe une liste M3U de chaînes (fichier ou lien) dans TV en direct (FootLive)."

    def add_arguments(self, parser):
        parser.add_argument("path_or_url")
        parser.add_argument("--source", default="Free-TV")
        parser.add_argument(
            "--all-categories",
            action="store_true",
            help="Activer aussi les catégories par pays (sinon seules Sport, Chaînes françaises, Afrique, Info, Films sont actives).",
        )

    def handle(self, *args, **options):
        target = options["path_or_url"]
        try:
            if target.startswith(("http://", "https://")):
                request = urllib.request.Request(target, headers={"User-Agent": "JessnaCineHub/1.0"})
                with urllib.request.urlopen(request, timeout=60) as response:
                    text = response.read().decode("utf-8", errors="replace")
            else:
                with open(target, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
        except Exception as error:
            raise CommandError(f"Impossible de lire la liste: {error}")

        activate = None if options["all_categories"] else {name for name, _ in MAIN_CATEGORIES}
        summary = import_channels(text, source=options["source"], activate_categories=activate)
        self.stdout.write(self.style.SUCCESS(
            f"{summary['created']} chaînes ajoutées, {summary['updated']} mises à jour "
            f"({summary['accepted']} acceptées dans la liste)."
        ))
        for reason, count in sorted(summary["rejected"].items(), key=lambda item: -item[1]):
            self.stdout.write(f"  écartées - {reason}: {count}")
