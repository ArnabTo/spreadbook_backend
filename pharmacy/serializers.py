from rest_framework import serializers

from .models import Prescription, PrescriptionItem


class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = "__all__"
        read_only_fields = ["id"]


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, required=False)

    class Meta:
        model = Prescription
        fields = "__all__"
        read_only_fields = [
            "id",
            "submitted_at",
            "approved_at",
            "approved_by",
            "rejected_at",
            "rejected_by",
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        prescription = Prescription.objects.create(**validated_data)
        for item in items_data:
            PrescriptionItem.objects.create(prescription=prescription, **item)
        return prescription

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item in items_data:
                PrescriptionItem.objects.create(prescription=instance, **item)

        return instance
