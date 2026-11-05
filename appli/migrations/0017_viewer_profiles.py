from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appli', '0016_userprofile_parental_pin'),
    ]

    operations = [
        migrations.AddField(
            model_name='watchhistory',
            name='viewer',
            field=models.CharField(db_index=True, default='parent', max_length=10),
        ),
        migrations.AddField(
            model_name='mylistitem',
            name='viewer',
            field=models.CharField(db_index=True, default='parent', max_length=10),
        ),
        migrations.AlterUniqueTogether(
            name='mylistitem',
            unique_together={('user', 'movie_slug', 'viewer')},
        ),
    ]
