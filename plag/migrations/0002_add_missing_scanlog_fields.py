# plag/migrations/000X_add_missing_scanlog_fields.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.migrations import RunPython
import django.db.models.fields.json

class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('plag', '0001_initial'), # IMPORTANT: Confirm this is your last successful plag migration
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Use RunPython.noop for all fields that now exist in the DB.
        migrations.RunPython(RunPython.noop, RunPython.noop), # For ai_probability_score
        migrations.RunPython(RunPython.noop, RunPython.noop), # For burstiness_score
        migrations.RunPython(RunPython.noop, RunPython.noop), # For top_words
        migrations.RunPython(RunPython.noop, RunPython.noop), # For text_snippet
        migrations.RunPython(RunPython.noop, RunPython.noop), # For document_name
        migrations.RunPython(RunPython.noop, RunPython.noop), # For uploaded_file
        migrations.RunPython(RunPython.noop, RunPython.noop), # For user (which is user_id) <-- NEW ADDITION

        # Add only the fields that are STILL missing.
        # Based on your previous errors, 'ai_label' should be the only remaining AddField.
        migrations.AddField(
            model_name='scanlog',
            name='ai_label',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        # If 'fail_type' was also missing from your DB but present in your model:
        # migrations.AddField(
        #     model_name='scanlog',
        #     name='fail_type',
        #     field=models.CharField(blank=True, choices=[('H', 'HTTP error'), ('C', 'No content candidates found (initial scan) or matched (post processing)'), ('E', 'Internal processing error'), ('I', 'Skipped/Ignored')], max_length=1, null=True),
        # ),
    ]