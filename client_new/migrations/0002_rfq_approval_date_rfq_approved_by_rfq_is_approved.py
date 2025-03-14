# Generated by Django 5.1.1 on 2025-03-05 09:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BaseApp', '0001_initial'),
        ('client_new', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='rfq',
            name='approval_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rfq',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_rfqs', to='BaseApp.employee'),
        ),
        migrations.AddField(
            model_name='rfq',
            name='is_approved',
            field=models.BooleanField(default=False),
        ),
    ]
