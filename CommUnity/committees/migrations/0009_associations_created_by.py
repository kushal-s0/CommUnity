# Generated by Django 5.1.6 on 2025-03-11 14:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('committees', '0008_nofification_email'),
        ('members', '0004_member_position'),
    ]

    operations = [
        migrations.AddField(
            model_name='associations',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.coremember'),
        ),
    ]
