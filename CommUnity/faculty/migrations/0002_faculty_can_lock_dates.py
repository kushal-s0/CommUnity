# Generated by Django 5.1.6 on 2025-04-15 18:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='faculty',
            name='can_lock_dates',
            field=models.BooleanField(default=False),
        ),
    ]
