# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-11 07:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mooringlicensing', '0112_auto_20210511_1223'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='proposal',
            name='company_ownership',
        ),
        migrations.AddField(
            model_name='proposal',
            name='company_ownership_name',
            field=models.CharField(blank=True, max_length=200, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='proposal',
            name='company_ownership_percentage',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]