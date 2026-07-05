from django import forms
from .models import Quiz


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'description','max_attempts']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập tên đề kiểm tra'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Mô tả đề kiểm tra'
            })
        }


class ManualQuestionForm(forms.Form):
    content = forms.CharField(
        label='Nội dung câu hỏi',
        widget=forms.Textarea(attrs={
            'class': 'form-control mb-3',
            'rows': 3,
            'placeholder': 'Ví dụ: Python là gì?'
        })
    )

    answers = forms.CharField(
        label='Các đáp án',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Mỗi đáp án 1 dòng\n*Python là ngôn ngữ lập trình\nJava là hệ điều hành\nHTML là database'
        }),
        help_text='Đặt dấu * trước đáp án đúng'
    )