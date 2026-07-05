from django.urls import path
from . import views

app_name = 'accounts'
urlpatterns = [

    path(
        'login/',
        views.login_view,
        name='login'
        
    ),

    path(
        'register/',
        views.register_view,
        name='register'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),
    path(
        'profile/',
        views.profile_view,
        name='profile'
    ),
      path(
        'login_required/',
        views.login_required_view,
        name='login_required'
    ),
    # Dashboard học sinh
    path(
        'student/',
        views.stu_dashboard,
        name='stu_dashboard'
    ),

    # Dashboard giáo viên
    path(
        'teacher/',
        views.tea_dashboard,
        name='tea_dashboard'
    ),

    # Dashboard admin
    path(
        'admin/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),

]
