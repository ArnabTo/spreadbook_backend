from rest_framework import serializers
from .models import ServiceItem, ProductService





class ProductServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    company_name = serializers.CharField(source="company.name", read_only=True, default=None)

    class Meta:
        model = ProductService
        fields = [
            "id",
            "company",
            "company_name",
            "name",
            "code",
            "arabic_name",
            "category",
            "category_name",
            "is_tax_applied",
            "tax_rate",
            "sales_price",
            "quality_applicable",
            "minimum_sales_rate",
            "avg_qty",
            "is_active",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = ("id", "company", "createdAt", "updatedAt")

    def validate(self, data):
        if data.get("is_tax_applied") and not data.get("tax_rate"):
            raise serializers.ValidationError({"tax_rate": "Tax rate is required when tax is applied."})
        if data.get("minimum_sales_rate") and data.get("sales_price"):
            if float(data["minimum_sales_rate"]) > float(data["sales_price"]):
                raise serializers.ValidationError({"minimum_sales_rate": "Cannot exceed sales price."})
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            if hasattr(request.user, "companyId") and request.user.companyId:
                validated_data["company"] = request.user.companyId
        return super().create(validated_data)

class ServiceItemSerializer(serializers.ModelSerializer):
     class Meta:
          model = ServiceItem
          fields = '__all__'
          lookup_field = 'slug'
          extra_kwargs = {
               'url': {'lookup_field': 'slug'},
               # 'comments': {'required': False},
          }
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)