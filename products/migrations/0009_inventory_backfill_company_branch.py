from django.db import migrations


def forwards(apps, schema_editor):
    InventoryItem = apps.get_model("products", "InventoryItem")
    InventoryCategory = apps.get_model("products", "InventoryCategory")

    # Backfill InventoryItem.companyId / branch from linked Product.
    # Only sets fields when currently NULL to avoid overwriting curated values.
    qs = (
        InventoryItem.objects.filter(product__isnull=False)
        .filter(companyId__isnull=True)
        .select_related("product")
        .only(
            "id",
            "companyId_id",
            "branch_id",
            "product__companyId_id",
            "product__branch_id",
        )
    )

    batch = []
    for item in qs.iterator(chunk_size=1000):
        product = getattr(item, "product", None)
        if not product:
            continue

        desired_company_id = getattr(product, "companyId_id", None)
        desired_branch_id = getattr(product, "branch_id", None)

        if desired_company_id is None and desired_branch_id is None:
            continue

        updates = {}
        if item.companyId_id is None and desired_company_id is not None:
            updates["companyId_id"] = desired_company_id
        if getattr(item, "branch_id", None) is None and desired_branch_id is not None:
            updates["branch_id"] = desired_branch_id

        if updates:
            updates["id"] = item.id
            batch.append(updates)

        if len(batch) >= 1000:
            for row in batch:
                InventoryItem.objects.filter(id=row["id"]).update(
                    **{k: v for k, v in row.items() if k != "id"}
                )
            batch.clear()

    if batch:
        for row in batch:
            InventoryItem.objects.filter(id=row["id"]).update(
                **{k: v for k, v in row.items() if k != "id"}
            )

    # Backfill InventoryCategory.companyId when it can be inferred from items.
    # Only sets when exactly one non-null companyId is used for that category.
    category_company_rows = (
        InventoryItem.objects.filter(category__isnull=False, companyId__isnull=False)
        .values_list("category_id", "companyId_id")
        .distinct()
    )

    category_to_company = {}
    for category_id, company_id in category_company_rows.iterator(chunk_size=2000):
        seen = category_to_company.get(category_id)
        if seen is None:
            category_to_company[category_id] = {company_id}
        else:
            if len(seen) < 2:
                seen.add(company_id)

    for category_id, company_ids in category_to_company.items():
        if len(company_ids) == 1:
            (company_id,) = tuple(company_ids)
            InventoryCategory.objects.filter(
                id=category_id, companyId__isnull=True
            ).update(companyId_id=company_id)


def backwards(apps, schema_editor):
    # Non-destructive backfill; no automatic rollback.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0008_inventory_scoping_fields"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
