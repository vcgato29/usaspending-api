# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-05-16 03:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0015_update_ref_program_activity_table'),
    ]

    operations = [
        migrations.CreateModel(
            name='GTASTotalObligation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fiscal_year', models.IntegerField()),
                ('fiscal_quarter', models.IntegerField()),
                ('total_obligation', models.DecimalField(decimal_places=2, max_digits=25)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'gtas_total_obligation',
                'managed': True,
            },
        ),
        migrations.AlterUniqueTogether(
            name='gtastotalobligation',
            unique_together=set([('fiscal_year', 'fiscal_quarter')]),
        ),
    ]