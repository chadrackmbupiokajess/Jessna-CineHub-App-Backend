"""
TV EN DIRECT (FootLive) - lecture des listes de chaînes M3U.

On garde uniquement les chaînes jouables par le lecteur de l'application
(flux HLS .m3u8) et diffusées depuis le site / le CDN officiel de la chaîne.
Sont écartés:
- les flux hébergés sur une simple adresse IP (ex: http://151.80.18.177:86/...):
  ce sont des rediffusions non officielles;
- les chaînes payantes connues (Eleven Sports, Eurosport, beIN, Canal+, DAZN...);
- les liens YouTube / Dailymotion / Twitch / pages web (pas des flux vidéo);
- les entrées marquées "[NO PUBLIC STREAM]".
"""
import ipaddress
import re
from urllib.parse import urlparse

# Chaînes payantes: jamais importées, même si un lien circule.
PREMIUM_BRANDS = re.compile(
    r"eleven\s*sports|euro\s*sport|bein|canal\s*\+|canal\s*plus|dazn|sky\s*sport|"
    r"j\s*sports|rmc\s*sport|sport\s*tv\s*[1-5]|setanta|supersport|premier\s*sports|"
    r"tnt\s*sports|bt\s*sport|movistar|starz|hbo|showtime|cinemax|ocs\b",
    re.IGNORECASE,
)

# Hébergeurs qui rediffusent des chaînes sans être la chaîne elle-même.
RESTREAM_HOSTS = (
    "cammonitorplus.net", "mcquack.net", "premiumfree.tv", "tvkaista.net", "hls.tv",
    "erbvr.com", "iptv", "restream", "xtream",
)

# Chaînes en français des pays où plusieurs langues sont diffusées.
FRENCH_NAMES = re.compile(
    r"rtl-be|arte|tv5\s*monde|tv5monde|ln24|bx1|^ici\b|\bici\s|tva\b|télé|savoir|\(fr\)|rdi\b|"
    r"tvm\s*3|monaco|français|francais|french|france",
    re.IGNORECASE,
)

SPORT_WORDS = re.compile(r"sport|foot|soccer|calcio|tennis|futbol|fútbol|esport3|deport", re.IGNORECASE)

# Groupes de la liste -> catégorie affichée dans l'application.
FRENCH_GROUPS = {"France", "Monaco"}
MULTILINGUAL_GROUPS = {"Belgium", "Switzerland", "Canada"}
AFRICA_GROUPS = {
    "Nigeria", "Kenya", "Chad", "Somalia", "Egypt", "Morocco", "Algeria", "Tunisia",
    "Senegal", "Ivory Coast", "Côte d'Ivoire", "Cameroon", "Congo", "DR Congo", "Ghana",
    "South Africa", "Ethiopia", "Uganda", "Tanzania", "Rwanda", "Mali", "Benin", "Togo",
    "Gabon", "Guinea", "Burkina Faso", "Niger", "Madagascar", "Mauritius", "Sudan", "Libya",
}
NEWS_GROUPS = {"News", "News (AR)", "News (ES)", "Business", "Weather"}

