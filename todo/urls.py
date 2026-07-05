from django.urls import path
from . import views
app_name = 'todo'
urlpatterns = [
    path("", views.todo_list, name="todo_list"),
    path("teacher/", views.teacher_todo, name="teacher_todo_list"),
    path("student/", views.todo_list, name="student_todo"),
    path("create/", views.create_personal_todo, name="create_personal_todo"),
    path("<int:pk>/edit/", views.edit_personal_todo, name="edit_personal_todo"),
    path("<int:pk>/delete/", views.delete_personal_todo, name="delete_personal_todo"),
    path('submit/<int:pk>/', views.submit_todo, name='submit_todo'),
    path('submission/<int:pk>/file/', views.view_submission_file, name='view_submission_file'),
    path('toggle/<int:pk>/', views.toggle_todo, name='toggle_todo'),
    path('complete/<int:pk>/', views.complete_personal_todo, name='complete_personal_todo')
    
]   

