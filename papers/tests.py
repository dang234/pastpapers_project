from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import PastPaper, Profile
from django.core.files.uploadedfile import SimpleUploadedFile

class BaseTestCase(TestCase):
    """Base setup for users and papers"""
    def setUp(self):
        # Normal user
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # Admin user
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpass')

        # Sample papers
        self.paper_file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        self.paper1 = PastPaper.objects.create(
            title="Math Paper",
            course_code="MATH101",
            department="Mathematics",
            year="2024",
            semester="1",
            file=self.paper_file,
            user=self.admin_user
        )
        self.paper2 = PastPaper.objects.create(
            title="CS Paper",
            course_code="CS101",
            department="Computer Science",
            year="2025",
            semester="2",
            file=self.paper_file,
            user=self.admin_user
        )

        self.client = Client()

# ================================
# Model Tests
# ================================
class ModelTests(BaseTestCase):
    def test_paper_creation(self):
        self.assertEqual(self.paper1.title, "Math Paper")
        self.assertEqual(self.paper1.download_count, 0)

    def test_increment_download_count(self):
        self.paper1.increment_download_count()
        self.paper1.refresh_from_db()
        self.assertEqual(self.paper1.download_count, 1)

# ================================
# View & URL Tests
# ================================
class ViewTests(BaseTestCase):
    def test_landing_redirect_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('landing'))
        self.assertRedirects(response, reverse('home'))

    def test_home_requires_login(self):
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, '/login/?next=/home/')

    def test_view_papers_content(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('view_papers'))
        self.assertContains(response, 'Math Paper')
        self.assertContains(response, 'CS Paper')

# ================================
# Permissions / Admin Only
# ================================
class PermissionTests(BaseTestCase):
    def test_upload_access(self):
        # Normal user cannot access
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('upload_paper'))
        self.assertEqual(response.status_code, 302)

        # Admin can access
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('upload_paper'))
        self.assertEqual(response.status_code, 200)

    def test_delete_paper_permissions(self):
        url = reverse('delete_paper', args=[self.paper1.id])
        # Normal user cannot delete
        self.client.login(username='testuser', password='testpass')
        self.client.post(url)
        self.assertTrue(PastPaper.objects.filter(id=self.paper1.id).exists())

        # Admin can delete
        self.client.login(username='admin', password='adminpass')
        self.client.post(url)
        self.assertFalse(PastPaper.objects.filter(id=self.paper1.id).exists())

    def test_edit_paper_permissions(self):
        url = reverse('edit_paper', args=[self.paper2.id])
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect

# ================================
# Registration & Profile Tests
# ================================
class UserTests(BaseTestCase):
    def test_register_user(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'ComplexPass123',
            'password2': 'ComplexPass123'
        })
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_profile_update(self):
        self.client.login(username='testuser', password='testpass')
        profile = self.user.profile
        url = reverse('account_manager')

        response = self.client.post(url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'bio': 'Updated bio',
            'university': 'Test University'
        })
        profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(profile.bio, 'Updated bio')
        self.assertEqual(profile.university, 'Test University')
        self.assertRedirects(response, url)

# ================================
# Download & Theme Tests
# ================================
class ActionTests(BaseTestCase):
    def test_download_increments_count(self):
        url = reverse('download_paper', args=[self.paper1.id])
        response = self.client.get(url)
        self.paper1.refresh_from_db()
        self.assertEqual(self.paper1.download_count, 1)
        self.assertEqual(response.status_code, 302)

    def test_set_theme_api(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(
            reverse('set_theme'),
            data='{"theme":"dark"}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'success', 'theme': 'dark'})
        self.assertEqual(self.client.session['theme'], 'dark')

        # GET request should fail
        response = self.client.get(reverse('set_theme'))
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {'error': 'Invalid request'})

# ================================
# Search & Filter Tests
# ================================
class SearchFilterTests(BaseTestCase):
    def test_search_title(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('view_papers'), {'q': 'Math'})
        self.assertContains(response, 'Math Paper')
        self.assertNotContains(response, 'CS Paper')

    def test_filter_department(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('view_papers'), {'department': 'Computer Science'})
        self.assertContains(response, 'CS Paper')
        self.assertNotContains(response, 'Math Paper')

    def test_filter_year(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('view_papers'), {'year': '2024'})
        self.assertContains(response, 'Math Paper')
        self.assertNotContains(response, 'CS Paper')
