# plag/migrations/000X_add_missing_scanlog_fields.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.migrations import RunPython # Make sure RunPython is imported
import django.db.models.fields.json # Make sure this is imported for JSONField

class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('plag', '0001_initial'), # <--- IMPORTANT: Confirm this is your last successful plag migration
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Use RunPython.noop for ai_probability_score, burstiness_score, AND top_words
        # because they now exist in the DB.
        migrations.RunPython(RunPython.noop, RunPython.noop), # For ai_probability_score
        migrations.RunPython(RunPython.noop, RunPython.noop), # For burstiness_score
        migrations.RunPython(RunPython.noop, RunPython.noop), # For top_words

        # Add only the fields that are STILL missing (if any)
        migrations.AddField(
            model_name='scanlog',
            name='ai_label',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='scanlog',
            name='text_snippet',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='scanlog',
            name='document_name',
            field=models.CharField(default='Unnamed Document', max_length=255),
        ),
        migrations.AddField(
            model_name='scanlog',
            name='uploaded_file',
            field=models.FileField(blank=True, null=True, upload_to='scanned_documents/'),
        ),
        migrations.AddField(
            model_name='scanlog',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        # If 'fail_type' was also missing from your DB but present in your model:
        # migrations.AddField(
        #     model_name='scanlog',
        #     name='fail_type',
        #     field=models.CharField(blank=True, choices=[('H', 'HTTP error'), ('C', 'No content candidates found (initial scan) or matched (post processing)'), ('E', 'Internal processing error'), ('I', 'Skipped/Ignored')], max_length=1, null=True),
        # ),
    ]