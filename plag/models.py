import os
import random
import string

from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import JSONField

''' Not moved over (yet):
indextrial - will need
'''


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    student_id = models.CharField(max_length=20, blank=True, null=True)
    staff_id = models.CharField(max_length=20, blank=True, null=True)
    full_name = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username
    

class Order(models.Model):
    GBP = 'GBP'
    EUR = 'EUR'
    USD = 'USD'
    CURRENCIES = (
        (GBP, 'GBP'),
        (EUR, 'EUR'),
        (USD, 'USD'),
    )

    # A user can have multiple orders, if they've amended their order (since we close the old one)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    renewal_day = models.PositiveSmallIntegerField(default=1)
    price = models.DecimalField(max_digits=9, decimal_places=2)  # 9, 2 = N,NNN,NNN.DD
    currency = models.CharField(max_length=3,
                                 choices=CURRENCIES,
                                 default=USD)
    is_active = models.BooleanField(default=True)
    time_order_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id) + ': ' + str(self.price) + ' ' + self.currency


class ProtectedResource(models.Model):
    # Handling choices below due to http://www.b-list.org/weblog/2007/nov/02/handle-choices-right-way/
    URL = 'URL'
    PDF = 'PDF'
    DOC = 'DOC'
    DOCX = 'DOCX'
    PPTX = 'PPTX'
    TXT = 'TXT'
    RESOURCE_TYPES = (
        (URL, 'Website address'),
        (PDF, 'PDF file'),
        (DOC, 'Word document, old format'),
        (DOCX, 'Word document, new format'),
        (PPTX, 'Powerpoint presentation'),
        (TXT, 'Standard text file'),
    )

    A = 'A'
    N = 'N'
    S = 'S'
    F = 'F'
    P = 'P'
    O = 'O'
    I = 'I'
    STATUS_TYPES = (
        (A, 'Active'),
        (N, 'Newly placed order'),
        (S, 'Being scanned'),
        (F, 'Last scan failed'),
        (P, 'Awaiting payment'),
        (I, 'Inactive'),
    )

    DAILY = 86400
    WEEKLY = 604800
    MONTHLY = 2592000
    SCAN_FREQUENCY = (
        (DAILY, 'Daily'),
        (WEEKLY, 'Weekly'),
        (MONTHLY, 'Monthly'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    url = models.CharField(max_length=2048, blank=True)
    file = models.FileField(upload_to='userfiles/%Y/%m/%d', blank=True)
    type = models.CharField(max_length=4, choices=RESOURCE_TYPES, default=URL)
    status = models.CharField(max_length=1, choices=STATUS_TYPES, default=A)
    scan_frequency = models.PositiveIntegerField(choices=SCAN_FREQUENCY,
                                                 default=WEEKLY)
    next_scan = models.DateTimeField()
    original_filename = models.CharField(max_length=260, null=True, blank=True)  # If type not URL

    def __str__(self):
        return str(self.id) + ': ' + self.type

    def extension(self):
        name, extension = os.path.splitext(self.file.name)
        return extension

    def clean(self):
        # Either URL or File must be entered
        if self.url is None and self.file is None:
            raise ValidationError('URL or file required')


class Invoice(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=9, decimal_places=2)  # 9, 2 = N,NNN,NNN.DD
    explanation = models.CharField(max_length=1000, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    paid = models.DateTimeField(null=True, blank=True)
    is_adjustment = models.BooleanField(default=False)
    # max length is 17: https://developer.paypal.com/docs/classic/api/merchant/TransactionSearch_API_Operation_NVP/
    paypal_tid = models.CharField(max_length=17, null=True, blank=True)

    def __str__(self):
        return str(self.id) + ': ' + str(self.price)


class Query(models.Model):
    query = models.CharField(max_length=250)

    def __str__(self):
        return str(self.id) + ': ' + self.query


class ScanLog(models.Model):
    H = 'H'
    C = 'C'
    E = 'E'
    I = 'I'

    FAILED_TYPE = (
        (H, 'HTTP error'),
        (C, 'No content candidates found (initial scan) or matched (post processing)'),
        (E, 'Internal processing error'),
        (I, 'Skipped/Ignored'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scan_logs', null=True, blank=True) 

    timestamp = models.DateTimeField(auto_now_add=True)
    protected_resource = models.ForeignKey(ProtectedResource, null=True, blank=True, on_delete=models.SET_NULL)
    protected_source = models.TextField(null=True, blank=True)  # the text (source) of the protected resource
    queries = models.ManyToManyField(Query, blank=True) # This links the *entire set of queries* for a scan log
    scoring_debug = models.TextField(null=True, blank=True)
    fail_reason = models.CharField(max_length=500, null=True, blank=True)
    fail_type = models.CharField(max_length=1, choices=FAILED_TYPE, null=True, blank=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True)

    average_plagiarism_percent = models.FloatField(
        null=True, blank=True, 
        help_text='Average plagiarism percentage for documents with multiple sources, excluding false positives.'
    )
    average_calculated_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Timestamp when the average plagiarism percentage was last calculated.'
    )
    
    overall_plagiarism_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Overall percentage of the document found to be plagiarized across all sources."
    )
    overall_calculated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp when the overall plagiarism percentage was last calculated."
    )

    # --- New fields to add for the student dashboard and detailed report display ---
    document_name = models.CharField(max_length=255, default='Unnamed Document') # Store the original document name
    uploaded_file = models.FileField(upload_to='scanned_documents/', null=True, blank=True) # Optional: if you want to store the original file

    ai_probability_score = models.FloatField(null=True, blank=True) # Essential for AI score display
    ai_label = models.CharField(max_length=50, null=True, blank=True)
    burstiness_score = models.FloatField(null=True, blank=True)     # Essential for burstiness score display
    text_snippet = models.TextField(null=True, blank=True)          # Essential for the 'Analyzed Text Sample' display
    top_words = JSONField(null=True, blank=True)

    def __str__(self):
        # Adjusted __str__ for clarity on dashboard/report
        doc_name = self.document_name if self.document_name else "Unnamed Document"
        return f"Scan {self.id}: {doc_name} by {self.user.username if self.user else 'N/A'} on {self.timestamp.strftime('%Y-%m-%d')}"


class ScanResult(models.Model):
    result_log = models.ForeignKey(ScanLog, on_delete=models.CASCADE)
    query = models.ForeignKey(Query, related_name='scan_results', on_delete=models.CASCADE)

    timestamp = models.DateTimeField(auto_now_add=True)
    match_url = models.CharField(max_length=2048)
    match_display_url = models.CharField(max_length=2048)
    match_title = models.CharField(max_length=100)
    match_desc = models.CharField(max_length=500)
    post_scanned = models.BooleanField(default=False)
    post_fail_reason = models.CharField(max_length=500, null=True, blank=True)
    post_fail_type = models.CharField(max_length=1, choices=ScanLog.FAILED_TYPE, null=True, blank=True)
    perc_of_duplication = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # NNN.DD%

    def __str__(self):
        return f"Result {self.id} for Scan {self.result_log.id}: {self.perc_of_duplication}% on {self.timestamp.strftime('%Y-%m-%d')}"


class RecentBlogPosts(models.Model):
    title = models.CharField(max_length=200)
    link = models.CharField(max_length=2048)
    desc = models.TextField(null=True, blank=True)
    date = models.DateTimeField()


class UserPreference(models.Model):
    EMAIL_FREQ_INSTANT = 'I'
    EMAIL_FREQ_DAILY = 'D'
    EMAIL_FREQ_WEEKLY = 'W'
    EMAIL_FREQ_MONTHLY = 'M'
    EMAIL_FREQ_NEVER = 'N'
    EMAIL_FREQ = (
        (EMAIL_FREQ_INSTANT, 'Instant'),
        (EMAIL_FREQ_DAILY, 'Daily'),
        (EMAIL_FREQ_WEEKLY, 'Weekly'),
        (EMAIL_FREQ_MONTHLY, 'Monthly'),
        (EMAIL_FREQ_NEVER, 'Never'),
    )

    PER_PAGE_RESULTS = (
        (5, 5),
        (10, 10),
        (15, 15),
        (20, 20),
        (25, 25),
        (30, 30),
        (50, 50),
        (75, 75),
        (100, 100),
        (150, 150),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    results_per_page = models.PositiveSmallIntegerField(choices=PER_PAGE_RESULTS, null=True, blank=True)
    email_frequency = models.CharField(max_length=1, choices=EMAIL_FREQ, null=True, blank=True)
    false_positive_prot = models.BooleanField(default=True)

    def __str__(self):
        return str(self.id)
    

class Classroom(models.Model):
    lecturer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='lecturer_classrooms',
        limit_choices_to={'is_lecturer': True}
    )
    name = models.CharField(max_length=100)
    group = models.CharField(max_length=20, blank=True)
    intake = models.CharField(max_length=20, blank=True)
    students = models.ManyToManyField(
        User,
        related_name='student_classrooms',
        blank=True,
        limit_choices_to={'is_student': True}
    )
    join_code = models.CharField(max_length=8, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = self.generate_join_code()
        super().save(*args, **kwargs)

    def generate_join_code(self):
        length = 6
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            if not Classroom.objects.filter(join_code=code).exists():
                return code

    def __str__(self):
        return self.name
    

class Task(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.classroom.name}"

class Submission(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'is_student': True}
    )
    report_file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    similarity_score = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.task.title}"
