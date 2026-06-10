import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'ERP_Shop.settings'
import django
django.setup()

# ── Add Country & StateProvince models to company/models.py ──
with open('company/models.py', 'r', encoding='utf-8') as f:
    c = f.read()

if 'class Country' not in c:
    country_model = '''

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    arabic_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ["name"]

    def __str__(self):
        return self.name


class StateProvince(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="states")
    name = models.CharField(max_length=100)
    arabic_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "States / Provinces"
        ordering = ["country", "name"]
        unique_together = ["country", "name"]

    def __str__(self):
        return f"{self.name}, {self.country.name}"
'''
    # Insert before the last class or at end
    insert_pos = c.rfind('\n\nclass CompanyCustomization')
    if insert_pos > 0:
        c = c[:insert_pos] + country_model + '\n' + c[insert_pos:]
    else:
        c += country_model
    with open('company/models.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Country & StateProvince models added')
else:
    print('Country model already exists')

# ── Run migration ──
from django.core.management import call_command
call_command('makemigrations', 'company')
call_command('migrate', 'company')
print('Migrations applied')
