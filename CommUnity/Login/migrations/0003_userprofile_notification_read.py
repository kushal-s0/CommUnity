# Generated by Django 5.1.6 on 2025-04-13 16:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Login', '0002_userprofile_preferences'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='notification_read',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
