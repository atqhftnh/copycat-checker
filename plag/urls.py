from django.urls import path, re_path # <-- Replaced 'patterns' and 'url'
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import views as auth_views

from . import views 
from . import const 
from .views import (
    student_classroom_detail,
    lecturer_classroom_detail,
    join_classroom,
    create_classroom,
    download_submissions,
    upload_report,
    leave_classroom,
    student_dashboard_view, # New import for dashboard
    view_specific_scan,
)


urlpatterns = [ 
    # Home Page URLs
    path('index-trial/', views.IndexTrialView.as_view(), name='index_trial'),

    # Download URL (uses a named group, so re_path)
    re_path(r'^download/(?P<prot_res_id>\d+)$', views.download_file, name='download'),

    # Static Pages using TemplateView
    path('products/', TemplateView.as_view(template_name='plag/static/products.html'), name='products'),
    path('features-screenshots/', TemplateView.as_view(template_name='plag/static/features_and_screenshots.html'), name='features'),
    path('url-protection/', TemplateView.as_view(template_name='plag/static/url_protection.html'), name='url_prot'),
    path('document-protection/', TemplateView.as_view(template_name='plag/static/doc_protection.html'), name='doc_prot'),
    path('pricing/', TemplateView.as_view(template_name='plag/static/pricing.html'), name='pricing'),
    path('risks-of-plagiarism/', TemplateView.as_view(template_name='plag/static/risks_of_plagiarism.html'), name='risks_plag'),

    path('about-us/', TemplateView.as_view(template_name='plag/static/about.html'), name='about'),
    path('our-customers/', TemplateView.as_view(template_name='plag/static/our_customers.html'), name='our_customers'),
    path('contact-us/', TemplateView.as_view(template_name='plag/static/contact_us.html'), name='contact'),

    # Order and AJAX URLs
    path('order/', views.OrderView.as_view(), name='order'),
    path('ajax/username-check/', views.username_unique, name='ajax_username_unique'),

    # Account URLs
    path('account/profile/', login_required(views.ProfileView.as_view()), name='profile'),

    # Recent Scans URLs (use re_path for optional regex parts)
    path('account/recent-scans/', views.recent_scans, name='recent_scans_default'),
    re_path(r'^account/recent-scans/(?P<num_days>\d+)$', views.recent_scans, name='recent_scans'),
    re_path(r'^account/recent-scans/(?P<num_days>\d+)/(?P<hide_zero>hide-zero)$', views.recent_scans, name='recent_scans_hide_zero'),

    # Scan History URLs (use re_path for optional regex parts)
    path('account/scan-history/', views.scan_history, name='scan_history'),
    re_path(r'^account/scan-history/(?P<hide_zero>hide-zero)$', views.scan_history, name='scan_history_hide_zero'),

    # AJAX Plagiarism Results URLs (use re_path for optional regex parts)
    path('ajax/plag-results/', views.plagiarism_results, name='ajax_plag_results_default'),
    re_path(r'^ajax/plag-results/(?P<scan_id>\d+)$', views.plagiarism_results, name='plag_results'),

    path('ajax/sitemap/', views.sitemap_to_urls, name='ajax_urls'),

    path('account/protected-resources/', login_required(views.ProtectedResources.as_view()), name='protected_resources'),

    # More Static Pages
    path('sitemap/', TemplateView.as_view(template_name='plag/static/sitemap.html'), name='sitemap'),
    path('terms-of-service/', TemplateView.as_view(template_name='plag/static/terms_of_service.html'), name='terms_of_service'),
    path('privacy-policy/', TemplateView.as_view(template_name='plag/static/privacy_policy.html'), name='privacy_policy'),

    # TODO Remove (if it's truly a TODO to remove, leave it for now)
    path('data-cleanse/', views.data_cleanse, name='data_cleanse'),

    path('copyright/', TemplateView.as_view(template_name='plag/static/copyright.html'), name='copyright'),

    path('', views.HomepageView.as_view(), name='homepage'),

    path('login/', views.custom_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.custom_logout, name='logout'),

    # Student URLs
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/scan/<int:scan_id>/', view_specific_scan, name='view_specific_scan'),
    path('student/classroom/<int:classroom_id>/', student_classroom_detail, name='student_classroom_detail'),
    path('student/join/', views.join_classroom, name='join_classroom'),
    #path('join_classroom/', join_classroom, name='join_classroom'),
    path('leave-classroom/<int:classroom_id>/', views.leave_classroom, name='leave_classroom'),
    path('upload-report/', upload_report, name='upload_report'),

    # Lecturer URLs
    path('lecturer/dashboard/', views.lecturer_dashboard, name='lecturer_dashboard'),
    path('lecturer/create_classroom/', create_classroom, name='create_classroom'),
    path('lecturer/classroom/<int:classroom_id>/', lecturer_classroom_detail, name='lecturer_classroom_detail'),
    path('lecturer/tasks/<int:task_id>/download/', download_submissions, name='download_submissions'),
    path('lecturer/classroom/<int:classroom_id>/edit/', views.edit_classroom, name='edit_classroom'),
    path('lecturer/classroom/<int:classroom_id>/delete/', views.delete_classroom, name='delete_classroom'),
    path('classroom/<int:classroom_id>/remove_student/<int:student_id>/', views.remove_student, name='remove_student'),
    path('lecturer/classroom/<int:classroom_id>/edit_task/<int:task_id>/', views.edit_task, name='edit_task'),
    path('lecturer/delete_task/<int:task_id>/', views.delete_task, name='delete_task'),
    path('lecturer/classroom/<int:classroom_id>/remove_student/<int:student_id>/', views.remove_student, name='remove_student'),
    path('lecturer/classroom/<int:classroom_id>/task/<int:task_id>/', views.view_task_detail, name='view_task_detail'),

    # Reset Password URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='plag/static/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='plag/static/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='plag/static/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='plag/static/password_reset_complete.html'), name='password_reset_complete'),
]