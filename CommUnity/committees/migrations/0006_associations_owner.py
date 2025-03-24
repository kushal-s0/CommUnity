# Generated by Django 5.1.6 on 2025-03-24 10:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('committees', '0005_remove_associations_edit_request_data_and_more'),
        ('members', '0008_alter_coremember_assosiation'),
    ]

    operations = [
        migrations.AddField(
            model_name='associations',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_associations', to='members.coremember'),
        ),
    ]
