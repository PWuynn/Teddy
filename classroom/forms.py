from django import forms
from classroom.models import Classroom


class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = [
            'name',
            'description',
            'max_members',
            'join_permission',
        ]