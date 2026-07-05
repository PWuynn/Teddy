import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "study_support.settings")
django.setup()

from django.apps import apps

for app in apps.get_app_configs():
    print(app.label)
    for model in app.get_models():
        print("   -", model.__name__)