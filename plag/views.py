from datetime import datetime, timedelta
from io import BytesIO
import json
import urllib.parse
import logging
import os.path
from zipfile import ZipFile

from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from django.core.files import File
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.views.generic import View, TemplateView
from django.views.decorators.csrf import csrf_protect
from django.utils.timezone import utc
from django.utils import timezone
from plag import const
from plag.forms import AddStudentForm, ClassroomForm, TaskForm, UserInfoForm, PasswordChangeForm, UserPreferencesForm, UserCreationForm
from plag.models import Order, ProtectedResource, Invoice, ScanResult, ScanLog, Query, Submission, Task, UserProfile, Classroom
from plag.services import AccountHomepage, AccountPlagiarismScans, ProtectedResourcesOrder, get_user_preferences, \
    get_scan_frequencies_for_order, process_homepage_trial, post_process_index_trial

logger = logging.getLogger(__name__)


class HomepageView(TemplateView):
    template_name = 'plag/static/homepage.html'


def register(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        student_id = request.POST.get('student_id')
        staff_id = request.POST.get('staff_id')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        username = email  # or generate one from name/id

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('register')

        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password1)
            profile = UserProfile.objects.create(
                user=user,
                role=role,
                full_name=full_name,
                student_id=student_id if role == 'student' else '',
                staff_id=staff_id if role == 'lecturer' else ''
            )
            messages.success(request, "Account created! You can now log in.")
            return redirect('login')

    return render(request, 'plag/static/register.html')


def custom_login(request):
    if request.method == 'POST':
        input_id = request.POST.get('username')
        password = request.POST.get('password')

        try:
            # Try to find a user by student ID or staff ID
            profile = UserProfile.objects.get(student_id=input_id)
        except UserProfile.DoesNotExist:
            try:
                profile = UserProfile.objects.get(staff_id=input_id)
            except UserProfile.DoesNotExist:
                profile = None

        if profile:
            user = authenticate(request, username=profile.user.username, password=password)
            if user is not None:
                login(request, user)
                role = profile.role
                if role == 'student':
                    return redirect('index')
                elif role == 'lecturer':
                    return redirect('lecturer_dashboard')
                else:
                    return redirect('index')
        
        messages.error(request, "Invalid username or password.")
        return redirect('login')

    return render(request, 'plag/static/login.html')


def custom_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('login')


@login_required
def student_dashboard(request):
    classrooms = request.user.student_classrooms.all()
    return render(request, 'plag/static/index.html', {'classrooms': classrooms})


# --- New View: Student Dashboard (lists past scans) ---
@login_required
def student_dashboard_view(request):
    # Fetch all scan logs for the current user, ordered by most recent
    # Ensure 'user' field is present in ScanLog for this to work
    recent_scans = ScanLog.objects.filter(user=request.user).order_by('-timestamp')[:5] # Order by your existing 'timestamp' field

    # Pass the user's UserProfile object to the template
    student_profile = request.user.userprofile if hasattr(request.user, 'userprofile') else None

    context = {
        'recent_scans': recent_scans,
        'student': student_profile,
        'user': request.user,
    }
    return render(request, 'plag/static/index.html', context) # Render your existing index.html as the dashboard


# --- New View: View Specific Past Scan (re-displays index_trial.html with saved data) ---
@login_required
def view_specific_scan(request, scan_id):
    # Fetch the specific ScanLog and its associated ScanResults
    # Ensure 'user' field in ScanLog is used for security
    scan_log = get_object_or_404(ScanLog, id=scan_id, user=request.user)
    # Use result_log for the related name
    scan_results = scan_log.scanresult_set.all().order_by('-perc_of_duplication') # Order by your existing field

    # Pass the user's UserProfile object to the template
    student_profile = request.user.userprofile if hasattr(request.user, 'userprofile') else None

    context = {
        'scan_log': scan_log,
        'scan_results': scan_results,
        'ai_probability_score': scan_log.ai_probability_score,
        'burstiness_score': scan_log.burstiness_score,
        'top_words': scan_log.top_words,
        'text_snippet': scan_log.text_snippet,
        'student': student_profile,
    }
    return render(request, 'plag/index_trial.html', context) # Render index_trial.html with pre-loaded data



