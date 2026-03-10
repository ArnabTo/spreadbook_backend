from django.db import models
# from .product_model import Product


class Category(models.Model):
    # product  = models.ForeignKey(Product,related_name='category', on_delete=models.CASCADE, null=True) 
    name = models.CharField(max_length=50, null=True, blank=True)
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    branchId = models.ManyToManyField(
        "company.Branch",
        blank=True,
        help_text="Branches this user can access",
    )

    is_active = models.BooleanField(default=True, null=True, blank=True)
    

    def __str__(self):
        """String for representing the Model object."""
        return self.name
