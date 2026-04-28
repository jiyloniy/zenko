from django import forms
from .models import BoyashJarayonLog


class BoyashLogForm(forms.ModelForm):
    class Meta:
        model = BoyashJarayonLog
        fields = ('smena', 'vishilka_soni', 'par_soni', 'izoh', 'sana')
        widgets = {
            'smena':         forms.Select(attrs={'class': 'f-inp'}),
            'vishilka_soni': forms.NumberInput(attrs={'class': 'f-inp', 'min': 1}),
            'par_soni':      forms.NumberInput(attrs={'class': 'f-inp', 'min': 1}),
            'izoh':          forms.Textarea(attrs={'class': 'f-inp', 'rows': 2}),
            'sana':          forms.DateInput(attrs={'class': 'f-inp', 'type': 'date'}),
        }

    def clean_vishilka_soni(self):
        val = self.cleaned_data.get('vishilka_soni', 1)
        if val < 1:
            raise forms.ValidationError("Vishilka soni kamida 1 bo'lishi kerak.")
        return val

    def clean_par_soni(self):
        val = self.cleaned_data.get('par_soni', 1)
        if val < 1:
            raise forms.ValidationError("Par soni kamida 1 bo'lishi kerak.")
        return val
