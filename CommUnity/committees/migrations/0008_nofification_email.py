# Generated by Django 5.1.6 on 2025-03-10 19:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('committees', '0007_nofification'),
    ]

    operations = [
        migrations.AddField(
            model_name='nofification',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
