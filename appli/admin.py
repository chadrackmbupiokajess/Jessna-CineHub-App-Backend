import os

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.utils import timezone
from datetime import timedelta
from .models import AppUpdate, SubscriptionPlan, PaymentMethod, Subscription, Payment, Notification, UserProfile, AppContent


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
