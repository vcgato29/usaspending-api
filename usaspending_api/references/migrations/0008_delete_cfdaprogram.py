# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-05-15 18:48
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0007_migrate_cfda_data'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CFDAProgram',
        ),
    ]