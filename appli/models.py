import secrets
import string
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('payment_success', 'Paiement réussi'),
        ('payment_pending', 'Paiement en cours'),
        ('payment_failed', 'Paiement échoué'),
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

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=100, blank=True)
    avatar_initial = models.CharField(max_length=2, blank=True)
    avatar_color = models.CharField(max_length=7, default='#ff2d55')
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    favorite_count = models.IntegerField(default=0)
    recent_watch_count = models.IntegerField(default=0)
    downloads_count = models.IntegerField(default=0)
    # Code parental (4 chiffres) du profil Parent, stocké HACHÉ (jamais en clair).
    parental_pin = models.CharField(max_length=128, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.display_name or self.user.username}"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(hours=1)

    def __str__(self):
        return f"{self.user.username} - {'utilise' if self.used_at else 'actif'}"

class AppUpdate(models.Model):
    version = models.CharField(max_length=50, help_text="Version APK affichee aux utilisateurs")
    apk_file = models.FileField(upload_to='app_updates/', blank=True, null=True, help_text="Importer le fichier APK de la nouvelle version")
    apk_url = models.URLField(blank=True, help_text="Ancien lien direct de téléchargement de l'APK (optionnel)")
    message = models.TextField(default="Une nouvelle version de l'application est disponible.")
    is_active = models.BooleanField(default=False, help_text="Activer pour afficher la notification dans l'application mobile")
    force_update = models.BooleanField(default=False, help_text="Indique si la mise a jour est obligatoire")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            AppUpdate.objects.exclude(pk=self.pk).update(is_active=False)

    def __str__(self):
        return f"APK {self.version}"

    def get_download_url(self, request=None):
        if self.apk_file:
            url = self.apk_file.url
            url = request.build_absolute_uri(url) if request else url
            # PythonAnywhere est en HTTPS, mais Django voit la requête en
            # HTTP derrière leur proxy: Android refuse les liens "http://".
            if url.startswith('http://') and '.pythonanywhere.com' in url:
                url = 'https://' + url[len('http://'):]
            return url
        return self.apk_url

