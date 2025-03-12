# Generated by Django 5.1.1 on 2025-03-12 10:33

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('BaseApp', '0001_initial'),
        ('client_new', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Timesheet',
            fields=[
                ('timesheet_id', models.AutoField(primary_key=True, serialize=False)),
                ('hours_logged', models.DecimalField(decimal_places=2, max_digits=5)),
                ('hourly_rate', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date_logged', models.DateField(default=django.utils.timezone.now)),
                ('remarks', models.TextField(blank=True, null=True)),
                ('total_amount', models.DecimalField(decimal_places=2, editable=False, max_digits=10)),
                ('job_card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='client_new.jobcard')),
                ('team_member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='BaseApp.employee')),
            ],
        ),
    ]
