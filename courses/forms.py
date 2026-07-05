from django import forms
from .models import Course
from classroom.models import Classroom


class CourseForm(forms.ModelForm):

    class Meta:
        model = Course

        fields = [
            'name',
            'description',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tên khóa học'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Mô tả khóa học',
                'rows': 4
            }),
        }


class ClassroomForm(forms.ModelForm):

    class Meta:
        model = Classroom

        fields = [
            'name',
            'description',
            'max_members',
            'join_permission',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tên lớp'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),

            'max_members': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'course_code': forms.TextInput(
    attrs={
        'class': 'form-control',
        'placeholder': 'Để trống để tạo tự động'
    }
)
        }
def clean_course_code(self):
    code = self.cleaned_data.get('course_code')

    if not code:
        return code

    code = code.upper()

    if len(code) != 6:
        raise forms.ValidationError(
            "Mã khóa học phải gồm 6 ký tự."
        )

    if Course.objects.filter(course_code=code).exists():
        raise forms.ValidationError(
            "Mã khóa học đã tồn tại."
        )

    return code