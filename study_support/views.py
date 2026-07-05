from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from classroom.models import Classroom, ClassroomMember
from courses.models import Course
from materials.models import Document
from quiz_ai.models import Quiz
from todo.models import Todo


def home(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.role == 'admin':
            return render(request, 'accounts/admin_dashboard/admin_dashboard.html')
        if request.user.role == 'teacher':
            return render(request, 'accounts/teacher/tea_dashboard.html')
        return render(request, 'accounts/student/stu_dashboard.html')

    return render(request, 'home/index.html')


@login_required
def assistant_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    question = request.POST.get('message', '').strip()

    if not question:
        return JsonResponse({
            'answer': 'Bạn nhập câu hỏi hoặc từ khóa cần tìm nhé.',
            'items': []
        })

    course_matches = Course.objects.filter(
        Q(name__icontains=question) |
        Q(description__icontains=question) |
        Q(course_code__icontains=question) |
        Q(creator__username__icontains=question)
    ).select_related('creator')[:5]

    classroom_matches = Classroom.objects.filter(
        Q(name__icontains=question) |
        Q(description__icontains=question) |
        Q(class_code__icontains=question) |
        Q(teacher__username__icontains=question) |
        Q(course__name__icontains=question)
    ).select_related('teacher', 'course')[:5]

    document_matches = Document.objects.filter(
        Q(title__icontains=question) |
        Q(description__icontains=question) |
        Q(subject__icontains=question) |
        Q(classroom__name__icontains=question)
    ).select_related('classroom', 'owner')[:5]

    quiz_matches = Quiz.objects.filter(
        Q(title__icontains=question) |
        Q(description__icontains=question) |
        Q(classroom__name__icontains=question)
    ).select_related('classroom', 'created_by')[:5]

    todo_matches = Todo.objects.filter(
        Q(title__icontains=question) |
        Q(description__icontains=question) |
        Q(classroom__name__icontains=question),
        Q(user=request.user) | Q(assigned_by=request.user)
    ).select_related('classroom', 'user')[:5]

    items = []

    for course in course_matches:
        items.append({
            'type': 'Khóa học',
            'title': course.name,
            'description': f'Mã {course.course_code} · tạo bởi {course.creator.username}',
            'url': reverse('courses:course_detail', args=[course.id]),
        })

    for classroom in classroom_matches:
        items.append({
            'type': 'Lớp học',
            'title': classroom.name,
            'description': f'Mã {classroom.class_code} · giáo viên {classroom.teacher.username}',
            'url': reverse('classroom:class_detail', args=[classroom.id]),
        })

    for document in document_matches:
        target_url = document.file.url if document.file else reverse('materials:document_list')
        items.append({
            'type': 'Tài liệu',
            'title': document.title,
            'description': f'{document.subject} · tải bởi {document.owner.username}',
            'url': target_url,
        })

    for quiz in quiz_matches:
        if quiz.classroom_id and not (
            quiz.created_by == request.user or ClassroomMember.objects.filter(
                classroom=quiz.classroom,
                student=request.user
            ).exists()
        ):
            continue

        items.append({
            'type': 'Quiz',
            'title': quiz.title,
            'description': f'{quiz.time_limit} phút · tạo bởi {quiz.created_by.username}',
            'url': reverse('quiz_ai:quiz_detail', args=[quiz.id]),
        })

    for todo in todo_matches:
        items.append({
            'type': 'Todo',
            'title': todo.title,
            'description': f'Giao cho {todo.user.username} · hạn {todo.deadline:%d/%m/%Y %H:%M}' if todo.deadline else f'Giao cho {todo.user.username}',
            'url': reverse('classroom:class_detail', args=[todo.classroom_id]) if todo.classroom_id else reverse('todo:todo_list'),
        })

    lower_question = question.lower()
    if any(word in lower_question for word in ['lớp', 'lop', 'classroom']):
        hint = 'Mình đã tìm trong tên lớp, mã lớp, giáo viên và khóa học liên quan.'
    elif any(word in lower_question for word in ['khóa', 'khoa', 'course']):
        hint = 'Mình đã tìm trong tên khóa học, mô tả, mã khóa và người tạo.'
    elif any(word in lower_question for word in ['tài liệu', 'tai lieu', 'document']):
        hint = 'Mình đã tìm trong kho tài liệu và tài liệu gắn với lớp học.'
    elif any(word in lower_question for word in ['quiz', 'kiểm tra', 'kiem tra', 'trắc nghiệm', 'trac nghiem']):
        hint = 'Mình đã tìm trong các bài kiểm tra bạn có quyền xem.'
    else:
        hint = 'Mình đã tìm trên khóa học, lớp học, tài liệu, quiz và todo liên quan.'

    if items:
        answer = f'Tìm thấy {len(items)} kết quả phù hợp. {hint}'
    else:
        answer = 'Mình chưa thấy kết quả khớp. Bạn thử nhập tên khóa học, mã lớp, tên tài liệu hoặc tên bài kiểm tra cụ thể hơn nhé.'

    return JsonResponse({
        'answer': answer,
        'items': items[:10],
    })