COUNTRY_FR = {
    "Albania": "Albanie", "Argentina": "Argentine", "Armenia": "Arménie", "Australia": "Australie",
    "Austria": "Autriche", "Azerbaijan": "Azerbaïdjan", "Belarus": "Biélorussie", "Belgium": "Belgique",
    "Bosnia and Herzegovina": "Bosnie-Herzégovine", "Brazil": "Brésil", "Bulgaria": "Bulgarie",
    "Canada": "Canada", "Chad": "Tchad", "Chile": "Chili", "China": "Chine", "Costa Rica": "Costa Rica",
    "Croatia": "Croatie", "Cyprus": "Chypre", "Czech Republic": "Tchéquie", "Denmark": "Danemark",
    "Dominican Republic": "République dominicaine", "Egypt": "Égypte", "Estonia": "Estonie",
    "Faroe Islands": "Îles Féroé", "Finland": "Finlande", "France": "France", "Georgia": "Géorgie",
    "Germany": "Allemagne", "Greece": "Grèce", "Greenland": "Groenland", "Hong Kong": "Hong Kong",
    "Hungary": "Hongrie", "Iceland": "Islande", "India": "Inde", "Indonesia": "Indonésie", "Iran": "Iran",
    "Iraq": "Irak", "Ireland": "Irlande", "Israel": "Israël", "Italy": "Italie", "Kazakhstan": "Kazakhstan",
    "Kenya": "Kenya", "Korea": "Corée", "Kosovo": "Kosovo", "Latvia": "Lettonie", "Lebanon": "Liban",
    "Lithuania": "Lituanie", "Luxembourg": "Luxembourg", "Macau": "Macao", "Malta": "Malte",
    "Mexico": "Mexique", "Moldova": "Moldavie", "Monaco": "Monaco", "Mongolia": "Mongolie",
    "Montenegro": "Monténégro", "Netherlands": "Pays-Bas", "Nigeria": "Nigeria", "North Korea": "Corée du Nord",
    "North Macedonia": "Macédoine du Nord", "Norway": "Norvège", "Paraguay": "Paraguay", "Peru": "Pérou",
    "Poland": "Pologne", "Portugal": "Portugal", "Qatar": "Qatar", "Romania": "Roumanie", "Russia": "Russie",
    "San Marino": "Saint-Marin", "Saudi Arabia": "Arabie saoudite", "Serbia": "Serbie", "Slovakia": "Slovaquie",
    "Slovenia": "Slovénie", "Somalia": "Somalie", "Spain": "Espagne", "Sweden": "Suède",
    "Switzerland": "Suisse", "Taiwan": "Taïwan", "Trinidad": "Trinité-et-Tobago", "Turkey": "Turquie",
    "Turkmenistan": "Turkménistan", "UK": "Royaume-Uni", "USA": "États-Unis", "Ukraine": "Ukraine",
    "United Arab Emirates": "Émirats arabes unis", "Venezuela": "Venezuela", "Andorra": "Andorre",
    "日本 / Japan": "Japon",
}

# Ordre d'affichage des catégories principales.
MAIN_CATEGORIES = [
    ("Sport", 1),
    ("Chaînes françaises", 2),
    ("Afrique", 3),
    ("Info", 4),
    ("Films et documentaires", 5),
]

_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
_MARKS_RE = re.compile(r"\s*[ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ]+\s*$")


def parse_m3u(text):
    """Liste des chaînes d'un fichier M3U (nom, logo, groupe, lien, en-têtes)."""
    entries = []
    current = None
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            attrs = dict(_ATTR_RE.findall(line))
            name = line.rsplit(",", 1)[-1].strip() if "," in line else attrs.get("tvg-name", "")
            current = {
                "name": _MARKS_RE.sub("", name).strip() or attrs.get("tvg-name", "").strip(),
                "marks": name[len(_MARKS_RE.sub("", name)):].strip(),
                "logo": attrs.get("tvg-logo", "").strip(),
                "group": attrs.get("group-title", "").strip(),
                "country": attrs.get("tvg-country", "").strip(),
                "referer": "",
                "user_agent": "",
            }
            continue
        if line.startswith("#EXTVLCOPT:") and current is not None:
            option = line[len("#EXTVLCOPT:"):]
            key, _, value = option.partition("=")
            if key.strip().lower() in ("http-referrer", "http-referer"):
                current["referer"] = value.strip()
            elif key.strip().lower() == "http-user-agent":
                current["user_agent"] = value.strip()
            continue
        if line.startswith("#"):
            continue
        if current is not None:
            current["url"] = line
            entries.append(current)
            current = None
    return entries


def _host_is_ip(host):
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def rejection_reason(entry):
    """Pourquoi une chaîne n'est pas importée ("" = acceptée)."""
    url = (entry.get("url") or "").strip()
    name = entry.get("name") or ""
    if not url or "NO PUBLIC STREAM" in url.upper():
        return "pas de flux public"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return "lien invalide"
    if _host_is_ip(parsed.hostname):
        return "flux sur une adresse IP (rediffusion non officielle)"
    host = parsed.hostname.lower()
    if any(word in host for word in RESTREAM_HOSTS):
        return "hébergeur de rediffusion (non officiel)"
    if any(site in host for site in ("youtube.", "youtu.be", "dailymotion.", "twitch.", "facebook.")):
        return "page vidéo (pas un flux direct)"
    if ".m3u8" not in url.lower():
        return "pas un flux HLS (.m3u8)"
    if PREMIUM_BRANDS.search(name):
        return "chaîne payante"
    return ""


