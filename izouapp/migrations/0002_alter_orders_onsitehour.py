# Generated by Django 5.1.4 on 2024-12-30 12:50

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('izouapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='onSiteHour',
            field=models.TimeField(default=datetime.time(12, 50, 48, 862582)),
        ),
    ]
