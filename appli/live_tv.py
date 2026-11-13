"""
TV EN DIRECT (FootLive) - API utilisée par l'application (PC, mobile, TV).

Les chaînes viennent de l'admin Django (TV en direct - chaînes), plus de
Yacine: personne ne peut les couper à la place de Jessna CinéHub.

GET /api/live-tv/categories/                  -> catégories actives
GET /api/live-tv/categories/<id>/channels/    -> chaînes d'une catégorie
GET /api/live-tv/channels/<id>/               -> lien de lecture d'une chaîne
POST /api/live-tv/channels/<id>/report/       -> {"status": "ok" | "fail"}

Une chaîne signalée en échec 5 fois sans jamais remarcher est masquée
automatiquement; elle revient dès qu'une lecture réussit.
"""
import json

from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import LiveTvCategory, LiveTvChannel

CACHE_SECONDS = 300


def _json(payload, status=200):
    response = JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})
    response["Cache-Control"] = f"public, max-age={CACHE_SECONDS}"
    return response


@require_GET
def live_tv_categories_view(request):
    categories = (
        LiveTvCategory.objects.filter(
            is_active=True,
            channels__is_active=True,
            channels__failure_count__lt=LiveTvChannel.AUTO_HIDE_FAILURES,
        )
        .distinct()
        .order_by("order", "name")
    )
    data = []
    for category in categories:
        count = category.channels.filter(is_active=True, failure_count__lt=LiveTvChannel.AUTO_HIDE_FAILURES).count()
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
    channels = category.channels.filter(
        is_active=True,
        failure_count__lt=LiveTvChannel.AUTO_HIDE_FAILURES,
    ).order_by("order", "name")
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


@csrf_exempt
@require_POST
def live_tv_channel_report_view(request, channel_id):
    """L'application signale si la chaîne a pu être lue ("ok") ou non ("fail")."""
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        body = {}
    status = str(body.get("status") or "").lower()
    if status not in ("ok", "fail"):
        return JsonResponse({"success": False, "error": "status doit valoir ok ou fail"}, status=400)
    now = timezone.now()
    channels = LiveTvChannel.objects.filter(id=channel_id)
    if status == "ok":
        updated = channels.update(failure_count=0, last_success_at=now)
    else:
        updated = channels.update(failure_count=F("failure_count") + 1, last_failure_at=now)
    if not updated:
        return JsonResponse({"success": False, "error": "Chaîne introuvable"}, status=404)
    return JsonResponse({"success": True})
