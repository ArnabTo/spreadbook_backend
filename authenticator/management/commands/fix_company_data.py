from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Fix company_id foreign key constraint issues"

    def handle(self, *args, **options):
        self.stdout.write("Fixing company_id data...")

        with connection.cursor() as cursor:
            # Check current table structure
            cursor.execute("PRAGMA table_info(authenticator_user);")
            columns = [row[1] for row in cursor.fetchall()]
            self.stdout.write(f"Available columns: {columns}")

            # Check what company_id values exist
            if "company_id" in columns:
                cursor.execute(
                    "SELECT DISTINCT company_id FROM authenticator_user WHERE company_id IS NOT NULL;"
                )
                company_ids = cursor.fetchall()
                self.stdout.write(f"Current company_id values: {company_ids}")

                # Check what companies exist in company table
                cursor.execute("SELECT id, name FROM company_company;")
                companies = cursor.fetchall()
                self.stdout.write(f"Available companies: {companies}")

                # Fix the problematic user
                cursor.execute(
                    """
                    UPDATE authenticator_user 
                    SET company_id = NULL 
                    WHERE id = 2 AND company_id = 'Raktch Technology & Software';
                """
                )

                rows_updated = cursor.rowcount
                self.stdout.write(f"Updated {rows_updated} rows")

                # Check if there are other invalid company_id values
                cursor.execute(
                    """
                    SELECT id, username, company_id 
                    FROM authenticator_user 
                    WHERE company_id IS NOT NULL 
                    AND company_id NOT IN (
                        SELECT CAST(id AS TEXT) FROM company_company
                    );
                """
                )
                invalid_users = cursor.fetchall()

                if invalid_users:
                    self.stdout.write(
                        f"Found users with invalid company_id: {invalid_users}"
                    )

                    # Set all invalid company_id values to NULL
                    cursor.execute(
                        """
                        UPDATE authenticator_user 
                        SET company_id = NULL 
                        WHERE company_id IS NOT NULL 
                        AND company_id NOT IN (
                            SELECT CAST(id AS TEXT) FROM company_company
                        );
                    """
                    )

                    self.stdout.write(f"Set invalid company_id values to NULL")

                self.stdout.write(
                    self.style.SUCCESS("Successfully fixed company_id data")
                )
            else:
                self.stdout.write("company_id column not found")
