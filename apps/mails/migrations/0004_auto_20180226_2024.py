# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-26 20:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mails', '0003_auto_20180226_2016'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='value',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
