# Generated by Django 4.1.9 on 2023-07-03 19:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0002_output_warning"),
    ]

    operations = [
        migrations.AddField(
            model_name="output",
            name="sensitive",
            field=models.BooleanField(default=False),
        ),
    ]
