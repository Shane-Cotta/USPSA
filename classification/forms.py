import csv
from io import TextIOWrapper

from django import forms

from .models import ClassifierAttempt


class AttemptForm(forms.ModelForm):
    class Meta:
        model = ClassifierAttempt
        fields = ("division", "stage", "match_date", "hit_factor")

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop("profile", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.profile:
            obj.profile = self.profile
        if commit:
            obj.save()
        return obj


class CSVImportForm(forms.Form):
    file = forms.FileField()

    def parse_rows(self):
        file = self.cleaned_data["file"]
        wrapper = TextIOWrapper(file, encoding="utf-8")
        reader = csv.DictReader(wrapper)
        return list(reader)
