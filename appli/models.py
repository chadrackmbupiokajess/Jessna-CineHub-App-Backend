from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('payment_success', 'Paiement réussi'),
        ('subscription_expiring', 'Abonnement expire bientôt'),
        ('subscription_expired', 'Abonnement expiré'),
        ('subscription_renewed', 'Abonnement renouvelé'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def is_active(self):
        if self.expires_at:
            return timezone.now() < self.expires_at and not self.is_read
        return not self.is_read
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(help_text="Durée en jours")
    features = models.JSONField(default=list, help_text="Liste des fonctionnalités")
    max_screens = models.IntegerField(default=2, help_text="Nombre d'écrans simultanés autorisés")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class PaymentMethod(models.Model):
    PAYMENT_TYPES = [
        ('airtel', 'Airtel Money'),
        ('orange', 'Orange Money'),
        ('mpesa', 'M-PESA'),
        ('paypal', 'PayPal'),
        ('bank', 'Compte Bancaire'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    account_number = models.CharField(max_length=100, blank=True)
    account_name = models.CharField(max_length=100, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_payment_type_display()}"

class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('expired', 'Expiré'),
        ('cancelled', 'Annulé'),
        ('pending', 'En attente'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    custom_max_screens = models.IntegerField(null=True, blank=True, help_text="Nombre d'écrans personnalisé (remplace celui du plan)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        return self.status == 'active' and self.end_date > timezone.now()

    def get_max_screens(self):
        """Retourne le nombre d'écrans autorisés (personnalisé ou par défaut du plan)"""
        if self.custom_max_screens is not None:
            return self.custom_max_screens
        return self.plan.max_screens

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('refunded', 'Remboursé'),
    ]
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=200, unique=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} - {self.amount}"

# Create your models here.
