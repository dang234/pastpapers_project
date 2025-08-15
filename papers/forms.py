from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile


# Sign-up form
class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="Required. Use a valid email address."
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


# Update user basic info
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']


# Update profile details
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_image', 'bio', 'university']
