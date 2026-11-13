# TV en direct: signalements des chaînes qui ne marchent plus.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appli', '0019_live_tv'),
    ]

    operations = [
        migrations.AddField(
            model_name='livetvchannel',
            name='failure_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Échecs signalés'),
        ),
        migrations.AddField(
            model_name='livetvchannel',
            name='last_failure_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Dernier échec'),
        ),
        migrations.AddField(
            model_name='livetvchannel',
            name='last_success_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Dernière lecture réussie'),
        ),
    ]
