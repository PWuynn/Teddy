from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.courses_list, name='course_list'),
    path('create/', views.create_course, name='create_course'),
    path('join/', views.join_course, name='join_course'),
    path('<int:pk>/',views.course_detail,name='course_detail'),
    path('<int:pk>/members/<int:membership_id>/<str:action>/', views.review_course_member, name='review_course_member'),
    path('<int:pk>/edit/',views.edit_course,name='edit_course'),
    path('<int:pk>/delete/',views.delete_course,name='delete_course'),
]
