from django import forms
from .models import Document


class DocumentForm(forms.ModelForm):

    class Meta:
        model = Document

        fields = [
            'title',
            'description',
            'level',
            'subject',
            'file',
            'permission'
        ]

        widgets = {
            'description': forms.Textarea(
                attrs={'rows': 4}
            )
        }