def category_for(entry):
    group = entry.get("group") or ""
    name = entry.get("name") or ""
    if SPORT_WORDS.search(name) and "radio" not in name.lower():
        return "Sport"
    if group in FRENCH_GROUPS or (group in MULTILINGUAL_GROUPS and FRENCH_NAMES.search(name)) \
            or re.search(r"tv5\s*monde|français|french", name, re.IGNORECASE):
        return "Chaînes françaises"
    if group in AFRICA_GROUPS or "Africa" in name:
        return "Afrique"
    if group in NEWS_GROUPS:
        return "Info"
    if group.startswith("VOD") or group.startswith("Documentaries") or group.startswith("Music"):
        return "Films et documentaires"
    return COUNTRY_FR.get(group, group or "Autres")


def select_channels(text):
    """(chaînes acceptées, nombre refusé par raison)."""
    accepted, rejected = [], {}
    seen = set()
    for entry in parse_m3u(text):
        reason = rejection_reason(entry)
        if not reason and entry["url"] in seen:
            reason = "doublon"
        if reason:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue
        seen.add(entry["url"])
        entry["category"] = category_for(entry)
        accepted.append(entry)
    return accepted, rejected


def import_channels(text, source="Free-TV", activate_categories=None):
    """
    Ajoute dans la base les chaînes acceptées d'une liste M3U.
    - Une chaîne déjà présente (même lien) est mise à jour, jamais dupliquée.
    - Rien n'est supprimé: les chaînes ajoutées à la main restent.
    - activate_categories: si donné, seules ces catégories sont activées à la
      création (les autres sont créées désactivées, à activer dans l'admin).
    Retourne un résumé: {ajoutées, mises à jour, refusées: {raison: nombre}}.
    """
    from django.db import transaction
    from .models import LiveTvCategory, LiveTvChannel

    accepted, rejected = select_channels(text)
    main_orders = dict(MAIN_CATEGORIES)
    categories = {category.name: category for category in LiveTvCategory.objects.all()}
    existing = {channel.stream_url: channel for channel in LiveTvChannel.objects.all()}
    created_count = updated_count = 0

    with transaction.atomic():
        for position, entry in enumerate(accepted):
            name = entry["category"][:100]
            category = categories.get(name)
            if category is None:
                active = activate_categories is None or name in activate_categories
                category = LiveTvCategory.objects.create(
                    name=name,
                    order=main_orders.get(name, 100),
                    is_active=active,
                )
                categories[name] = category
            url = entry["url"][:1000]
            channel = existing.get(url)
            if channel is None:
                channel = LiveTvChannel.objects.create(
                    category=category,
                    name=entry["name"][:150] or "Chaîne",
                    logo_url=entry["logo"][:500],
                    stream_url=url,
                    referer=entry["referer"][:500],
                    user_agent=entry["user_agent"][:300],
                    country=(entry["country"] or entry["group"])[:60],
                    source=source[:60],
                    order=position,
                )
                existing[url] = channel
                created_count += 1
            else:
                # Mise à jour du nom / logo uniquement (la catégorie et
                # l'activation choisies dans l'admin sont gardées).
                changed = False
                if entry["name"] and channel.name != entry["name"][:150]:
                    channel.name = entry["name"][:150]
                    changed = True
                if entry["logo"] and channel.logo_url != entry["logo"][:500]:
                    channel.logo_url = entry["logo"][:500]
                    changed = True
                if changed:
                    channel.save(update_fields=["name", "logo_url", "updated_at"])
                    updated_count += 1

    return {"created": created_count, "updated": updated_count, "accepted": len(accepted), "rejected": rejected}
