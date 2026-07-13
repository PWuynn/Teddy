from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from classroom.models import Classroom, ClassroomMember
from materials.models import Document
from quiz_ai.models import Quiz, QuizResult
from todo.models import Todo
from .forms import ClassroomForm
import os
from zoneinfo import ZoneInfo
from django.conf import settings
from django.core.files.storage import FileSystemStorage


def _teacher_required(request, classroom):
    return classroom.teacher == request.user


def _approved_member_required(request, classroom):
    return classroom.teacher == request.user or ClassroomMember.objects.filter(
        classroom=classroom,
        student=request.user,
        status='approved'
    ).exists()


def _build_assignment_groups(assignments):
    grouped = {}

    for assignment in assignments:
        key = (
            assignment.title,
            assignment.description or '',
            assignment.deadline,
            assignment.priority,
            assignment.assigned_by_id,
        )

        if key not in grouped:
            grouped[key] = {
                'title': assignment.title,
                'description': assignment.description,
                'deadline': assignment.deadline,
                'priority': assignment.priority,
                'assigned_by': assignment.assigned_by,
                'items': [],
                'submitted': [],
                'pending': [],
                'is_late': bool(assignment.deadline and timezone.now() > assignment.deadline),
                'representative_id': assignment.id,
            }

        group = grouped[key]
        group['items'].append(assignment)

        if assignment.submission_text.strip() or assignment.submission_file:
            group['submitted'].append(assignment)
        else:
            group['pending'].append(assignment)

    return list(grouped.values())


@login_required
def class_detail(request, pk):
    classroom = get_object_or_404(
        Classroom.objects.select_related('teacher', 'course'),
        pk=pk
    )

    is_teacher = classroom.teacher == request.user
    is_member = ClassroomMember.objects.filter(
        classroom=classroom,
        student=request.user,
        status='approved'
    ).exists()
    pending_membership = ClassroomMember.objects.filter(
        classroom=classroom,
        student=request.user,
        status='pending'
    ).first()

    if not is_teacher and not is_member and not pending_membership:
        messages.warning(request, "Bạn cần tham gia lớp trước khi xem nội dung.")
        return redirect('classroom:join_classroom', pk=classroom.pk)

    can_interact = is_teacher or is_member

    members = ClassroomMember.objects.filter(
        classroom=classroom,
        status='approved'
    ).select_related('student').order_by('student__username')
    pending_members = ClassroomMember.objects.filter(
        classroom=classroom,
        status='pending'
    ).select_related('student').order_by('joined_at')

    documents = Document.objects.filter(
        classroom=classroom
    ).select_related('owner').order_by('-created_at')

    if is_teacher:
        assignments = Todo.objects.filter(
            classroom=classroom
        ).select_related('user', 'assigned_by').order_by('-created_at', 'deadline', 'user__username')
    else:
        assignments = Todo.objects.filter(
            classroom=classroom,
            user=request.user
        ).select_related('user', 'assigned_by').order_by('-created_at', 'deadline')

    assignment_groups = _build_assignment_groups(assignments)

    quizzes = Quiz.objects.filter(
        classroom=classroom
    ).select_related('created_by').prefetch_related('questions').order_by('-created_at')

    return render(request, 'classroom/class_detail.html', {
        'classroom': classroom,
        'members': members,
        'pending_members': pending_members,
        'documents': documents,
        'assignments': assignments,
        'assignment_groups': assignment_groups,
        'quizzes': quizzes,
        'is_teacher': is_teacher,
        'is_member': is_member,
        'pending_membership': pending_membership,
        'can_interact': can_interact,
    })


