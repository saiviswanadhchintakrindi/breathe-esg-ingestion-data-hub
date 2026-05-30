from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='normalizedrecord',
            name='client_environment',
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                help_text="Client environment tag e.g. Production, Staging, Dev, UAT"
            ),
        ),
    ]