@login_required
def student_classroom_detail(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)
    
    if not request.user.student_classrooms.filter(id=classroom_id).exists():
        messages.error(request, "You don't have access to this classroom")
        return redirect('index')
    
    # Change this line to use Task instead of Assignment
    tasks = classroom.tasks.all().order_by('-created_at')
    
    return render(request, 'plag/static/student_classroom_detail.html', {
        'classroom': classroom,
        'tasks': tasks
    })


@login_required
def join_classroom(request):
    
    if request.method == 'POST':
        join_code = request.POST.get('join_code')
        try:
            classroom = Classroom.objects.get(join_code=join_code)
            if classroom.students.filter(id=request.user.id).exists():
                messages.info(request, f'You have already joined {classroom.name}.')
            else:
                classroom.students.add(request.user)
                messages.success(request, f'Successfully joined {classroom.name}!')
            return redirect('index')
        except Classroom.DoesNotExist:
            messages.error(request, 'Invalid join code.')
            return redirect('index')
    
    return redirect('index')  # fallback


@login_required
def leave_classroom(request, classroom_id, student_id):

    classroom = get_object_or_404(Classroom, id=classroom_id)
    student = get_object_or_404(User, id=student_id, userprofile__role='student')
    
    if request.method == 'POST':
        Submission.objects.filter(student=student, task__classroom=classroom).delete()
        classroom.students.remove(request.user)
        messages.success(request, f'You have left {classroom.name}.')
        return redirect('index')

    return redirect('index')


@login_required
def lecturer_dashboard(request):
    classrooms = Classroom.objects.filter(lecturer=request.user)
    return render(request, 'plag/static/lecturer_module.html', {'classrooms': classrooms})


@login_required
def recent_scans(request, num_days=30, hide_zero='', template='plag/dynamic/recent_scans.html'):
    ctx = {}

    if int(num_days) < 1 or int(num_days) > 30:
        num_days = 30

    ctx.update(
        {'results': AccountPlagiarismScans.get_recent_finds(request.user.id, num_days, True if hide_zero else False)})
    ctx.update({'num_days': num_days})
    ctx.update({'hide_zero': hide_zero})

    return render(request, template, ctx)


@login_required
def scan_history(request, hide_zero='', template='plag/dynamic/scan_history.html'):
    ctx = {}

    finds = AccountPlagiarismScans.get_historical_finds(request.user.id, True if hide_zero else False)

    user_pref = get_user_preferences(request.user)
    if user_pref and user_pref.results_per_page:
        results_per_page = user_pref.results_per_page
    else:
        results_per_page = const.RESULTS_PER_PAGE

    # https://docs.djangoproject.com/en/1.7/topics/pagination/
    paginator = Paginator(finds, results_per_page)

    page = request.GET.get('page')
    try:
        results = paginator.page(page)
    except PageNotAnInteger:
        results = paginator.page(1)
    except EmptyPage:
        results = paginator.page(paginator.num_pages)

    ctx.update({'results': results})
    ctx.update({'hide_zero': hide_zero})

    return render(request, template, ctx)


