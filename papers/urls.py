from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
     # smart redirect
     path('', views.landing_or_home, name='landing'),
     path('landing/', views.landing_or_home, name='landing'),
    path('home/', views.home, name='home'),
    path('upload/', views.upload_paper, name='upload_paper'),
    path('view/', views.view_papers, name='view_papers'),
    path('delete/<int:paper_id>/', views.delete_paper, name='delete_paper'),
    path('edit/<int:paper_id>/', views.edit_paper, name='edit_paper'),
    path('download/<int:paper_id>/', views.download_paper, name='download_paper'),

    path('settings/', views.settings_view, name='settings'),
    path('my_files/', views.my_files, name='my_files'),
    path('account/', views.account_manager, name='account_manager'),
    path('about/', views.about, name='about'),

    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register, name='register'),
    path('set-theme/', views.set_theme, name='set_theme'),
    

]
