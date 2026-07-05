import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from classroom.models import Classroom
from .models import Course, CourseMember


def _filter_courses(queryset, keyword):
    if not keyword:
        return queryset

    return queryset.filter(
        Q(name__icontains=keyword) |
        Q(description__icontains=keyword) |
        Q(course_code__icontains=keyword) |
        Q(creator__username__icontains=keyword) |
        Q(classes__name__icontains=keyword) |
        Q(classes__class_code__icontains=keyword)
    ).distinct()


def _attach_membership_state(courses, user):
    for course in courses:
        course.classroom_count = course.classes.count()
        course.user_membership = CourseMember.objects.filter(
            course=course,
            user=user
        ).first()
    return courses


@login_required
def create_course(request):
    if request.method == 'POST':
        course = Course.objects.create(
            creator=request.user,
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            join_permission=request.POST.get('join_permission') or 'public',
        )

        class_names = request.POST.getlist('class_name[]')
        max_students = request.POST.getlist('max_students[]')

        for index, class_name in enumerate(class_names):
            class_name = class_name.strip()
            if not class_name:
                continue

            Classroom.objects.create(
                course=course,
                name=class_name,
                description='',
                teacher=request.user,
                class_code=uuid.uuid4().hex[:6].upper(),
                max_members=max_students[index] if index < len(max_students) and max_students[index] else 50
            )

        course.total_classes = course.classes.count()
        course.save(update_fields=['total_classes'])
        messages.success(request, "Da tao khoa hoc.")
        return redirect('courses:course_detail', pk=course.pk)

    return render(request, 'courses/create_course.html')


@login_required
def courses_list(request):
    keyword = request.GET.get('q', '').strip()
    courses = _filter_courses(Course.objects.select_related('creator').all(), keyword)
    courses = _attach_membership_state(courses, request.user)

    return render(request, 'courses/courses_list.html', {
        'courses': courses,
        'keyword': keyword,
    })


@login_required
def course_detail(request, pk):
    course = get_object_or_404(
        Course.objects.select_related('creator'),
        pk=pk
    )

    keyword = request.GET.get('q', '').strip()
    classrooms = course.classes.select_related('teacher').all()

    if keyword:
        classrooms = classrooms.filter(
            Q(name__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(class_code__icontains=keyword) |
            Q(teacher__username__icontains=keyword)
        ).distinct()

    membership = CourseMember.objects.filter(
        course=course,
        user=request.user
    ).first()

    pending_memberships = CourseMember.objects.none()
    if request.user == course.creator:
        pending_memberships = CourseMember.objects.filter(
            course=course,
            status='pending'
        ).select_related('user')

    can_interact = request.user == course.creator or (
        membership is not None and membership.status == 'approved'
    )

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'classrooms': classrooms,
        'keyword': keyword,
        'membership': membership,
        'can_interact': can_interact,
        'pending_memberships': pending_memberships,
        'approved_count': CourseMember.objects.filter(course=course, status='approved').count(),
    })


@login_required
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if request.user != course.creator:
        return redirect('courses:course_detail', pk=course.pk)

    course.delete()
    return redirect('courses:course_list')


@login_required
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if request.user != course.creator:
        return HttpResponseForbidden("Ban khong co quyen chinh sua khoa hoc nay.")

    if request.method == 'POST':
        course.name = request.POST.get('name', course.name).strip()
        course.description = request.POST.get('description', '')
        course.join_permission = request.POST.get('join_permission', course.join_permission)
        course.save()

        class_ids = request.POST.getlist('class_id[]')
        class_names = request.POST.getlist('class_name[]')
        max_students = request.POST.getlist('max_students[]')

        for index, class_name in enumerate(class_names):
            class_name = class_name.strip()
            if not class_name:
                continue

            max_members = max_students[index] if index < len(max_students) and max_students[index] else 50
            class_id = class_ids[index] if index < len(class_ids) else ''

            if class_id:
                Classroom.objects.filter(
                    id=class_id,
                    course=course
                ).update(
                    name=class_name,
                    max_members=max_members
                )
            else:
                Classroom.objects.create(
                    course=course,
                    name=class_name,
                    description='',
                    teacher=request.user,
                    class_code=uuid.uuid4().hex[:6].upper(),
                    max_members=max_members
                )

        course.total_classes = course.classes.count()
        course.save(update_fields=['total_classes'])
        messages.success(request, "Da cap nhat khoa hoc va giu lai du lieu lop cu.")
        return redirect('courses:course_detail', pk=course.pk)

    return render(request, 'courses/edit_course.html', {
        'course': course,
        'classrooms': course.classes.all()
    })


@login_required
def join_course(request):
    if request.method == 'POST':
        code = request.POST.get('course_code')

        try:
            course = Course.objects.get(course_code=code)

            if course.creator == request.user:
                messages.info(request, "Ban la nguoi tao khoa hoc nay.")
                return redirect('courses:course_detail', pk=course.pk)

            membership, created = CourseMember.objects.get_or_create(
                course=course,
                user=request.user,
                defaults={
                    'status': 'approved' if course.join_permission == 'public' else 'pending'
                }
            )

            if not created and membership.status == 'rejected':
                membership.status = 'pending' if course.join_permission == 'approval' else 'approved'
                membership.reviewed_at = None
                membership.reviewed_by = None
                membership.save()

            if membership.status == 'approved':
                messages.success(request, f'Da tham gia khoa hoc {course.name}.')
            elif membership.status == 'pending':
                messages.info(request, f'Yeu cau tham gia {course.name} dang cho nguoi tao duyet.')
            else:
                messages.warning(request, f'Yeu cau tham gia {course.name} da bi tu choi.')

            return redirect('courses:course_detail', pk=course.pk)

        except Course.DoesNotExist:
            messages.error(request, 'Ma khoa hoc khong ton tai.')

    return render(request, 'courses/join_course.html')


@login_required
def review_course_member(request, pk, membership_id, action):
    course = get_object_or_404(Course, pk=pk)

    if request.user != course.creator:
        return HttpResponseForbidden("Ban khong co quyen duyet thanh vien khoa hoc nay.")

    membership = get_object_or_404(
        CourseMember,
        pk=membership_id,
        course=course,
        status='pending'
    )

    if request.method == 'POST':
        if action == 'approve':
            membership.status = 'approved'
            messages.success(request, f'Da chap nhan {membership.user.username}.')
        elif action == 'reject':
            membership.status = 'rejected'
            messages.warning(request, f'Da tu choi {membership.user.username}.')
        else:
            return HttpResponseForbidden("Hanh dong khong hop le.")

        membership.reviewed_at = timezone.now()
        membership.reviewed_by = request.user
        membership.save()

    return redirect('courses:course_detail', pk=course.pk)