@login_required
def download_file(request, prot_res_id):
    prot_res = ProtectedResource.objects.filter(id=prot_res_id, order__user=request.user)

    if prot_res:
        filename = prot_res[0].file.name.split('/')[-1]
        response = HttpResponse(prot_res[0].file, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename=%s' % filename

        return response


def sitemap_to_urls(request):
    return_data = ProtectedResourcesOrder.get_urls_from_sitemap(request.GET.get('sitemap_url'))
    return HttpResponse(json.dumps(return_data), content_type="application/json")


@login_required
# TODO This excludes ones which haven't been post scanned. But the overall count does not. Also this doesn't look at false positives
def plagiarism_results(request, scan_id=-1):
    scan_results = ScanResult.objects.filter(result_log=scan_id,
                                             result_log__protected_resource__order__user=request.user,
                                             post_scanned=True)

    return_data = []
    for result in scan_results:
        return_data.append({
            'match_url': result.match_url,
            'match_display_url': result.match_display_url,
            'match_title': result.match_title,
            'match_desc': result.match_desc,
            'perc_of_duplication': str(result.perc_of_duplication),
        })

    return HttpResponse(json.dumps(return_data), content_type="application/json")


class ProfileView(View):
    template = 'plag/dynamic/profile.html'

    def get(self, request, *args, **kwargs):
        ctx = {
            'form': UserInfoForm(instance=request.user),
            'pref_form': UserPreferencesForm(instance=get_user_preferences(request.user)),
            'pass_form': PasswordChangeForm(user=request.user),
        }

        return render(request, self.template, ctx)

    def post(self, request, *args, **kwargs):
        f = UserInfoForm(request.POST, instance=request.user)
        pref = UserPreferencesForm(request.POST, instance=get_user_preferences(request.user))
        passwd = None
        valid = f.is_valid() and pref.is_valid()

        if "changing_password" in request.POST:
            passwd = PasswordChangeForm(user=request.user, data=request.POST)

            if passwd.is_valid():
                new_password = passwd.cleaned_data['new_password']
                # Bind the password change to the main form change. If there's an error there, don't change the password
                f.instance.set_password(new_password)
            else:
                valid = False

        if valid:
            pref.save()
            f.save()
            messages.success(request, 'Account information updated')
            return redirect('profile')
        else:
            ctx = {
                'form': f,
                'pref_form': pref,
                'pass_form': passwd if passwd else PasswordChangeForm(user=request.user),
            }
            return render(request, self.template, ctx)


# TODO The 'go back' icon for an existing resource doesn't reset the form
class ProtectedResources(View):
    template = 'plag/dynamic/protected_resource.html'

    def get(self, request, *args, **kwargs):
        ctx = {
            'prot_res': ProtectedResourcesOrder.get_prot_res(request.user),
            'scan_frequencies': ProtectedResource.SCAN_FREQUENCY,
            'accepted_file_exts': const.ACCEPTED_FILE_EXTENSIONS,
            'order': Order.objects.filter(user=request.user, is_active=True)[0],
            'numDaily': 0,
            'numWeekly': 0,
            'numMonthly': 0,
        }

        scan_freqs = get_scan_frequencies_for_order(request.user)
        for freq in scan_freqs:
            if freq['scan_frequency'] == ProtectedResource.DAILY:
                ctx.update({'numDaily': freq['dcount']})
            elif freq['scan_frequency'] == ProtectedResource.WEEKLY:
                ctx.update({'numWeekly': freq['dcount']})
            elif freq['scan_frequency'] == ProtectedResource.MONTHLY:
                ctx.update({'numMonthly': freq['dcount']})

        return render(request, self.template, ctx)

    def post(self, request, *args, **kwargs):
        redirect_loc, param = ProtectedResourcesOrder.handle_amended_order(request)
        if param:
            return redirect(redirect_loc, pk=param)
        else:
            return redirect(redirect_loc)


class OrderView(View):
    template = 'plag/dynamic/order.html'

    def get(self, request, *args, **kwargs):
        ctx = {
            'scan_frequencies': ProtectedResource.SCAN_FREQUENCY,
            'accepted_file_exts': const.ACCEPTED_FILE_EXTENSIONS,
            'user_form': UserCreationForm,
        }

        return render(request, self.template, ctx)

    def post(self, request, *args, **kwargs):
        redirect_loc, param = ProtectedResourcesOrder.handle_new_order(request)
        if param:
            return redirect(redirect_loc, pk=param)
        else:
            return redirect(redirect_loc)


class IndexTrialView(View):
    template = 'plag/static/index_trial.html'

    def get(self, request, *args, **kwargs):
        scan_log_id = request.GET.get('id1')
        scan_result_id = request.GET.get('id2')

        perc_dup = -1
        overall_plagiarism_percentage = -1
        ai_score = None
        ai_label = None

        scan_log = None
        scan_result = None

        if scan_log_id:
            try:
                # Process the result
                scan_result = post_process_index_trial(request, scan_log_id, scan_result_id)
                if scan_result:
                    perc_dup = scan_result.perc_of_duplication

                scan_log = ScanLog.objects.get(id=scan_log_id)
                if scan_log.overall_plagiarism_percentage is not None:
                    overall_plagiarism_percentage = str(scan_log.overall_plagiarism_percentage)

                if scan_log.ai_score is not None:
                    ai_score = scan_log.ai_score
                if scan_log.ai_label:
                    ai_label = scan_log.ai_label

            except ScanLog.DoesNotExist:
                logger.warning(f"ScanLog with id {scan_log_id} not found.")
            except Exception as e:
                logger.error(f"Error in IndexTrialView GET: {e}")

        # If it's an AJAX call, return JSON
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return HttpResponse(json.dumps({
                'id': scan_result_id,
                'perc_dup': str(perc_dup),
                'overall_plagiarism_percentage': overall_plagiarism_percentage,
                'ai_score': ai_score,
                'ai_label': ai_label,
            }), content_type="application/json")

        # Otherwise render the page (useful for manual GET testing)
        context = {
            'scan_log': scan_log,
            'scan_results': [scan_result] if scan_result else [],
            'overall_plagiarism_percentage': overall_plagiarism_percentage,
            'ai_probability_score': ai_score * 100 if ai_score is not None else None,
            'analysis_message': f"AI Detection: {ai_label}" if ai_label else None,
            'student': request.user.userprofile,
        }
        return render(request, self.template, context)

    def post(self, request, *args, **kwargs):
        # Run plagiarism scan
        scan_log, scan_results, extracted_text = process_homepage_trial(request)

        ai_probability_score = None
        ai_label_from_winston = None # New variable to store the label from WinstonAI
        burstiness_score = None
        top_words = []
        analysis_message = None

        if extracted_text.strip():
            # AI detection
            from util.winston import get_winston_ai_prediction, calculate_burstiness, get_top_repeated_words

            # 🛑 FIX: Unpack the tuple returned by get_winston_ai_prediction
            ai_probability_score, ai_label_from_winston = get_winston_ai_prediction(extracted_text)

            burstiness_score = calculate_burstiness(extracted_text)
            top_words = get_top_repeated_words(extracted_text)

            if ai_probability_score is not None:
                # Ensure ai_probability_score is a float before comparison
                # Add a check to ensure it's indeed a number
                if isinstance(ai_probability_score, (int, float)):
                    if ai_probability_score > 0.5:
                        analysis_message = "Text Analysis Result: AI generated content (WinstonAI)"
                        scan_log.ai_label = "AI-generated"
                    else:
                        analysis_message = "Text Analysis Result: Likely human content (WinstonAI)"
                        scan_log.ai_label = "Human-written"
                    scan_log.ai_score = ai_probability_score
                else:
                    # Handle unexpected type from WinstonAI if it's not None but also not a number
                    logger.error(f"WinstonAI returned non-numeric score: {ai_probability_score}")
                    analysis_message = "WinstonAI returned an unreadable score."
                    scan_log.ai_label = "Error"
                    scan_log.ai_score = None # Reset to None if type is wrong
            else:
                # This branch is taken if get_winston_ai_prediction returned (None, None)
                analysis_message = "WinstonAI could not detect a valid result (API error or no response)."
                scan_log.ai_label = "API Error"
                scan_log.ai_score = None # Ensure score is None on error

            scan_log.save() # Save changes to the scan_log object

        context = {
            'scan_log': scan_log,
            'scan_results': scan_results,
            'ai_probability_score': ai_probability_score * 100 if ai_probability_score is not None else None,
            'burstiness_score': burstiness_score,
            'top_words': top_words,
            # Use ai_label_from_winston if it's the source for message, otherwise use scan_log.ai_label
            'analysis_message': analysis_message or f"AI Detection: {scan_log.ai_label}" if scan_log and scan_log.ai_label else None,
            'student': request.user.userprofile,
        }

        return render(request, self.template, context)


def username_unique(request):
    return_data = False

    username = request.GET.get("username")
    if username:
        user = User.objects.filter(username=username)
        if not user:
            return_data = True

    return HttpResponse(json.dumps(return_data), content_type="application/json")


def data_cleanse(request):
    user = User.objects.get(username='tristanperry')

    for order in Order.objects.all():
        order.delete()

    new_order = Order(user=user, renewal_day=1, price=19.45, currency=Order.USD, is_active=True,
                      time_order_added=timezone.now())
    new_order.save()

    for prot_res in ProtectedResource.objects.all():
        prot_res.delete()

    past_date = timezone.now() - timedelta(days=5)
    url1 = ProtectedResource(order=new_order, url='http://www.diveinto.org/python3/serializing.html',
                             type=ProtectedResource.URL, status=ProtectedResource.A,
                             scan_frequency=ProtectedResource.DAILY, next_scan=past_date)
    url1.save()

    url2 = ProtectedResource(order=new_order, url='http://www.pontypoolpodiatrychiropody.co.uk/',
                             type=ProtectedResource.URL, status=ProtectedResource.A,
                             scan_frequency=ProtectedResource.DAILY, next_scan=past_date)
    url2.save()

    sentiment_analysis = File(open(r'C:\PlagiarismGuard\mediaroottest\testfiles\Sentiment Analysis.pdf', mode='rb'))
    file1 = ProtectedResource(order=new_order, file=sentiment_analysis, type=ProtectedResource.PDF,
                              status=ProtectedResource.A, scan_frequency=ProtectedResource.DAILY,
                              next_scan=past_date, original_filename='Sentiment Analysis.pdf')
    file1.save()

    johnny_sell = File(open(r'C:\PlagiarismGuard\mediaroottest\testfiles\Why Johnny Cant Sell.PDF', mode='rb'))
    file2 = ProtectedResource(order=new_order, file=johnny_sell, type=ProtectedResource.PDF,
                              status=ProtectedResource.A, scan_frequency=ProtectedResource.DAILY,
                              next_scan=past_date, original_filename='Why Johnny Cant Sell.PDF')
    file2.save()

    random_docx = File(open(r'C:\PlagiarismGuard\mediaroottest\testfiles\Random Doc.docx', mode='rb'))
    file3 = ProtectedResource(order=new_order, file=random_docx, type=ProtectedResource.DOCX,
                              status=ProtectedResource.A, scan_frequency=ProtectedResource.DAILY,
                              next_scan=past_date, original_filename='Random Doc.docx')
    file3.save()

    intro_nlp = File(open(r'C:\PlagiarismGuard\mediaroottest\testfiles\Introduction to NLP.pptx', mode='rb'))
    file4 = ProtectedResource(order=new_order, file=intro_nlp, type=ProtectedResource.PPTX,
                              status=ProtectedResource.A, scan_frequency=ProtectedResource.DAILY,
                              next_scan=past_date, original_filename='Introduction to NLP.pptx')
    file4.save()

    cl_links = File(open(r'C:\PlagiarismGuard\mediaroottest\testfiles\ComputerLover links.txt', mode='r', encoding='utf-8'))
    file5 = ProtectedResource(order=new_order, file=cl_links, type=ProtectedResource.TXT,
                              status=ProtectedResource.A, scan_frequency=ProtectedResource.DAILY,
                              next_scan=past_date, original_filename='ComputerLover links.txt')
    file5.save()

    bronafon_pack = File(open(r'C:\PlagiarismGuard\mediaroottest\testfiles\BronAfonApplicationPack.doc', mode='rb'))
    file6 = ProtectedResource(order=new_order, file=bronafon_pack, type=ProtectedResource.DOC,
                              status=ProtectedResource.A, scan_frequency=ProtectedResource.DAILY,
                              next_scan=past_date, original_filename='BronAfonApplicationPack.doc')
    file6.save()

    for invoice in Invoice.objects.all():
        invoice.delete()

    invoice = Invoice(order=new_order, price=94815.12, explanation='This invoice is a rip off')
    invoice.save()

    for hist in ScanResult.objects.all():
        hist.delete()

    for log in ScanLog.objects.all():
        log.delete()

    for query in Query.objects.all():
        query.delete()

    return render(request, 'plag/dynamic/data_cleanse.html')


@login_required
def create_classroom(request):
    
    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.lecturer = request.user
            classroom.save()
            messages.success(request, 'Classroom created successfully!')
            return redirect('lecturer_dashboard')
    else:
        form = ClassroomForm()
    return render(request, 'plag/static/create_classroom.html', {'form': form})

@login_required
def lecturer_classroom_detail(request, classroom_id):

    classroom = get_object_or_404(Classroom, id=classroom_id, lecturer=request.user)
    tasks = classroom.tasks.all().order_by('-created_at')
    students = classroom.students.all()
    task_form = TaskForm()

    if request.method == 'POST':
        if 'add_student' in request.POST:
            student_form = AddStudentForm(request.POST, classroom=classroom)  # pass classroom here
            if student_form.is_valid():
                student = student_form.cleaned_data['student']
                classroom.students.add(student)
                messages.success(request, f'Student {student.userprofile.full_name} added successfully!')
                return redirect('lecturer_classroom_detail', classroom_id=classroom_id)
        elif 'create_task' in request.POST:
            if not request.POST.get('task_id'):
                task_form = TaskForm(request.POST)
                if task_form.is_valid():
                    task = task_form.save(commit=False)
                    task.classroom = classroom
                    task.save()
                    messages.success(request, 'Task created successfully!')
                    return redirect('lecturer_classroom_detail', classroom_id=classroom_id)
        else:
            student_form = AddStudentForm(classroom=classroom)  # pass classroom here too
            task_form = TaskForm()
    else:
        student_form = AddStudentForm(classroom=classroom)  # pass classroom here as well
        task_form = TaskForm()

    context = {
        'classroom': classroom,
        'student_form': student_form,
        'task_form': task_form,
        'tasks': tasks,
    }
    return render(request, 'plag/static/lecturer_classroom_detail.html', context)

@login_required
def download_submissions(request, task_id):
    """
    Allows a lecturer to download all submissions for a specific task
    as a single ZIP file.
    """
    # Ensure the task exists and belongs to the logged-in lecturer
    task = get_object_or_404(Task, id=task_id, classroom__lecturer=request.user)
    
    # Get all submissions related to this task
    submissions = task.submissions.all()
    
    # Create an in-memory byte buffer to store the zip file
    buffer = BytesIO()
    
    # Create a ZipFile object in write mode
    with ZipFile(buffer, 'w') as zip_file:
        for submission in submissions:
            # Check if a report file exists for the submission
            if submission.report_file:
                try:
                    # Open the file from the storage backend.
                    # This works for both local and cloud storage.
                    with submission.report_file.open('rb') as f: # 'rb' for read binary
                        # Get the original filename to use inside the zip
                        # os.path.basename is safe as it just extracts the name from the path string
                        file_name_in_zip = os.path.basename(submission.report_file.name)
                        
                        # Write the content of the file directly into the zip archive
                        zip_file.writestr(file_name_in_zip, f.read())
                except Exception as e:
                    # Log the error if a specific file cannot be opened/read
                    # You might want to use Django's logging system here
                    print(f"Error processing file {submission.report_file.name}: {e}")
                    # Optionally, you could add a placeholder file to the zip
                    # indicating which file failed, or just skip it.
                    zip_file.writestr(f"error_{os.path.basename(submission.report_file.name)}.txt", 
                                     f"Could not process this file: {e}")
    
    # After writing all files, seek back to the beginning of the buffer
    buffer.seek(0)
    
    # Create the HTTP response with the zip file content
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    
    # Set the Content-Disposition header to prompt download
    response['Content-Disposition'] = f'attachment; filename=submissions_task_{task_id}.zip'
    
    return response

# For final report submission
@login_required
def upload_report(request):
    
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        file = request.FILES.get('document')
        
        if file and task_id:
            try:
                task = Task.objects.get(id=task_id)
                # Delete previous submission if exists
                Submission.objects.filter(task=task, student=request.user).delete()
                
                submission = Submission(
                    task=task,
                    student=request.user,
                    report_file=file
                )
                submission.save()
                messages.success(request, 'Final report submitted successfully!')
                return redirect('student_classroom_detail', classroom_id=task.classroom.id)
            except Task.DoesNotExist:
                messages.error(request, 'Invalid task')
        else:
            messages.error(request, 'Please select a file to upload')
    
    return redirect('student_dashboard')

@login_required
def edit_classroom(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id, lecturer=request.user)

    if request.method == 'POST':
        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, 'Classroom updated successfully.')
        else:
            messages.error(request, 'Error updating classroom.')
    return redirect('lecturer_dashboard')


