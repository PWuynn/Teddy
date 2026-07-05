from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ProfileForm

User = get_user_model()

def _dashboard_for(user):
    if user.is_superuser or user.role == 'admin':
        return 'accounts:admin_dashboard'
    if user.role == 'teacher':
        return 'accounts:tea_dashboard'
    return 'accounts:stu_dashboard'


# LOGIN
def login_view(request):
    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(
            request,
            username=username,
            password=password
        )
        if user is not None:

            login(request, user)

            return redirect(_dashboard_for(user))

        else:
            messages.error(request, "Sai tài khoản hoặc mật khẩu")

    return render(request, 'accounts/login.html')

# LOGOUT
def logout_view(request):

    logout(request)

    return redirect('home')


# REGISTER
def register_view(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        email = request.POST.get('email')
        role = request.POST.get('role')

        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 == password2:
            if role not in {'student', 'teacher'}:
                role = 'student'

            user = User.objects.create_user(
                username=username,
                email=email,
                full_name=username,
                role=role,
                password=password1
            )

            user.save()

            return redirect('accounts:login')

        else:
            messages.error(request, "Mật khẩu không khớp")

    return render(request, 'accounts/register.html')


@login_required
def login_required_view(request):

    return render(request, 'accounts/login_required.html')


@login_required
def admin_dashboard(request):

    return render(request, 'accounts/admin_dashboard/admin_dashboard.html')


@login_required
def tea_dashboard(request):

    return render(request, 'accounts/teacher/tea_dashboard.html')


@login_required
def stu_dashboard(request):

    return render(request, 'accounts/student/stu_dashboard.html')


@login_required
def profile_view(request):
    editing = request.GET.get('edit') == '1'

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Đã lưu hồ sơ.")
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    needs_required_info = not request.user.full_name or not request.user.email

    return render(request, 'accounts/profile.html', {
        'form': form,
        'editing': editing or needs_required_info,
        'needs_required_info': needs_required_info,
    })



