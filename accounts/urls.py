from django.urls import path
from . import views

app_name = 'accounts'
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/change-password/', views.change_password_view, name='change_password'),
    path('login_required/', views.login_required_view, name='login_required'),

    path('student/', views.stu_dashboard, name='stu_dashboard'),
    path('teacher/', views.tea_dashboard, name='tea_dashboard'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/latest-courses/', views.admin_latest_courses, name='admin_latest_courses'),
    path('admin-dashboard/latest-quizzes/', views.admin_latest_quizzes, name='admin_latest_quizzes'),
    path('admin-dashboard/latest-documents/', views.admin_latest_documents, name='admin_latest_documents'),
    path('admin-dashboard/latest-courses/<int:pk>/delete/', views.admin_delete_latest_course, name='admin_delete_latest_course'),
    path('admin-dashboard/latest-quizzes/<int:pk>/delete/', views.admin_delete_latest_quiz, name='admin_delete_latest_quiz'),
    path('admin-dashboard/latest-documents/<int:pk>/delete/', views.admin_delete_latest_document, name='admin_delete_latest_document'),

    path('users/', views.user_list, name='user_list'),
]