from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appli', '0015_pcapprelease'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='parental_pin',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
