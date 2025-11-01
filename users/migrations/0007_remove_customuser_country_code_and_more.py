from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_customuser_country_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='country_code',
        ),
        migrations.AlterField(
            model_name='customuser',
            name='payment_method',
            field=models.CharField(blank=True, choices=[('credit_card', 'Credit Card'), ('cash', 'Cash')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
    ]
