# Generated by Django 4.1.9 on 2023-07-03 14:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="output",
            name="warning",
            field=models.TextField(blank=True),
        ),
    ]
