# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-15 15:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0017_Adding_indeces_for_location_and_legal_entity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='legalentity',
            name='recipient_unique_id',
            field=models.TextField(blank=True, db_index=True, null=True, verbose_name='DUNS Number'),
        ),
        migrations.AlterField(
            model_name='location',
            name='address_line1',
            field=models.TextField(blank=True, db_index=True, null=True, verbose_name='Address Line 1'),
        ),
        migrations.AlterField(
            model_name='location',
            name='address_line2',
            field=models.TextField(blank=True, db_index=True, null=True, verbose_name='Address Line 2'),
        ),
        migrations.AlterField(
            model_name='location',
            name='address_line3',
            field=models.TextField(blank=True, db_index=True, null=True, verbose_name='Address Line 3'),
        ),
        migrations.AlterField(
            model_name='location',
            name='city_name',
            field=models.TextField(blank=True, db_index=True, null=True, verbose_name='City Name'),
        ),
        migrations.AlterField(
            model_name='location',
            name='state_code',
            field=models.TextField(blank=True, db_index=True, null=True, verbose_name='State Code'),
        ),
        migrations.AlterField(
            model_name='location',
            name='zip5',
            field=models.TextField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='location',
            name='zip_last4',
            field=models.TextField(blank=True, db_index=True, null=True),
        ),
    ]