@login_required
def delete_classroom(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id, lecturer=request.user)

    if request.method == 'POST':
        classroom.delete()
        messages.success(request, 'Classroom deleted successfully.')
        return redirect('lecturer_dashboard')

    return redirect('lecturer_dashboard')

@login_required
def edit_task(request, classroom_id, task_id):

    classroom = get_object_or_404(Classroom, id=classroom_id, lecturer=request.user)
    task = get_object_or_404(Task, id=task_id, classroom=classroom)

    task_form = TaskForm(request.POST, instance=task)
    if task_form.is_valid():
        task_form.save()
        messages.success(request, 'Task updated successfully!')
    else:
        messages.error(request, 'Error updating task.')
    return redirect('lecturer_classroom_detail', classroom_id=classroom_id)

@login_required
def delete_task(request, task_id):

    task = get_object_or_404(Task, id=task_id, classroom__lecturer=request.user)
    classroom_id = task.classroom.id
    task.delete()
    messages.success(request, 'Task deleted successfully!')
    return redirect('lecturer_classroom_detail', classroom_id=classroom_id)

@login_required
def remove_student(request, classroom_id, student_id):

    classroom = get_object_or_404(Classroom, id=classroom_id, lecturer=request.user)
    student = get_object_or_404(User, id=student_id, userprofile__role='student')

    Submission.objects.filter(student=student, task__classroom=classroom).delete()
    classroom.students.remove(student)
    
    messages.success(request, f"Student {student.userprofile.full_name} removed from classroom.")
    return redirect('lecturer_classroom_detail', classroom_id=classroom_id)

@login_required
def view_task_detail(request, classroom_id, task_id):
    classroom = get_object_or_404(Classroom, id=classroom_id, lecturer=request.user)
    task = get_object_or_404(Task, id=task_id, classroom=classroom)
    students = classroom.students.all()

    # Map each student to their submission (if any)
    student_submissions = []
    submitted_count = 0  # Count how many students actually submitted

    for student in students:
        submission = Submission.objects.filter(task=task, student=student).first()
        is_submitted = bool(submission)
        if is_submitted:
            submitted_count += 1

        student_submissions.append({
            'student': student,
            'submitted': bool(submission),
            'submission': submission,
            'submission_date': submission.submitted_at if submission else None,
        })

    total_count = students.count()
    pending_count = total_count - submitted_count

    context = {
        'classroom': classroom,
        'task': task,
        'student_submissions': student_submissions,
        'submitted_count': submitted_count,
        'total_count': total_count,
        'pending_count': pending_count,
    }
    return render(request, 'plag/static/view_task_detail.html', context)
