# Generated by Django 5.1.6 on 2025-03-15 07:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('Login', '0001_initial'),
        ('committees', '0001_initial'),
        ('faculty', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('date_time', models.DateTimeField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='faculty.faculty')),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='committees.associations')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_events', to='Login.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('location', models.CharField(choices=[('online', 'Online'), ('auditorium', 'Auditorium'), ('open canteen', 'Open Canteen'), ('turf', 'Turf'), ('vidya vihar', 'Vidya Vihar'), ('other', 'Other')], default='other', max_length=255)),
                ('booked_from', models.DateTimeField()),
                ('booked_to', models.DateTimeField()),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='event_location', to='events.event')),
            ],
        ),
        migrations.AddField(
            model_name='event',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='event_location', to='events.location'),
        ),
    ]
