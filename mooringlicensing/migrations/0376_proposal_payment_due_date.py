# Generated by Django 5.0.9 on 2024-11-28 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mooringlicensing', '0375_dcvpermit_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='payment_due_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
