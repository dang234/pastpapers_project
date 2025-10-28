# pastpapers_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language
from papers import views as papers_views  # Import your papers app views
from papers import views
# Non-internationalized URLs (no language prefix needed)
urlpatterns = [
    # Language switching endpoint
    path('set-language/', set_language, name='set_language'),
    # Theme switching endpoint
    path('set-theme/', papers_views.set_theme, name='set_theme'),
]

# Internationalized URLs (will have language prefixes like /en/, /sw/, /fr/)
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('papers.urls')),
    #path('multiupload/', include('multiupload.urls')),
    path('', views.landing_or_home, name='landing'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    prefix_default_language=False,  # Don't prefix default language (English)
)

# Serve uploaded files (only in development mode)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)