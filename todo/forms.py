from django import forms
from .models import Todo

class TodoForm(forms.ModelForm):

    class Meta:
        model = Todo

        fields = [
            'title',
            'description',
            'priority',
            'deadline',
        ]

        widgets = {

            'priority': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            )
        }


class SubmitTodoForm(forms.ModelForm):

    class Meta:
        model = Todo

        fields = [
            'submission_text',
            'submission_file',
        ]