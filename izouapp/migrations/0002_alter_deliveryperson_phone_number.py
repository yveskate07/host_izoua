# Generated by Django 5.1.4 on 2024-12-26 23:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("izouapp", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="deliveryperson",
            name="phone_number",
            field=models.CharField(blank=True, default="", max_length=20, null=True),
        ),
    ]