from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appli', '0009_appcontent'),
    ]

    operations = [
        migrations.AddField(
            model_name='appupdate',
            name='apk_file',
            field=models.FileField(blank=True, help_text='Importer le fichier APK de la nouvelle version', null=True, upload_to='app_updates/'),
        ),
        migrations.AlterField(
            model_name='appupdate',
            name='apk_url',
            field=models.URLField(blank=True, help_text="Ancien lien direct de telechargement de l'APK (optionnel)"),
        ),
    ]
