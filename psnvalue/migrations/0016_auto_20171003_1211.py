# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-10-03 12:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('psnvalue', '0015_gamelist_image_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gamelist',
            name='image_data',
            field=models.TextField(),
        ),
    ]
