from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Bus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bus_number', models.CharField(max_length=50, unique=True)),
                ('bus_type', models.CharField(max_length=100)),
                ('location', models.CharField(max_length=200)),
                ('current_mileage', models.PositiveIntegerField()),
                ('is_articulating', models.BooleanField(default=False)),
                ('min_rotor_thickness', models.DecimalField(decimal_places=2, max_digits=5)),
            ],
            options={
                'ordering': ['bus_number'],
            },
        ),
        migrations.CreateModel(
            name='RotorMeasurement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.CharField(max_length=20)),
                ('measurement_date', models.DateField()),
                ('mileage_at_measurement', models.PositiveIntegerField()),
                ('thickness_mm', models.DecimalField(decimal_places=3, max_digits=6)),
                ('bus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rotor_measurements', to='buses.bus')),
            ],
            options={
                'ordering': ['measurement_date', 'id'],
                'unique_together': {('bus', 'position', 'measurement_date')},
            },
        ),
    ]
