from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, HttpResponseForbidden, Http404
from .models import PersonalTodo
from .models import Todo,PersonalTodo
from .forms import TodoForm, SubmitTodoForm
from django.db.models import Q
from django.utils import timezone
import mimetypes
import os

@login_required
def teacher_todo(request):

    todos = Todo.objects.filter(
        assigned_by=request.user
    ).select_related('user', 'classroom').order_by('-created_at', 'classroom__name', 'user__username')

    grouped = {}

    for todo in todos:
        key = (
            todo.classroom_id,
            todo.title,
            todo.description or '',
            todo.deadline,
            todo.priority,
        )

        if key not in grouped:
            grouped[key] = {
                'classroom': todo.classroom,
                'title': todo.title,
                'description': todo.description,
                'deadline': todo.deadline,
                'priority': todo.priority,
                'items': [],
                'submitted': [],
                'pending': [],
                'is_late': bool(todo.deadline and timezone.now() > todo.deadline),
                'representative_id': todo.id,
            }

        group = grouped[key]
        group['items'].append(todo)

        if todo.submission_text.strip() or todo.submission_file:
            group['submitted'].append(todo)
        else:
            group['pending'].append(todo)

    return render(request, 'todo/teacher_todo_list.html', {
        'assignment_groups': list(grouped.values())
    })


@login_required
def todo_home(request):

    if request.user.role == 'teacher':
        return redirect('todo:teacher_todo_list')

    return redirect('todo:todo_list')

@login_required
def create_personal_todo(request):
    if request.method == "POST":

        title = request.POST.get("title")
        description = request.POST.get("description")
        priority = request.POST.get("priority")
        deadline = request.POST.get("deadline")
        is_public = False

        PersonalTodo.objects.create(
            user=request.user,
            title=title,
            description=description,
            priority=priority,
            deadline=deadline,
            is_public=is_public
        )

        return redirect("todo:todo_list")

    return render(request, "todo/student_create_todo.html")
@login_required
def student_todo(request):

    my_todos = Todo.objects.filter(
        user=request.user
    ).order_by('deadline')

    return render(request, 'todo/todo_list.html', {
        'my_todos': my_todos,
    })

@login_required
def todo_list(request):

    todos = PersonalTodo.objects.filter(user=request.user).order_by("deadline")
    assigned_todos = Todo.objects.filter(
        user=request.user
    ).select_related('classroom', 'assigned_by').order_by('todo_completed', 'deadline')

    personal_total = todos.count()
    personal_done = todos.filter(completed=True).count()
    assigned_total = assigned_todos.count()
    assigned_done = assigned_todos.filter(todo_completed=True).count()

    return render(
        request,
        "todo/todo_list.html",
        {
            "todos": todos,
            "assigned_todos": assigned_todos,
            "personal_total": personal_total,
            "personal_done": personal_done,
            "assigned_total": assigned_total,
            "assigned_done": assigned_done,
        }
    )
@login_required
def edit_personal_todo(request, pk):
    todo = get_object_or_404(
        PersonalTodo,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":
        todo.title = request.POST.get("title")
        todo.description = request.POST.get("description")
        todo.priority = request.POST.get("priority")
        todo.deadline = request.POST.get("deadline")
        todo.is_public = False

        todo.save()

        return redirect("todo:todo_list")

    return render(
        request,
        "todo/edit_personal_todo.html",
        {"todo": todo}
    )
@login_required
def toggle_todo(request, pk):

    todo = get_object_or_404(
        Todo,
        id=pk,
        user=request.user
    )

    todo.todo_completed = not todo.todo_completed
    todo.save(update_fields=['todo_completed'])

    return redirect('todo:todo_list')


@login_required
def submit_todo(request, pk):

    todo = get_object_or_404(
        Todo,
        pk=pk,
        user=request.user
    )

    if request.method == 'POST':

        if todo.deadline and timezone.now() > todo.deadline:
            messages.error(request, "Bài đã quá hạn, bạn không thể nộp bài.")
            return redirect('todo:todo_list')

        form = SubmitTodoForm(
            request.POST,
            request.FILES,
            instance=todo
        )

        if form.is_valid():

            submitted_todo = form.save(commit=False)
            submitted_todo.completed = True
            submitted_todo.save()

            messages.success(request, 'Nộp bài thành công.')

            return redirect('todo:todo_list')

    else:
        form = SubmitTodoForm(instance=todo)

    return render(request, 'todo/submit_todo.html', {
        'form': form,
        'todo': todo
    })

@login_required
def delete_personal_todo(request, pk):
    todo = get_object_or_404(
        PersonalTodo,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":
        todo.delete()
        return redirect("todo:todo_list")

    return render(request,
        "todo/delete_personal_todo.html",
        {"todo": todo})
@login_required
def complete_personal_todo(request, pk):
    todo = get_object_or_404(
        PersonalTodo,
        pk=pk,
        user=request.user
    )

    todo.completed = not todo.completed
    todo.save()

    return redirect("todo:todo_list")

@login_required
def view_submission_file(request, pk):
    todo = get_object_or_404(
        Todo.objects.select_related('classroom', 'assigned_by', 'user'),
        pk=pk
    )

    can_view = (
        todo.user == request.user or
        todo.assigned_by == request.user or
        (todo.classroom and todo.classroom.teacher == request.user)
    )

    if not can_view:
        return HttpResponseForbidden("Bạn không có quyền xem file nộp bài này.")

    if not todo.submission_file:
        raise Http404("Bài này chưa có file nộp.")

    download = request.GET.get('download') == '1'
    filename = os.path.basename(todo.submission_file.name)
    content_type, _ = mimetypes.guess_type(filename)

    return FileResponse(
        todo.submission_file.open('rb'),
        as_attachment=download,
        filename=filename,
        content_type=content_type or 'application/octet-stream'
    )
