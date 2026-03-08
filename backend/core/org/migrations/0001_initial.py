import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrgUnit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=100)),
                ("node_type", models.CharField(default="org", max_length=100)),
                (
                    "isolation_policy",
                    models.CharField(
                        choices=[("open", "Open"), ("isolated", "Isolated"), ("inherit_only", "Inherit Only"), ("visible_only", "Visible Only")],
                        default="open", max_length=20,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                        related_name="children", to="org.orgunit",
                    ),
                ),
            ],
            options={"app_label": "org", "db_table": "org_units"},
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "role",
                    models.CharField(
                        choices=[("owner", "Owner"), ("admin", "Admin"), ("member", "Member"), ("viewer", "Viewer")],
                        default="member", max_length=20,
                    ),
                ),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to=settings.AUTH_USER_MODEL)),
                ("org_unit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="org.orgunit")),
            ],
            options={
                "app_label": "org",
                "db_table": "memberships",
                "constraints": [models.UniqueConstraint(fields=("user", "org_unit"), name="unique_user_org_unit")],
            },
        ),
        migrations.CreateModel(
            name="APIKey",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("prefix", models.CharField(db_index=True, max_length=8)),
                ("hashed_key", models.CharField(max_length=64)),
                (
                    "role",
                    models.CharField(
                        choices=[("owner", "Owner"), ("admin", "Admin"), ("member", "Member"), ("viewer", "Viewer")],
                        default="member", max_length=20,
                    ),
                ),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_api_keys", to=settings.AUTH_USER_MODEL)),
                ("org_unit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="api_keys", to="org.orgunit")),
            ],
            options={
                "app_label": "org",
                "db_table": "api_keys",
                "constraints": [models.UniqueConstraint(fields=("prefix", "hashed_key"), name="unique_api_key")],
            },
        ),
    ]
