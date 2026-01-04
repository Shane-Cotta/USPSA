from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from classification.models import ShooterProfile


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=False)
    uspsa_number = forms.CharField(max_length=32)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "uspsa_number")

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            ShooterProfile.objects.update_or_create(
                user=user, defaults={"uspsa_number": self.cleaned_data["uspsa_number"]}
            )
        return user


class ShooterProfileForm(forms.ModelForm):
    class Meta:
        model = ShooterProfile
        fields = ("uspsa_number", "name", "club")
