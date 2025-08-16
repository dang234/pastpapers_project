from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseRedirect, FileResponse, JsonResponse
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import PastPaper
from .forms import SignUpForm
import json
import os
import base64
from django.conf import settings
from .forms import UserForm, ProfileForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods



# ==========================
# Landing or Home Logic
# ==========================
def landing_or_home(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'landing.html')


# ==========================
# 🔐 Only allow admin or staff users
# ==========================
def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# ==========================
# 🏠 Home / Dashboard
# ==========================


@login_required
def home(request):
    recent_papers = PastPaper.objects.order_by('-uploaded_at')[:5]
    popular_papers = PastPaper.objects.order_by('-download_count')[:5]
    return render(request, 'home.html', {
        'recent_papers': recent_papers,
        'popular_papers': popular_papers
    })



# ==========================
# 📤 Upload View (Admin only)
# ==========================
@user_passes_test(is_admin)
def upload_paper(request):
    if request.method == 'POST' and request.FILES.get('file'):
        title = request.POST['title']
        course_code = request.POST['course_code']
        department = request.POST['department']
        year = request.POST['year']
        semester = request.POST['semester']
        file = request.FILES['file']

        paper = PastPaper(
            title=title,
            course_code=course_code,
            department=department,
            year=year,
            semester=semester,
            file=file,
            user=request.user
        )
        paper.save()
        return render(request, 'upload.html', {'success': True})

    return render(request, 'upload.html')


# ==========================
# 📄 View Papers
# ==========================
def view_papers(request):
    query = request.GET.get('q')
    department_filter = request.GET.get('department')
    year_filter = request.GET.get('year')

    papers = PastPaper.objects.all()

    if query:
        papers = papers.filter(
            title__icontains=query
        ) | papers.filter(
            course_code__icontains=query
        ) | papers.filter(
            year__icontains=query
        )

    if department_filter:
        papers = papers.filter(department=department_filter)

    if year_filter:
        papers = papers.filter(year=year_filter)

    departments = PastPaper.objects.values_list('department', flat=True).distinct()
    years = PastPaper.objects.values_list('year', flat=True).distinct()

    paginator = Paginator(papers.order_by('-uploaded_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'view.html', {
        'papers': page_obj,
        'query': query,
        'departments': departments,
        'years': years,
        'selected_department': department_filter,
        'selected_year': year_filter,
    })


# ==========================
# 📥 Download + Track
# ==========================
def download_paper(request, paper_id):
    paper = get_object_or_404(PastPaper, pk=paper_id)
    paper.increment_download_count()
    return redirect(paper.file.url)


# ==========================
# ❌ Delete Paper (Admin only)
# ==========================
@user_passes_test(is_admin)
def delete_paper(request, paper_id):
    paper = get_object_or_404(PastPaper, pk=paper_id)
    paper.file.delete()
    paper.delete()
    return redirect('view_papers')


# ==========================
# ✏️ Edit Paper (Admin only)
# ==========================
@user_passes_test(is_admin)
def edit_paper(request, paper_id):
    paper = get_object_or_404(PastPaper, pk=paper_id)

    if request.method == 'POST':
        paper.title = request.POST['title']
        paper.course_code = request.POST['course_code']
        paper.department = request.POST['department']
        paper.year = request.POST['year']
        paper.semester = request.POST['semester']
        if request.FILES.get('file'):
            paper.file.delete()
            paper.file = request.FILES['file']
        paper.save()
        return redirect('view_papers')

    return render(request, 'edit.html', {'paper': paper})


# ==========================
# 📂 My Files (User only)
# ==========================
@login_required
def my_files(request):
    user_papers = PastPaper.objects.filter(user=request.user).order_by('-uploaded_at')

    paginator = Paginator(user_papers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'my_files.html', {
        'papers': page_obj
    })


# ==========================
# ⚙️ Settings
# ==========================
@login_required
def settings_view(request):
    return render(request, 'settings.html')


# ==========================
# 👤 Account Manager
# ==========================


@login_required
def account_manager(request):
    profile = request.user.profile  # Assuming OneToOne relationship

    # Check if user is in edit mode
    edit_mode = request.GET.get("edit") == "true"

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect("account_manager")  # Back to view mode

    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)

    return render(request, "account_manager.html", {
        "user_form": user_form,
        "profile_form": profile_form,
        "profile": profile,
        "edit_mode": edit_mode
    })


# ==========================
# 📝 Register User
# ==========================
def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})


# Replace your existing set_theme function with this updated version:


@csrf_exempt  # Add this decorator
@require_http_methods(["POST"])  # Add this decorator
def set_theme(request):
    """Handle theme switching requests from frontend"""
    try:
        data = json.loads(request.body)
        theme = data.get('theme')
        
        if theme in ['light', 'dark']:
            # Save theme in session
            request.session['theme'] = theme
            return JsonResponse({'status': 'success', 'theme': theme})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid theme'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# ==========================
# ℹ️ About Page
# ==========================
@login_required
def about(request):
    profile_path = os.path.join(settings.BASE_DIR, 'papers', 'static', 'papers', 'images', 'profile.jpg')

    if os.path.exists(profile_path):
        # Use actual profile picture if exists
        profile_image_url = f"papers/images/profile.jpg"
        avatar_data_uri = None
    else:
        # Generate default SVG avatar with initials "DT"
        initials = "DT"
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" width="150" height="150">
            <rect width="100%" height="100%" fill="#3B82F6"/>
            <text x="50%" y="55%" font-size="60" fill="white" font-family="Arial" text-anchor="middle" dominant-baseline="middle">{initials}</text>
        </svg>
        '''
        svg_base64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        avatar_data_uri = f"data:image/svg+xml;base64,{svg_base64}"
        profile_image_url = None

    return render(request, 'about.html', {
        'profile_image_url': profile_image_url,
        'avatar_data_uri': avatar_data_uri
    })

