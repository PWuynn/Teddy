from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models.functions import ExtractMonth
from collections import Counter
import json
from .forms import ProfileForm
from accounts.models import CustomUser
from classroom.models import Classroom
from courses.models import Course
from materials.models import Document
from quiz.models import Quiz
from todo.models import PersonalTodo, Todo


User = get_user_model()


def _dashboard_for(user):
    if user.is_superuser or user.role == 'admin':
        return 'accounts:admin_dashboard'
    if user.role == 'teacher':
        return 'accounts:tea_dashboard'
    return 'accounts:stu_dashboard'


def _admin_totals():
    total_quizzes = Quiz.objects.count()
    return {
        'total_users': User.objects.count(),
        'total_teachers': User.objects.filter(role='teacher').count(),
        'total_students': User.objects.filter(role='student').count(),
        'total_courses': Course.objects.count(),
        'total_classes': Classroom.objects.count(),
        'total_documents': Document.objects.count(),
        'total_quizzes': total_quizzes,
        'total_quiz': total_quizzes,
        'total_todos': Todo.objects.count() + PersonalTodo.objects.count(),
    }


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(
            request,
            username=username,
            password=password
        )
        if user is not None:
            login(request, user)
            return redirect(_dashboard_for(user))

        messages.error(request, 'Sai tài khoản hoặc mật khẩu')

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


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

        messages.error(request, 'Mật khẩu không khớp')

    return render(request, 'accounts/register.html')


@login_required
def login_required_view(request):
    return render(request, 'accounts/login_required.html')


@staff_member_required
def admin_dashboard(request):
    totals = _admin_totals()
    total_admins = (
        User.objects.filter(role='admin').count()
        + User.objects.filter(is_superuser=True).exclude(role='admin').count()
    )

    latest_users = CustomUser.objects.order_by('-date_joined')[:5]
    latest_courses = Course.objects.select_related('creator').order_by('-created_at')[:5]
    latest_quizzes = Quiz.objects.select_related('created_by').order_by('-created_at')[:5]
    latest_documents = Document.objects.select_related('owner').order_by('-created_at')[:5]

    month_data = (
        CustomUser.objects
        .annotate(month=ExtractMonth('date_joined'))
        .values('month')
    )
    counter = Counter()
    for item in month_data:
        counter[item['month']] += 1

    month_labels = [
        'T1', 'T2', 'T3', 'T4', 'T5', 'T6',
        'T7', 'T8', 'T9', 'T10', 'T11', 'T12',
    ]
    month_values = [counter.get(i, 0) for i in range(1, 13)]

    context = {
        **totals,
        'latest_users': latest_users,
        'latest_courses': latest_courses,
        'latest_quizzes': latest_quizzes,
        'latest_documents': latest_documents,
        'month_labels': json.dumps(month_labels),
        'month_values': json.dumps(month_values),
        'role_labels': json.dumps(['Giáo viên', 'Học sinh', 'Quản trị'], ensure_ascii=False),
        'role_values': json.dumps([
            totals['total_teachers'],
            totals['total_students'],
            total_admins,
        ]),
    }
    return render(request, 'accounts/admin_dashboard/admin_dashboard.html', context)


@staff_member_required
def admin_latest_courses(request):
    courses = Course.objects.select_related('creator').order_by('-created_at')
    return render(request, 'accounts/admin_dashboard/latest_items.html', {
        **_admin_totals(),
        'latest_type': 'courses',
        'page_title': 'Khóa học mới',
        'page_subtitle': 'Danh sách khóa học được tạo gần đây nhất trong hệ thống.',
        'items': courses,
    })


@staff_member_required
def admin_latest_quizzes(request):
    quizzes = Quiz.objects.select_related('created_by', 'classroom').order_by('-created_at')
    return render(request, 'accounts/admin_dashboard/latest_items.html', {
        **_admin_totals(),
        'latest_type': 'quizzes',
        'page_title': 'Quiz mới',
        'page_subtitle': 'Danh sách quiz được tạo gần đây nhất trong hệ thống.',
        'items': quizzes,
    })


@staff_member_required
def admin_latest_documents(request):
    documents = Document.objects.select_related('owner', 'classroom').order_by('-created_at')
    return render(request, 'accounts/admin_dashboard/latest_items.html', {
        **_admin_totals(),
        'latest_type': 'documents',
        'page_title': 'Tài liệu mới',
        'page_subtitle': 'Danh sách tài liệu được đăng gần đây nhất trong hệ thống.',
        'items': documents,
    })


@staff_member_required
def admin_delete_latest_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete()
        messages.success(request, "Đã xóa khóa học.")
    return redirect('accounts:admin_latest_courses')


@staff_member_required
def admin_delete_latest_quiz(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, "Đã xóa quiz.")
    return redirect('accounts:admin_latest_quizzes')


@staff_member_required
def admin_delete_latest_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        document.delete()
        messages.success(request, "Đã xóa tài liệu.")
    return redirect('accounts:admin_latest_documents')

@login_required
def tea_dashboard(request):
    return render(request, 'accounts/teacher/tea_dashboard.html')


@login_required
def stu_dashboard(request):
    return render(request, 'accounts/student/stu_dashboard.html')


@login_required
def settings_view(request):
    return render(request, 'accounts/settings.html')


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Mật khẩu đã được cập nhật.')
            return redirect('accounts:settings')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def profile_view(request):
    editing = request.GET.get('edit') == '1'

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, 'Đã lưu hồ sơ.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    needs_required_info = not request.user.full_name or not request.user.email

    return render(request, 'accounts/profile.html', {
        'form': form,
        'editing': editing or needs_required_info,
        'needs_required_info': needs_required_info,
    })


@login_required
def user_list(request):
    users = CustomUser.objects.all()
    return render(request, 'accounts/user_list.html', {
        'users': users
    })

