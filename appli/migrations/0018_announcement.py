# Annonces envoyées à tous les utilisateurs (promotions, nouveautés...).

import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('appli', '0017_viewer_profiles'),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text="Titre court, ex: -50 % sur l'abonnement mensuel", max_length=120)),
                ('message', models.TextField(help_text='Message envoyé à tous les utilisateurs')),
                ('category', models.CharField(choices=[('promotion', 'Promotion / prix'), ('new_content', 'Nouveaux films et séries'), ('info', 'Information'), ('maintenance', 'Maintenance')], default='info', max_length=20)),
                ('is_active', models.BooleanField(default=True, help_text="Décocher pour retirer l'annonce de l'application")),
                ('starts_at', models.DateTimeField(default=django.utils.timezone.now, help_text="L'annonce est envoyée à partir de cette date")),
                ('ends_at', models.DateTimeField(blank=True, help_text='Date de fin (optionnel), ex: fin de la promotion', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_by', models.ManyToManyField(blank=True, editable=False, related_name='read_announcements', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Annonce',
                'verbose_name_plural': 'Annonces',
                'ordering': ['-starts_at'],
            },
        ),
    ]
