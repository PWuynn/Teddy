from django.urls import path
from . import views

app_name = 'quiz_ai'
urlpatterns = [
    path('create_quiz/', views.create_quiz, name='create_quiz'),
    path('quizzes/', views.quiz_list, name='quiz_list'),
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('quiz/<int:quiz_id>/take/',views.take_quiz,name='take_quiz'),
    path('quiz/<int:quiz_id>/flashcards/', views.flashcards, name='flashcards'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('quiz/<int:quiz_id>/delete/',views.delete_quiz,name='delete_quiz'),
    path('history/', views.quiz_history, name='quiz_history'),
    path('result/<int:result_id>/delete/',views.delete_result,name='delete_result'),
    path('quiz/<int:quiz_id>/add-question/', views.add_question, name='add_question'),
    path('question/<int:question_id>/edit/',views.edit_question,name='edit_question'),
    path('question/<int:question_id>/delete/',views.delete_question,name='delete_question'),
]   
