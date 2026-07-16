from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from .models import Document
from .forms import DocumentForm

@login_required
def document_list(request):

    documents = Document.objects.all().order_by('-created_at')

    q = request.GET.get('q')
    level = request.GET.get('level')
    subject = request.GET.get('subject')

    if q:
        documents = documents.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(subject__icontains=q)
        )

    if level:
        documents = documents.filter(level=level)

    if subject:
        documents = documents.filter(subject__icontains=subject)

    return render(
        request,
        'materials/document_list.html',
        {
            'documents': documents
        }
    )

@login_required
def edit_document(request, pk):
    doc = get_object_or_404(
        Document,
        pk=pk,
        owner=request.user
    )

    if request.method == "POST":

        doc.title = request.POST.get("title")
        doc.description = request.POST.get("description")
        doc.subject = request.POST.get("subject")
        doc.level = request.POST.get("level")
        doc.permission = request.POST.get("permission")

        if request.FILES.get("file"):
            doc.file = request.FILES.get("file")

        doc.save()

        messages.success(
            request,
            "Cập nhật tài liệu thành công."
        )

        return redirect("materials:document_list")

    return render(
        request,
        "materials/edit_document.html",
        {"doc": doc}
    )
@login_required
def delete_document(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)

    if request.method == "POST":
        doc.delete()
        return redirect("materials:document_list")

    return render(request, "materials/delete_document.html", {"doc": doc})
@login_required
def upload_document(request):

    if request.method == "POST":

        Document.objects.create(
            owner=request.user,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            level=request.POST.get("level"),
            subject=request.POST.get("subject"),
            permission=request.POST.get("permission"),
            file=request.FILES.get("file")
        )

        messages.success(
            request,
            "Tải tài liệu thành công."
        )

        return redirect("materials:document_list")

    return render(
        request,
        "materials/upload_document.html"
    )

@login_required
def download_document(request, pk):

    document = get_object_or_404(
        Document,
        pk=pk
    )

    return render(
        request,
        'materials/download_document.html',
        {
            'document': document
        }
    )