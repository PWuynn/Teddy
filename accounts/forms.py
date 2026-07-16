from django import forms
from django.contrib.auth import get_user_model


User = get_user_model()


class LoginForm(forms.Form):

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Nh?p t?n t?i kho?n'
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Nh?p m?t kh?u'
            }
        )
    )


class ProfileForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            'avatar',
            'full_name',
            'birth_date',
            'school',
            'phone',
            'email',
            'bio',
        ]
        labels = {
            'avatar': 'Ảnh đại diện',
            'full_name': 'Họ tên',
            'birth_date': 'Ngày tháng năm sinh',
            'school': 'Trường',
            'phone': 'Số điện thọai',
            'email': 'Email',
            'bio': 'Mô tả khác',
        }
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'school': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].required = True
        self.fields['email'].required = True
