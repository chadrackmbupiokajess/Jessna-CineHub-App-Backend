from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appli', '0014_sharedlink'),
    ]

    operations = [
        migrations.CreateModel(
            name='PcAppRelease',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(help_text="Version de l'application PC (ex: 2.3.3)", max_length=50)),
                ('installer_file', models.FileField(blank=True, help_text="Importer l'installateur Windows (.exe) de la nouvelle version", null=True, upload_to='pc_updates/')),
                ('download_url', models.URLField(blank=True, help_text='OU lien public de téléchargement (GitHub, Google Drive, Mega...). Utilisé si aucun fichier n\'est importé.')),
                ('message', models.TextField(blank=True, default='Téléchargez Jessna CinéHub pour Windows.')),
                ('is_active', models.BooleanField(default=False, help_text='Activer pour proposer cette version sur la page de partage')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Version PC',
                'verbose_name_plural': 'Versions PC',
                'ordering': ['-updated_at'],
            },
        ),
    ]
