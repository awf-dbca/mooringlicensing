# Generated by Django 5.0.9 on 2024-09-17 02:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mooringlicensing', '0356_alter_proposalsitelicenseemooringrequest_mooring_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposalsitelicenseemooringrequest',
            name='approved_by_endorser',
            field=models.BooleanField(default=False),
        ),
    ]
