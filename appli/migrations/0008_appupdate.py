from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appli', '0007_userprofile_phone'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppUpdate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(help_text='Version APK affichee aux utilisateurs', max_length=50)),
                ('apk_url', models.URLField(help_text="Lien direct de telechargement de l'APK")),
                ('message', models.TextField(default="Une nouvelle version de l'application est disponible.")),
                ('is_active', models.BooleanField(default=False, help_text="Activer pour afficher la notification dans l'application mobile")),
                ('force_update', models.BooleanField(default=False, help_text='Indique si la mise a jour est obligatoire')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
    ]
