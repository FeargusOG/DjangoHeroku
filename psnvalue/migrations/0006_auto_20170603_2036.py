# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-06-03 20:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('psnvalue', '0005_auto_20170523_1926'),
    ]

    operations = [
        migrations.AddField(
            model_name='library',
            name='library_rating_mean',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='library',
            name='library_rating_stdev',
            field=models.FloatField(default=0.0),
        ),
    ]
