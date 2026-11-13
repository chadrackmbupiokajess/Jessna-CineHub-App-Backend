# TV en direct (FootLive): catégories et chaînes gérées depuis l'admin.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appli', '0018_announcement'),
    ]

    operations = [
        migrations.CreateModel(
            name='LiveTvCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nom')),
                ('logo_url', models.URLField(blank=True, max_length=500, verbose_name='Logo (lien)')),
                ('order', models.PositiveIntegerField(default=100, help_text='Plus petit = affiché en premier', verbose_name='Ordre')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'TV en direct - catégorie',
                'verbose_name_plural': 'TV en direct - catégories',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='LiveTvChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='Nom')),
                ('logo_url', models.URLField(blank=True, max_length=500, verbose_name='Logo (lien)')),
                ('stream_url', models.URLField(max_length=1000, verbose_name='Lien du flux (.m3u8)')),
                ('referer', models.CharField(blank=True, max_length=500, verbose_name="Referer (si le flux l'exige)")),
                ('user_agent', models.CharField(blank=True, max_length=300, verbose_name="User-Agent (si le flux l'exige)")),
                ('country', models.CharField(blank=True, max_length=60, verbose_name='Pays')),
                ('source', models.CharField(blank=True, help_text='Ex: Free-TV, partenaire, ajout manuel', max_length=60, verbose_name='Source')),
                ('order', models.PositiveIntegerField(default=100, verbose_name='Ordre')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='channels', to='appli.livetvcategory', verbose_name='Catégorie')),
            ],
            options={
                'verbose_name': 'TV en direct - chaîne',
                'verbose_name_plural': 'TV en direct - chaînes',
                'ordering': ['category__order', 'order', 'name'],
            },
        ),
    ]
