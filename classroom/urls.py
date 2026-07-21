from django.urls import path
from . import views

app_name = 'classroom'

urlpatterns = [
    path('', views.classroom_list, name='classroom_list'),
    path('create/', views.create_classroom, name='create_classroom'),
    path('<int:pk>/', views.class_detail, name='class_detail'),
    path('join/<int:pk>/',views.join_classroom,name='join_classroom'),
    path('<int:pk>/documents/upload/', views.upload_class_document, name='upload_class_document'),
    path('<int:pk>/todos/assign/', views.assign_class_todo, name='assign_class_todo'),
    path('todo/<int:todo_id>/edit-group/', views.edit_class_todo_group, name='edit_class_todo_group'),
    path('todo/<int:todo_id>/delete-group/', views.delete_class_todo_group, name='delete_class_todo_group'),
    path('<int:pk>/members/<int:member_id>/<str:action>/', views.review_classroom_member, name='review_classroom_member'),
    path('<int:pk>/remove-member/<int:member_id>/',views.remove_classroom_member,name='remove_classroom_member'),
    path('<int:pk>/quizzes/create/', views.create_class_quiz, name='create_class_quiz'),
    path('todo/<int:todo_id>/submit/',views.submit_todo_file,name="submit_todo_file"),
    path('<int:pk>/quizzes/history/<int:result_id>/delete/', views.delete_class_quiz_result, name='delete_class_quiz_result'),
    path('<int:pk>/quizzes/history/reload/<int:penalty_id>/delete/', views.delete_class_quiz_reload_attempt, name='delete_class_quiz_reload_attempt'),
    path('<int:pk>/quizzes/history.json', views.class_quiz_history_json, name='class_quiz_history_json'),
]
