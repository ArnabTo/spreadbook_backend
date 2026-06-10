with open('company/models.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Find Branch class end (it's before Warehouse)
branch_save_end = c.find('\n\nclass Warehouse(models.Model):')
# Country/StateProvince must go BEFORE Warehouse

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

c = c[:branch_save_end] + country_models + c[branch_save_end:]

# Now add fields to Warehouse after code
old = '''    code = models.CharField(
        max_length=20, unique=True, help_text="Unique warehouse code"
    )

    phoneNumber'''
new = '''    code = models.CharField(
        max_length=20, unique=True, help_text="Unique warehouse code"
    )

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

    phoneNumber'''
c = c.replace(old, new)

with open('company/models.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')
