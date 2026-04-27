from django import forms
from apps.users.models import User
from .models import IlishJarayonLog, Vishilka


class IlishLogForm(forms.ModelForm):
    class Meta:
        model  = IlishJarayonLog
        fields = ('hodim', 'smena', 'vishilka', 'vishilka_soni', 'izoh', 'sana')
        widgets = {
            'hodim':         forms.Select(attrs={'class': 'f-inp'}),
            'smena':         forms.Select(attrs={'class': 'f-inp'}),
            'vishilka':      forms.Select(attrs={'class': 'f-inp'}),
            'vishilka_soni': forms.NumberInput(attrs={'class': 'f-inp', 'min': 1}),
            'izoh':          forms.Textarea(attrs={'class': 'f-inp', 'rows': 2}),
            'sana':          forms.DateInput(attrs={'class': 'f-inp', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hodim'].queryset    = User.objects.all().order_by('name')
        self.fields['hodim'].empty_label = 'Hodimni tanlang'
        self.fields['vishilka'].queryset    = Vishilka.objects.filter(is_active=True)
        self.fields['vishilka'].empty_label = 'Vishilkani tanlang'

    def clean_vishilka_soni(self):
        val = self.cleaned_data.get('vishilka_soni', 1)
        if val < 1:
            raise forms.ValidationError('Vishilka soni kamida 1 bo\'lishi kerak.')
        return val


class VishilkaForm(forms.ModelForm):
    class Meta:
        model  = Vishilka
        fields = ('nomi', 'quantity', 'is_active')
        widgets = {
            'nomi':      forms.TextInput(attrs={'class': 'f-inp'}),
            'quantity':  forms.NumberInput(attrs={'class': 'f-inp', 'min': 1}),
            'is_active': forms.CheckboxInput(),
        }

    def clean_nomi(self):
        nomi = self.cleaned_data.get('nomi', '').strip()
        if not nomi:
            raise forms.ValidationError('Nom kiritilishi shart.')
        qs = Vishilka.objects.filter(nomi__iexact=nomi)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Bu nomli vishilka allaqachon mavjud.')
        return nomi

    def clean_quantity(self):
        val = self.cleaned_data.get('quantity', 0)
        if val < 1:
            raise forms.ValidationError('Par soni kamida 1 bo\'lishi kerak.')
        return val
