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
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.contrib import messages
from django.db import transaction
import logging
from .models import Profile, Download
from django.core.paginator import Paginator





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
logger = logging.getLogger(__name__)

@user_passes_test(is_admin)
def upload_paper(request):
    """Handle both single and bulk paper uploads"""
    
    if request.method == 'POST':
        upload_type = request.POST.get('upload_type', 'single')
        
        try:
            if upload_type == 'single':
                success = handle_single_upload(request)
            else:
                success = handle_bulk_upload(request)
            
            if success:
                return render(request, 'upload.html', {'success': True})
            else:
                messages.error(request, 'Upload failed. Please try again.')
                
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            messages.error(request, f'An error occurred: {str(e)}')
    
    return render(request, 'upload.html')

# Add these new helper functions to your views.py:

def handle_single_upload(request):
    """Handle single file upload"""
    
    # Extract form data
    title = request.POST.get('title', '').strip()
    course_code = request.POST.get('course_code', '').strip()
    department = request.POST.get('department', '').strip()
    year = request.POST.get('year')
    semester = request.POST.get('semester', '').strip()
    uploaded_file = request.FILES.get('file')
    
    # Validation
    if not all([title, course_code, department, year, semester, uploaded_file]):
        messages.error(request, 'All fields are required.')
        return False
    
    # Validate file type
    if not uploaded_file.name.lower().endswith('.pdf'):
        messages.error(request, 'Only PDF files are allowed.')
        return False
    
    try:
        # Create PastPaper object
        paper = PastPaper.objects.create(
            title=title,
            course_code=course_code,
            department=department,
            year=int(year),
            semester=semester,
            file=uploaded_file,
            user=request.user
        )
        
        logger.info(f"Single paper uploaded: {paper.title}")
        messages.success(request, f'Paper "{title}" uploaded successfully!')
        return True
        
    except Exception as e:
        logger.error(f"Single upload error: {str(e)}")
        messages.error(request, f'Error uploading paper: {str(e)}')
        return False

def handle_bulk_upload(request):
    """Handle bulk file upload"""
    
    # Extract common data
    department = request.POST.get('bulk_department', '').strip()
    year = request.POST.get('bulk_year')
    semester = request.POST.get('bulk_semester', '').strip()
    
    # Get files and their metadata
    files = request.FILES.getlist('files')
    course_codes = request.POST.getlist('course_codes[]')
    titles = request.POST.getlist('titles[]')
    
    # Validation
    if not all([department, year, semester]):
        messages.error(request, 'Department, year, and semester are required for bulk upload.')
        return False
    
    if not files:
        messages.error(request, 'No files selected for upload.')
        return False
    
    if len(files) != len(course_codes) or len(files) != len(titles):
        messages.error(request, 'Mismatch between files and metadata. Please try again.')
        return False
    
    # Validate all files are PDFs
    for file in files:
        if not file.name.lower().endswith('.pdf'):
            messages.error(request, f'File "{file.name}" is not a PDF. All files must be PDFs.')
            return False
    
    # Use database transaction for bulk upload
    try:
        with transaction.atomic():
            uploaded_papers = []
            
            for i, file in enumerate(files):
                course_code = course_codes[i].strip()
                title = titles[i].strip()
                
                # Skip if essential data is missing
                if not course_code or not title:
                    messages.warning(request, f'Skipped file "{file.name}" - missing course code or title.')
                    continue
                
                # Create PastPaper object
                paper = PastPaper.objects.create(
                    title=title,
                    course_code=course_code,
                    department=department,
                    year=int(year),
                    semester=semester,
                    file=file,
                    user=request.user
                )
                
                uploaded_papers.append(paper)
                logger.info(f"Bulk uploaded: {paper.title}")
            
            if uploaded_papers:
                messages.success(request, f'Successfully uploaded {len(uploaded_papers)} papers!')
                return True
            else:
                messages.warning(request, 'No papers were uploaded. Please check your data.')
                return False
                
    except Exception as e:
        logger.error(f"Bulk upload error: {str(e)}")
        messages.error(request, f'Error during bulk upload: {str(e)}')
        return False
    

# 📄 View Papers
# ==========================
def view_papers(request):
    # Get all papers initially
    papers = PastPaper.objects.all()
    
    # Handle search query
    query = request.GET.get('q', '')
    if query:
        papers = papers.filter(
            Q(title__icontains=query) |
            Q(course_code__icontains=query) |
            Q(department__icontains=query) |
            Q(year__icontains=query)
        )
    
    # Handle department filter
    selected_department = request.GET.get('department', '')
    if selected_department:
        papers = papers.filter(department=selected_department)
    
    # Handle year filter
    selected_year = request.GET.get('year', '')
    if selected_year:
        papers = papers.filter(year=selected_year)
    
    # Handle tab filters (new functionality)
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'recent':
        # Show papers uploaded in the last 30 days
        papers = papers.filter(uploaded_at__gte=timezone.now() - timedelta(days=30))
    elif filter_type == 'files':
        # Show only papers that have files attached
        papers = papers.exclude(file='')
    
    # Handle sorting (new functionality)
    sort_by = request.GET.get('sort', 'relevance')
    if sort_by == 'title':
        papers = papers.order_by('title')
    elif sort_by == '-uploaded_at':
        papers = papers.order_by('-uploaded_at')
    elif sort_by == '-year':
        papers = papers.order_by('-year')
    elif sort_by == 'relevance' or not sort_by:
        # Default ordering
        papers = papers.order_by('-uploaded_at')
    
    # Get filter options for dropdowns
    departments = PastPaper.objects.values_list('department', flat=True).distinct().order_by('department')
    years = PastPaper.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    # Pagination
    paginator = Paginator(papers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'papers': page_obj,
        'query': query,
        'selected_department': selected_department,
        'selected_year': selected_year,
        'filter_type': filter_type,
        'sort_by': sort_by,
        'departments': departments,
        'years': years,
    }
    
    return render(request, 'view.html', context)
# ==========================
# 📥 Download + Track
# ==========================
from django.contrib.auth.decorators import login_required

@login_required
def download_paper(request, paper_id):
    paper = get_object_or_404(PastPaper, pk=paper_id)
    
    # Track the download
    Download.objects.get_or_create(user=request.user, paper=paper)
    
    # Increment download count
    paper.increment_download_count()
    
    return redirect(paper.file.url)

# ==========================
# 📥 My Downloads (User only)

@login_required
def my_downloads(request):
    # Get papers downloaded by the current user
    downloaded_papers = PastPaper.objects.filter(
        user_downloads__user=request.user
    ).select_related('user').prefetch_related('user_downloads').distinct().order_by('-user_downloads__downloaded_at')
    
    # Pagination
    paginator = Paginator(downloaded_papers, 10)
    page_number = request.GET.get('page')
    papers = paginator.get_page(page_number)
    
    return render(request, 'my_files.html', {'papers': papers})

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
    # Get or create profile if it doesn't exist
    profile, created = Profile.objects.get_or_create(user=request.user)

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


# themes
# ==========================
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

