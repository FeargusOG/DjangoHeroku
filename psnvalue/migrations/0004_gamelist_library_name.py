# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-04-16 17:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('psnvalue', '0003_library_library_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamelist',
            name='library_name',
            field=models.OneToOneField(default=0, on_delete=django.db.models.deletion.CASCADE, to='psnvalue.Library'),
            preserve_default=False,
        ),
    ]