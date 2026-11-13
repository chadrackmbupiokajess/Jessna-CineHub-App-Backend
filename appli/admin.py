import os

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.utils import timezone
from datetime import timedelta
from .models import AppUpdate, SubscriptionPlan, PaymentMethod, Subscription, Payment, Notification, UserProfile, AppContent, PcAppRelease, Announcement
from .models import LiveTvCategory, LiveTvChannel


class AppUpdateAdminForm(forms.ModelForm):
    server_apk_file = forms.ChoiceField(
        label='APK deja present sur le serveur',
        required=False,
        choices=[],
        help_text="Pour eviter l'erreur 413, deposez l'APK dans media/app_updates/ puis selectionnez-le ici.",
    )

    class Meta:
        model = AppUpdate
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app_updates_dir = os.path.join(settings.MEDIA_ROOT, 'app_updates')
        choices = [('', 'Aucun fichier serveur')]
        if os.path.isdir(app_updates_dir):
            for filename in sorted(os.listdir(app_updates_dir), reverse=True):
                if filename.lower().endswith('.apk'):
                    choices.append((f'app_updates/{filename}', filename))
        self.fields['server_apk_file'].choices = choices
        if self.instance and self.instance.apk_file:
            self.fields['server_apk_file'].initial = self.instance.apk_file.name

    def save(self, commit=True):
        instance = super().save(commit=False)
        server_apk_file = self.cleaned_data.get('server_apk_file')
        uploaded_apk = self.cleaned_data.get('apk_file')
        if server_apk_file and not uploaded_apk:
            instance.apk_file.name = server_apk_file
        if commit:
            instance.save()
            self.save_m2m()
        return instance

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'duration_days', 'max_screens', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'payment_type', 'account_number', 'is_default', 'created_at']
    list_filter = ['payment_type', 'is_default', 'created_at']
    search_fields = ['user__username', 'account_number', 'account_name']
    readonly_fields = ['created_at']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'start_date', 'end_date', 'auto_renew', 'get_max_screens_display', 'created_at']
    list_filter = ['status', 'auto_renew', 'plan', 'created_at']
    search_fields = ['user__username', 'plan__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'

    def get_max_screens_display(self, obj):
        return obj.get_max_screens()
    get_max_screens_display.short_description = 'Écrans max'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'display_name', 'avatar_initial', 'avatar_color', 'favorite_count', 'recent_watch_count', 'downloads_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'display_name', 'bio']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(AppUpdate)
class AppUpdateAdmin(admin.ModelAdmin):
    form = AppUpdateAdminForm
    list_display = ['version', 'apk_file', 'is_active', 'force_update', 'updated_at']
    list_filter = ['is_active', 'force_update', 'created_at']
    search_fields = ['version', 'message', 'apk_file', 'apk_url']
    readonly_fields = ['created_at', 'updated_at']

class PcAppReleaseAdminForm(forms.ModelForm):
    # Comme pour l'APK: un gros fichier .exe peut dépasser la limite d'envoi
    # (erreur 413). On peut alors le déposer dans media/pc_updates/ puis le
    # choisir ici.
    server_installer_file = forms.ChoiceField(
        label='Installateur deja present sur le serveur',
        required=False,
        choices=[],
        help_text="Pour eviter l'erreur 413, deposez le .exe dans media/pc_updates/ puis selectionnez-le ici.",
    )

    class Meta:
        model = PcAppRelease
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pc_updates_dir = os.path.join(settings.MEDIA_ROOT, 'pc_updates')
        choices = [('', 'Aucun fichier serveur')]
        if os.path.isdir(pc_updates_dir):
            for filename in sorted(os.listdir(pc_updates_dir), reverse=True):
                if filename.lower().endswith(('.exe', '.msi', '.zip')):
                    choices.append((f'pc_updates/{filename}', filename))
        self.fields['server_installer_file'].choices = choices
        if self.instance and self.instance.installer_file:
            self.fields['server_installer_file'].initial = self.instance.installer_file.name

    def clean(self):
        cleaned = super().clean()
        if not (cleaned.get('installer_file') or cleaned.get('server_installer_file') or cleaned.get('download_url')
                or (self.instance and self.instance.installer_file)):
            raise forms.ValidationError("Importez l'installateur, choisissez un fichier du serveur ou indiquez un lien de téléchargement.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        server_file = self.cleaned_data.get('server_installer_file')
        uploaded = self.cleaned_data.get('installer_file')
        if server_file and not uploaded:
            instance.installer_file.name = server_file
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(PcAppRelease)
class PcAppReleaseAdmin(admin.ModelAdmin):
    form = PcAppReleaseAdminForm
    list_display = ['version', 'installer_file', 'download_url', 'is_active', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['version', 'message', 'download_url']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'amount', 'status', 'payment_method', 'payment_date', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'subscription__user__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'payment_date'
    actions = ['validate_payment', 'reject_payment']

    def save_model(self, request, obj, form, change):
        status_changed_to_completed = False
        if change and obj.pk:
            previous_payment = Payment.objects.filter(pk=obj.pk).only('status').first()
            status_changed_to_completed = (
                previous_payment is not None
                and previous_payment.status != 'completed'
                and obj.status == 'completed'
            )

        super().save_model(request, obj, form, change)

        if status_changed_to_completed:
            if not obj.payment_date:
                obj.payment_date = timezone.now()
                obj.save(update_fields=['payment_date', 'updated_at'])

            subscription = obj.subscription
            subscription.status = 'active'
            subscription.save(update_fields=['status', 'updated_at'])

            Notification.objects.create(
                user=subscription.user,
                notification_type='payment_success',
                title='Paiement valide',
                message=f'Votre abonnement {subscription.plan.name} a ete active avec succes. Merci pour votre paiement de {obj.amount} $!',
                expires_at=timezone.now() + timedelta(days=7)
            )

    def validate_payment(self, request, queryset):
        updated = 0
        for payment in queryset.filter(status='pending'):
            payment.status = 'completed'
            payment.payment_date = timezone.now()
            payment.save()
            
            # Activer l'abonnement associé
            subscription = payment.subscription
            subscription.status = 'active'
            subscription.save()
            
            # Créer une notification pour l'utilisateur
            Notification.objects.create(
                user=subscription.user,
                notification_type='payment_success',
                title='Paiement validé',
                message=f'Votre abonnement {subscription.plan.name} a été activé avec succès. Merci pour votre paiement de {payment.amount} $!',
                expires_at=timezone.now() + timedelta(days=2)
            )

            # Créer une notification supplémentaire pour confirmer l'activation
            Notification.objects.create(
                user=subscription.user,
                notification_type='payment_success',
                title='Abonnement activé',
                message=f'Votre abonnement {subscription.plan.name} est maintenant actif. Vous pouvez profiter de tous nos services.',
                expires_at=timezone.now() + timedelta(days=7)
            )
            
            updated += 1
        
        if updated > 0:
            self.message_user(request, f'{updated} paiement(s) validé(s) avec succès.', messages.SUCCESS)
        else:
            self.message_user(request, 'Aucun paiement en attente trouvé.', messages.WARNING)
    
    validate_payment.short_description = 'Valider les paiements sélectionnés'

    def reject_payment(self, request, queryset):
        updated = 0
        for payment in queryset.filter(status='pending'):
            payment.status = 'failed'
            payment.save()
            
            # Désactiver l'abonnement associé
            subscription = payment.subscription
            subscription.status = 'cancelled'
            subscription.save()
            
            # Créer une notification pour l'utilisateur
            Notification.objects.create(
                user=subscription.user,
                notification_type='subscription_expired',
                title='Paiement rejeté',
                message=f'Votre paiement de {payment.amount} $ a été rejeté. Veuillez réessayer.',
                expires_at=timezone.now() + timedelta(days=2)
            )
            
            updated += 1
        
        if updated > 0:
            self.message_user(request, f'{updated} paiement(s) rejeté(s).', messages.SUCCESS)
        else:
            self.message_user(request, 'Aucun paiement en attente trouvé.', messages.WARNING)
    
    reject_payment.short_description = 'Rejeter les paiements sélectionnés'

# Register your models here.


@admin.register(AppContent)
class AppContentAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'title', 'subtitle', 'is_active', 'updated_at']
    list_filter = ['content_type', 'is_active', 'updated_at']
    search_fields = ['title', 'subtitle', 'content']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    """Annonces envoyées à TOUS les utilisateurs (cloche + notification)."""
    list_display = ('title', 'category', 'is_active', 'starts_at', 'ends_at', 'readers_count', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'message')
    list_editable = ('is_active',)
    fields = ('title', 'message', 'category', 'is_active', 'starts_at', 'ends_at')

    @admin.display(description='Lue par')
    def readers_count(self, obj):
        return obj.read_by.count()



# ---------------------------------------------------------------------------
# TV EN DIRECT (FootLive): chaînes gérées ici (plus de Yacine).
# Bouton "Importer une liste M3U" en haut de la liste des chaînes.
# ---------------------------------------------------------------------------
class LiveTvImportForm(forms.Form):
    playlist_file = forms.FileField(
        required=False,
        label="Fichier M3U",
        help_text="Liste de chaînes (.m3u / .m3u8 / .txt), ex: la liste Free-TV.",
    )
    playlist_url = forms.URLField(
        required=False,
        label="ou lien de la liste",
        help_text="Ex: https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    )
    source = forms.CharField(initial="Free-TV", max_length=60, label="Source")
    all_categories = forms.BooleanField(
        required=False,
        label="Activer aussi les catégories par pays",
        help_text="Sinon seules Sport, Chaînes françaises, Afrique, Info et Films sont actives (les autres restent à activer ici).",
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("playlist_file") and not cleaned.get("playlist_url"):
            raise forms.ValidationError("Choisissez un fichier ou collez un lien.")
        return cleaned


@admin.register(LiveTvCategory)
class LiveTvCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active', 'channels_count')
    list_editable = ('order', 'is_active')
    search_fields = ('name',)
    actions = ['activate_categories', 'deactivate_categories']

    @admin.display(description='Chaînes actives')
    def channels_count(self, obj):
        return obj.channels.filter(is_active=True).count()

    @admin.action(description='Activer les catégories sélectionnées')
    def activate_categories(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} catégorie(s) activée(s).', messages.SUCCESS)

    @admin.action(description='Désactiver les catégories sélectionnées')
    def deactivate_categories(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} catégorie(s) désactivée(s).', messages.SUCCESS)


@admin.register(LiveTvChannel)
class LiveTvChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'country', 'source', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active', 'category', 'source')
    search_fields = ('name', 'country', 'stream_url')
    list_select_related = ('category',)
    list_per_page = 100
    actions = ['activate_channels', 'deactivate_channels']
    change_list_template = 'admin/appli/livetvchannel/change_list.html'

    @admin.action(description='Activer les chaînes sélectionnées')
    def activate_channels(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} chaîne(s) activée(s).', messages.SUCCESS)

    @admin.action(description='Désactiver les chaînes sélectionnées')
    def deactivate_channels(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} chaîne(s) désactivée(s).', messages.SUCCESS)

    def get_urls(self):
        from django.urls import path
        custom = [
            path(
                'import-m3u/',
                self.admin_site.admin_view(self.import_m3u_view),
                name='appli_livetvchannel_import_m3u',
            ),
        ]
        return custom + super().get_urls()

    def import_m3u_view(self, request):
        import urllib.request
        from django.shortcuts import redirect
        from django.template.response import TemplateResponse
        from .live_tv_m3u import MAIN_CATEGORIES, import_channels

        if not self.has_add_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        form = LiveTvImportForm(request.POST or None, request.FILES or None)
        if request.method == 'POST' and form.is_valid():
            try:
                upload = form.cleaned_data.get('playlist_file')
                if upload:
                    text = upload.read().decode('utf-8', errors='replace')
                else:
                    req = urllib.request.Request(
                        form.cleaned_data['playlist_url'],
                        headers={'User-Agent': 'JessnaCineHub/1.0'},
                    )
                    with urllib.request.urlopen(req, timeout=60) as response:
                        text = response.read().decode('utf-8', errors='replace')
            except Exception as error:
                self.message_user(request, f'Impossible de lire la liste: {error}', messages.ERROR)
            else:
                activate = None if form.cleaned_data.get('all_categories') else {name for name, _ in MAIN_CATEGORIES}
                summary = import_channels(text, source=form.cleaned_data.get('source') or 'Free-TV', activate_categories=activate)
                rejected = sum(summary['rejected'].values())
                self.message_user(
                    request,
                    f"{summary['created']} chaîne(s) ajoutée(s), {summary['updated']} mise(s) à jour, "
                    f"{rejected} écartée(s) (non officielles, payantes ou illisibles par l'application).",
                    messages.SUCCESS,
                )
                return redirect('admin:appli_livetvchannel_changelist')

        context = {
            **self.admin_site.each_context(request),
            'title': 'Importer une liste de chaînes (M3U)',
            'form': form,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/appli/livetvchannel/import_m3u.html', context)