class PcAppRelease(models.Model):
    """
    Version de l'application PC (Windows), gérée dans l'admin comme l'APK
    (AppUpdate). Le lien de la version ACTIVE est proposé sur la page de
    partage quand on ouvre un lien depuis un ordinateur.
    """
    version = models.CharField(max_length=50, help_text="Version de l'application PC (ex: 2.3.3)")
    installer_file = models.FileField(
        upload_to='pc_updates/',
        blank=True,
        null=True,
        help_text="Importer l'installateur Windows (.exe) de la nouvelle version",
    )
    download_url = models.URLField(
        blank=True,
        help_text="OU lien public de téléchargement (GitHub, Google Drive, Mega...). Utilisé si aucun fichier n'est importé.",
    )
    message = models.TextField(default="Téléchargez Jessna CinéHub pour Windows.", blank=True)
    is_active = models.BooleanField(default=False, help_text="Activer pour proposer cette version sur la page de partage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Version PC'
        verbose_name_plural = 'Versions PC'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Une seule version PC active à la fois (comme pour l'APK).
        if self.is_active:
            PcAppRelease.objects.exclude(pk=self.pk).update(is_active=False)

    def __str__(self):
        return f"PC {self.version}"

    def get_download_url(self, request=None):
        if self.installer_file:
            url = self.installer_file.url
            return request.build_absolute_uri(url) if request else url
        return self.download_url

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
        ('cinetpay', 'CinetPay'),
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

class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_history')
    movie_title = models.CharField(max_length=255)
    movie_slug = models.CharField(max_length=255)
    movie_poster = models.URLField(blank=True)
    content_type = models.CharField(max_length=20, choices=[('movie', 'Film'), ('tv', 'Série')])
    season = models.IntegerField(null=True, blank=True)
    episode = models.IntegerField(null=True, blank=True)
    episode_title = models.CharField(max_length=255, blank=True)
    watched_at = models.DateTimeField(auto_now_add=True)
    progress_percentage = models.IntegerField(default=0, help_text="Pourcentage de visionnage")
    duration_watched = models.IntegerField(default=0, help_text="Durée visionnée en secondes")
    # Profil qui a regardé: 'parent' (par défaut) ou 'kids' (profil Enfant).
    viewer = models.CharField(max_length=10, default='parent', db_index=True)

    class Meta:
        ordering = ['-watched_at']

    def __str__(self):
        return f"{self.user.username} - {self.movie_title}"

class MyListItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_list_items')
    movie_title = models.CharField(max_length=255)
    movie_slug = models.CharField(max_length=255)
    movie_poster = models.URLField(blank=True)
    content_type = models.CharField(max_length=20, choices=[('movie', 'Film'), ('tv', 'Série')], default='movie')
    # Profil propriétaire de l'entrée: 'parent' (par défaut) ou 'kids'.
    viewer = models.CharField(max_length=10, default='parent', db_index=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        unique_together = ('user', 'movie_slug', 'viewer')

    def __str__(self):
        return f"{self.user.username} - {self.movie_title}"

class SharedLink(models.Model):
    code = models.CharField(max_length=12, unique=True, db_index=True)
    movie_title = models.CharField(max_length=255)
    movie_slug = models.CharField(max_length=255)
    movie_poster = models.URLField(blank=True)
    content_type = models.CharField(max_length=20, choices=[('movie', 'Film'), ('tv', 'Série')], default='movie')
    category = models.CharField(max_length=255, blank=True)
    release_date = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def generate_code(length=7):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def save(self, *args, **kwargs):
        if not self.code:
            new_code = self.generate_code()
            while SharedLink.objects.filter(code=new_code).exists():
                new_code = self.generate_code()
            self.code = new_code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.movie_title}"

class AppContent(models.Model):
    CONTENT_TYPES = [
        ('help', 'Aide'),
        ('contact', 'Nous contacter'),
        ('about', 'À propos de l\'application'),
        ('account', 'Compte'),
    ]
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, unique=True)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    content = models.TextField(help_text="Contenu détaillé de la page")
    contact_email = models.EmailField(blank=True, help_text="Email de contact pour la page Nous contacter")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Téléphone de contact")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['content_type']

    def __str__(self):
        return f"{self.get_content_type_display()} - {self.title}"

# Create your models here.


class Announcement(models.Model):
    """
    ANNONCE ENVOYÉE À TOUS LES UTILISATEURS (promotion de prix, nouveautés,
    information, maintenance...). Elle apparaît dans la cloche de l'appli
    et en notification sur le téléphone (avec le jingle), une seule fois
    par utilisateur.
    """
    CATEGORY_CHOICES = [
        ('promotion', 'Promotion / prix'),
        ('new_content', 'Nouveaux films et séries'),
        ('info', 'Information'),
        ('maintenance', 'Maintenance'),
    ]

    title = models.CharField(max_length=120, help_text="Titre court, ex: -50 % sur l'abonnement mensuel")
    message = models.TextField(help_text="Message envoyé à tous les utilisateurs")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='info')
    is_active = models.BooleanField(default=True, help_text="Décocher pour retirer l'annonce de l'application")
    starts_at = models.DateTimeField(default=timezone.now, help_text="L'annonce est envoyée à partir de cette date")
    ends_at = models.DateTimeField(null=True, blank=True, help_text="Date de fin (optionnel), ex: fin de la promotion")
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, blank=True, related_name='read_announcements', editable=False)

    class Meta:
        ordering = ['-starts_at']
        verbose_name = 'Annonce'
        verbose_name_plural = 'Annonces'

    def is_live(self):
        now = timezone.now()
        return self.is_active and self.starts_at <= now and (self.ends_at is None or self.ends_at > now)

    def __str__(self):
        return self.title



class LiveTvCategory(models.Model):
    """
    TV EN DIRECT (FootLive): catégorie de chaînes affichée dans l'application
    (Sport, Chaînes françaises, Afrique, Info...). Décocher "Active" pour la
    retirer de l'application sans rien supprimer.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='Nom')
    logo_url = models.URLField(max_length=500, blank=True, verbose_name='Logo (lien)')
    order = models.PositiveIntegerField(default=100, verbose_name='Ordre', help_text="Plus petit = affiché en premier")
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'TV en direct - catégorie'
        verbose_name_plural = 'TV en direct - catégories'

    def __str__(self):
        return self.name


class LiveTvChannel(models.Model):
    """
    TV EN DIRECT (FootLive): une chaîne et son lien de diffusion (HLS .m3u8).
    N'ajoutez que des chaînes gratuites et officielles, ou celles que vous avez
    le droit de diffuser (partenaire, fournisseur sous licence).
    """
    category = models.ForeignKey(LiveTvCategory, on_delete=models.CASCADE, related_name='channels', verbose_name='Catégorie')
    name = models.CharField(max_length=150, verbose_name='Nom')
    logo_url = models.URLField(max_length=500, blank=True, verbose_name='Logo (lien)')
    stream_url = models.URLField(max_length=1000, verbose_name='Lien du flux (.m3u8)')
    referer = models.CharField(max_length=500, blank=True, verbose_name='Referer (si le flux l\'exige)')
    user_agent = models.CharField(max_length=300, blank=True, verbose_name='User-Agent (si le flux l\'exige)')
    country = models.CharField(max_length=60, blank=True, verbose_name='Pays')
    source = models.CharField(max_length=60, blank=True, verbose_name='Source', help_text="Ex: Free-TV, partenaire, ajout manuel")
    order = models.PositiveIntegerField(default=100, verbose_name='Ordre')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__order', 'order', 'name']
        verbose_name = 'TV en direct - chaîne'
        verbose_name_plural = 'TV en direct - chaînes'

    def __str__(self):
        return f"{self.name} ({self.category})"
