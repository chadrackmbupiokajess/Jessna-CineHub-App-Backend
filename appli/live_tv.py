"""
TV EN DIRECT (FootLive) - API utilisée par l'application (PC, mobile, TV).

Les chaînes viennent de l'admin Django (TV en direct - chaînes), plus de
Yacine: personne ne peut les couper à la place de Jessna CinéHub.

GET /api/live-tv/categories/                  -> catégories actives
GET /api/live-tv/categories/<id>/channels/    -> chaînes d'une catégorie
GET /api/live-tv/channels/<id>/               -> lien de lecture d'une chaîne
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import LiveTvCategory, LiveTvChannel

CACHE_SECONDS = 300


def _json(payload, status=200):
    response = JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})
    response["Cache-Control"] = f"public, max-age={CACHE_SECONDS}"
    return response


@require_GET
def live_tv_categories_view(request):
    categories = (
        LiveTvCategory.objects.filter(is_active=True, channels__is_active=True)
        .distinct()
        .order_by("order", "name")
    )
    data = []
    for category in categories:
        count = category.channels.filter(is_active=True).count()
        data.append({
            "id": category.id,
            "name": category.name,
            "logo": category.logo_url,
            "count": count,
        })
    return _json({"success": True, "data": data})


@require_GET
def live_tv_category_channels_view(request, category_id):
    category = LiveTvCategory.objects.filter(id=category_id, is_active=True).first()
    if category is None:
        return _json({"success": False, "error": "Catégorie introuvable", "data": []}, status=404)
    channels = category.channels.filter(is_active=True).order_by("order", "name")
    data = [
        {
            "id": channel.id,
            "name": channel.name,
            "logo": channel.logo_url,
            "category_id": category.id,
            "country": channel.country,
        }
        for channel in channels
    ]
    return _json({"success": True, "data": data})


@require_GET
def live_tv_channel_view(request, channel_id):
    channel = LiveTvChannel.objects.filter(id=channel_id, is_active=True, category__is_active=True).first()
    if channel is None:
        return _json({"success": False, "error": "Chaîne introuvable"}, status=404)
    headers = {}
    if channel.referer:
        headers["Referer"] = channel.referer
    if channel.user_agent:
        headers["User-Agent"] = channel.user_agent
    return _json({
        "success": True,
        "data": {
            "id": channel.id,
            "name": channel.name,
            "logo": channel.logo_url,
            "category_id": channel.category_id,
            "url": channel.stream_url,
            "headers": headers,
        },
    })
