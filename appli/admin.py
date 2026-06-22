from django.contrib import admin, messages
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPlan, PaymentMethod, Subscription, Payment, Notification


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
    list_display = ['user', 'plan', 'status', 'start_date', 'end_date', 'auto_renew', 'get_max_screens_display',
                    'created_at']
    list_filter = ['status', 'auto_renew', 'plan', 'created_at']
    search_fields = ['user__username', 'plan__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'

    def get_max_screens_display(self, obj):
        return obj.get_max_screens()

    get_max_screens_display.short_description = 'Écrans max'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'amount', 'status', 'payment_method', 'payment_date', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'subscription__user__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'payment_date'
    actions = ['validate_payment', 'reject_payment']

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
