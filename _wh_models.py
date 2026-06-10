import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'ERP_Shop.settings'
import django
django.setup()

with open('company/models.py', 'r', encoding='utf-8') as f:
    c = f.read()

# ── 1. Add Country & StateProvince before CompanyCustomization ──
country_models = '''


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
insert_pos = c.find('\n\nclass CompanyCustomization')
c = c[:insert_pos] + country_models + c[insert_pos:]

# ── 2. Add fields to Warehouse model ──
# Find the code line end
wh_start = c.find('class Warehouse(models.Model):')
code_start = c.find('max_length=20, unique=True, help_text="Unique warehouse code"', wh_start)
code_line_end = c.find('\n', code_start)

new_fields = '''

    country_ref = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name="warehouses")
    state_ref = models.ForeignKey(StateProvince, on_delete=models.SET_NULL, null=True, blank=True, related_name="warehouses")
    arabic_country = models.CharField(max_length=100, blank=True, null=True)
    arabic_state = models.CharField(max_length=100, blank=True, null=True)
    arabic_city = models.CharField(max_length=100, blank=True, null=True)
    arabic_building_no = models.CharField(max_length=50, blank=True, null=True)
    arabic_street_name = models.CharField(max_length=200, blank=True, null=True)
    arabic_district = models.CharField(max_length=100, blank=True, null=True)
    arabic_additional_no = models.CharField(max_length=50, blank=True, null=True)
    arabic_zip_code = models.CharField(max_length=20, blank=True, null=True)
    building_no = models.CharField(max_length=50, blank=True, null=True)
    street_name = models.CharField(max_length=200, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    additional_no = models.CharField(max_length=50, blank=True, null=True)
'''

c = c[:code_line_end+1] + new_fields + c[code_line_end+1:]

with open('company/models.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Models written OK')

# ── 3. Run migration ──
from django.core.management import call_command
call_command('makemigrations', 'company')
call_command('migrate', 'company')
print('Migrations OK')