@login_required
def classroom_list(request):
    keyword = request.GET.get('q', '').strip()
    classrooms = Classroom.objects.select_related('teacher', 'course').all()

    if keyword:
        classrooms = classrooms.filter(
            Q(name__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(class_code__icontains=keyword) |
            Q(teacher__username__icontains=keyword) |
            Q(course__name__icontains=keyword)
        ).distinct()

    return render(request, 'classroom/classroom_list.html', {
        'classrooms': classrooms,
        'keyword': keyword,
    })


@login_required
def create_classroom(request):
    if request.method == 'POST':
        form = ClassroomForm(request.POST)

        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.teacher = request.user
            classroom.save()
            return redirect('classroom:classroom_list')
    else:
        form = ClassroomForm()

    return render(request, 'classroom/create_classroom.html', {
        'form': form
    })


@login_required
def edit_classroom(request, pk):
    classroom = get_object_or_404(Classroom, id=pk, teacher=request.user)

    if request.method == "POST":
        classroom.name = request.POST.get("name")
        classroom.description = request.POST.get("description")
        classroom.save()
        return redirect("classroom:class_detail", pk=pk)

    return render(request, "classroom/edit.html", {
        "classroom": classroom
    })


@login_required
def join_classroom(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)

    if request.method == "POST":
        membership = ClassroomMember.objects.filter(
            classroom=classroom,
            student=request.user
        ).first()

        if membership and membership.status == 'approved':
            messages.warning(request, "Bạn đã tham gia lớp này rồi.")
        elif membership and membership.status == 'pending':
            messages.info(request, "Yêu cầu tham gia lớp đang chờ giáo viên duyệt.")
            return redirect('classroom:class_detail', pk=classroom.pk)
        elif classroom.members.filter(status='approved').count() >= classroom.max_members:
            messages.error(request, "Lớp học đã đủ số lượng thành viên.")
        else:
            status = 'approved' if classroom.join_permission == 'free' else 'pending'

            if membership and membership.status == 'rejected':
                membership.status = status
                membership.reviewed_at = None
                membership.reviewed_by = None
                membership.save()
            else:
                membership = ClassroomMember.objects.create(
                    classroom=classroom,
                    student=request.user,
                    status=status
                )

            if status == 'approved':
                classroom.students.add(request.user)
                messages.success(request, "Tham gia lớp học thành công.")
                return redirect('classroom:class_detail', pk=classroom.pk)

            messages.info(request, "Đã gửi yêu cầu tham gia. Vui lòng chờ giáo viên duyệt.")
            return redirect('classroom:class_detail', pk=classroom.pk)

        return redirect('classroom:class_detail', pk=classroom.pk)

    return render(request, 'classroom/join_classroom.html', {
        'classroom': classroom
    })


@login_required
def upload_class_document(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)

    if request.method != 'POST':
        return redirect('classroom:class_detail', pk=classroom.pk)

    if not _approved_member_required(request, classroom):
        return HttpResponseForbidden("Ban can duoc chap nhan vao lop truoc khi tai tai lieu.")

    uploaded_file = request.FILES.get('file')

    if not uploaded_file:
        messages.error(request, "Vui long chon tep tai lieu.")
        return redirect('classroom:class_detail', pk=classroom.pk)

    Document.objects.create(
        owner=request.user,
        classroom=classroom,
        title=request.POST.get('title') or uploaded_file.name,
        description=request.POST.get('description', ''),
        level=request.POST.get('level') or 'THPT',
        subject=request.POST.get('subject') or classroom.name,
        permission=request.POST.get('permission') or 'download',
        file=uploaded_file
    )

    messages.success(request, "Da tai tai lieu len lop.")
    return redirect('classroom:class_detail', pk=classroom.pk)


@login_required
def assign_class_todo(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)

    if request.method != 'POST':
        return redirect('classroom:class_detail', pk=classroom.pk)

    if not _teacher_required(request, classroom):
        return HttpResponseForbidden("Ban khong co quyen giao bai trong lop nay.")

    assign_scope = request.POST.get('assign_scope', 'all')
    selected_ids = request.POST.getlist('student_ids')
    members_query = ClassroomMember.objects.filter(
        classroom=classroom,
        status='approved'
    ).select_related('student')

    if assign_scope == 'selected':
        if not selected_ids:
            messages.warning(request, "Vui long chon it nhat mot thanh vien de giao bai.")
            return redirect('classroom:class_detail', pk=classroom.pk)

        members_query = members_query.filter(student_id__in=selected_ids)

    member_users = [member.student for member in members_query]

    if not member_users:
        messages.warning(request, "Lop chua co hoc sinh/sinh vien de giao bai.")
        return redirect('classroom:class_detail', pk=classroom.pk)

    deadline = parse_datetime(request.POST.get('deadline', ''))
    if deadline and timezone.is_naive(deadline):
        deadline = timezone.make_aware(deadline, timezone.get_current_timezone())

    for student in member_users:
        Todo.objects.create(
            user=student,
            assigned_by=request.user,
            classroom=classroom,
            role='student',
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            priority=request.POST.get('priority') or 'medium',
            deadline=deadline,
        )
    
    messages.success(request, f"Da giao bai cho {len(member_users)} thanh vien.")
    return redirect('classroom:class_detail', pk=classroom.pk)


@login_required
def edit_class_todo_group(request, todo_id):
    todo = get_object_or_404(
        Todo.objects.select_related('classroom', 'assigned_by'),
        id=todo_id
    )
    classroom = todo.classroom

    if not _teacher_required(request, classroom):
        return HttpResponseForbidden("Ban khong co quyen chinh sua bai duoc giao trong lop nay.")

    group = Todo.objects.filter(
        classroom=classroom,
        assigned_by=todo.assigned_by,
        title=todo.title,
        description=todo.description,
        deadline=todo.deadline,
        priority=todo.priority,
    )
    members = ClassroomMember.objects.filter(
        classroom=classroom,
        status='approved'
    ).select_related('student').order_by('student__username')

    if request.method == 'POST':
        selected_ids = {int(value) for value in request.POST.getlist('student_ids') if value.isdigit()}
        if not selected_ids:
            messages.warning(request, "Vui long chon it nhat mot thanh vien.")
            return redirect('classroom:edit_class_todo_group', todo_id=todo.id)

        deadline = parse_datetime(request.POST.get('deadline', ''))
        if deadline and timezone.is_naive(deadline):
            deadline = timezone.make_aware(deadline, timezone.get_current_timezone())

        title = request.POST.get('title', '').strip()
        if not title:
            messages.warning(request, "Tieu de bai giao khong duoc de trong.")
            return redirect('classroom:edit_class_todo_group', todo_id=todo.id)

        allowed_ids = {member.student_id for member in members}
        selected_ids &= allowed_ids
        if not selected_ids:
            messages.warning(request, "Thanh vien duoc chon khong hop le.")
            return redirect('classroom:edit_class_todo_group', todo_id=todo.id)

        existing = {item.user_id: item for item in group}
        group.exclude(user_id__in=selected_ids).delete()
        group.filter(user_id__in=selected_ids).update(
            title=title,
            description=request.POST.get('description', '').strip(),
            priority=request.POST.get('priority') or 'medium',
            deadline=deadline,
        )
        for user_id in selected_ids - set(existing):
            Todo.objects.create(
                user_id=user_id, assigned_by=request.user, classroom=classroom,
                role='student', title=title,
                description=request.POST.get('description', '').strip(),
                priority=request.POST.get('priority') or 'medium', deadline=deadline,
            )

        messages.success(request, "Da cap nhat bai duoc giao.")
        return redirect('classroom:class_detail', pk=classroom.pk)

    return render(request, 'classroom/edit_assignment.html', {
        'classroom': classroom, 'assignment': todo, 'members': members,
        'selected_member_ids': set(group.values_list('user_id', flat=True)),
    })

@login_required
def delete_class_todo_group(request, todo_id):
    todo = get_object_or_404(
        Todo.objects.select_related('classroom', 'assigned_by'),
        id=todo_id
    )
    classroom = todo.classroom

    if request.method != 'POST':
        return redirect('classroom:class_detail', pk=classroom.pk)

    if todo.assigned_by != request.user:
        return HttpResponseForbidden("Bạn chỉ có thể xóa bài do mình giao.")

    if not todo.deadline or timezone.now() <= todo.deadline:
        messages.warning(request, "Chỉ có thể xóa bài giao đã quá hạn.")
        return redirect('classroom:class_detail', pk=classroom.pk)

    deleted_count, _ = Todo.objects.filter(
        classroom=classroom,
        assigned_by=request.user,
        title=todo.title,
        description=todo.description,
        deadline=todo.deadline,
        priority=todo.priority,
    ).delete()

    messages.success(request, f"Đã xóa {deleted_count} bài giao quá hạn.")
    return redirect('classroom:class_detail', pk=classroom.pk)


@login_required
def review_classroom_member(request, pk, member_id, action):
    classroom = get_object_or_404(Classroom, pk=pk)

    if classroom.teacher != request.user:
        return HttpResponseForbidden("Ban khong co quyen duyet thanh vien lop nay.")

    membership = get_object_or_404(
        ClassroomMember,
        pk=member_id,
        classroom=classroom,
        status='pending'
    )

    if request.method == 'POST':
        if action == 'approve':
            membership.status = 'approved'
            classroom.students.add(membership.student)
            messages.success(request, f"Đã chấp nhận {membership.student.username}.")
        elif action == 'reject':
            membership.status = 'rejected'
            classroom.students.remove(membership.student)
            messages.warning(request, f"Đã từ chối {membership.student.username}.")
        else:
            return HttpResponseForbidden("Hành động không hợp lệ.")

        membership.reviewed_at = timezone.now()
        membership.reviewed_by = request.user
        membership.save()

    return redirect('classroom:class_detail', pk=classroom.pk)

@login_required
def remove_classroom_member(
    request,
    pk,
    member_id
):
    classroom = get_object_or_404(
        Classroom,
        pk=pk
    )

    if not request.user.is_admin and classroom.teacher != request.user:
        return HttpResponseForbidden("Bạn không có quyền quản lý lớp này.")

    membership = get_object_or_404(
        ClassroomMember,
        pk=member_id,
        classroom=classroom
    )

    if request.method == "POST":

        classroom.students.remove(
            membership.student
        )

        membership.delete()

        messages.success(
            request,
            f"Đã xóa {membership.student.username} khỏi lớp học."
        )

    return redirect(
        "classroom:class_detail",
        pk=pk
    )
@login_required
def create_class_quiz(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)

    if request.method != 'POST':
        return redirect('classroom:class_detail', pk=classroom.pk)

    if not _teacher_required(request, classroom):
        return HttpResponseForbidden("Ban khong co quyen tao bai kiem tra trong lop nay.")

    quiz = Quiz.objects.create(
        title=request.POST.get('title'),
        description=request.POST.get('description', ''),
        created_by=request.user,
        classroom=classroom,
        max_attempts=request.POST.get('max_attempts') or None,
        time_limit=request.POST.get('time_limit') or 30,
    )

    messages.success(request, "Da tao bai kiem tra. Hay them cau hoi trac nghiem.")
    return redirect('quiz_ai:add_question', quiz_id=quiz.id)

@login_required
def submit_todo_file(request, todo_id):
    todo = get_object_or_404(
        Todo,
        id=todo_id,
        user=request.user
    )

    if request.method != "POST":
        return redirect(
            "classroom:class_detail",
            pk=todo.classroom.id
        )

    if not _approved_member_required(request, todo.classroom):
        return HttpResponseForbidden("Ban can duoc chap nhan vao lop truoc khi nop bai.")

    if todo.deadline and timezone.now() > todo.deadline:
        messages.error(request, "Bai da qua han, ban khong the nop bai.")
        return redirect(
            "classroom:class_detail",
            pk=todo.classroom.id
        )

    uploaded_file = request.FILES.get("submission_file")

    if not uploaded_file:
        messages.error(request, "Vui lòng chọn file.")
        return redirect(
            "classroom:class_detail",
            pk=todo.classroom.id
        )

    todo.submission_file = uploaded_file
    todo.completed = True
    todo.save()

    messages.success(
        request,
        "Nộp bài thành công."
    )

    return redirect(
        "classroom:class_detail",
        pk=todo.classroom.id
    )
@login_required
def delete_class_quiz_result(request, pk, result_id):
    classroom = get_object_or_404(Classroom, pk=pk)
    if not _teacher_required(request, classroom):
        return HttpResponseForbidden("Ban khong co quyen xoa lich su lam bai cua lop nay.")

    result = get_object_or_404(
        QuizResult.objects.select_related('quiz'),
        id=result_id,
        quiz__classroom=classroom,
    )
    if request.method == 'POST':
        result.delete()
        messages.success(request, "Da xoa lich su lam bai.")
    return redirect('classroom:class_detail', pk=classroom.pk)

@login_required
def class_quiz_history_json(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)

    if not _teacher_required(request, classroom):
        return HttpResponseForbidden("Ban khong co quyen xem lich su lop nay.")

    results = QuizResult.objects.filter(
        quiz__classroom=classroom
    ).select_related('user', 'quiz').order_by('-created_at')[:30]

    return JsonResponse({
        'results': [
            {
                'student': result.user.username,
                'quiz': result.quiz.title,
                'score': result.score,
                'created_at': timezone.localtime(result.created_at, ZoneInfo('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M'),
                'delete_url': reverse('classroom:delete_class_quiz_result', args=[classroom.pk, result.id]),
            }
            for result in results
        ]
    })
