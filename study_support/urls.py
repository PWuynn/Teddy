from django.urls import path, include 
from . import views
from django.contrib import admin
from quiz_ai import views as quiz_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('assistant/chat/', views.assistant_chat, name='assistant_chat'),
    path('admin/', admin.site.urls),
    path('', include('quiz_ai.urls')),
    path('',include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('create_quiz/', quiz_views.create_quiz, name='create_quiz'),
    path('classroom/', include('classroom.urls')),
    path('courses/', include('courses.urls')),
    path('materials/', include('materials.urls')),
    path('todo/', include('todo.urls')),
]
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
