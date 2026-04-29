from django import forms
from apps.users.models import User
from .models import Tosh, ToshQadashLog, KleyRasxod, ToshRasxod


class ToshForm(forms.ModelForm):
    class Meta:
        model  = Tosh
        fields = ('name', 'code', 'is_active')
        widgets = {
            'name':      forms.TextInput(attrs={'class': 'f-inp'}),
            'code':      forms.TextInput(attrs={'class': 'f-inp'}),
            'is_active': forms.CheckboxInput(),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Nom kiritilishi shart.')
        return name

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError('Kod kiritilishi shart.')
        qs = Tosh.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Bu kodli tosh allaqachon mavjud.')
        return code


class ToshLogForm(forms.ModelForm):
    class Meta:
        model  = ToshQadashLog
        fields = ('hodim', 'smena', 'tosh', 'par_soni', 'izoh', 'sana')
        widgets = {
            'hodim':    forms.Select(attrs={'class': 'f-inp'}),
            'smena':    forms.Select(attrs={'class': 'f-inp'}),
            'tosh':     forms.Select(attrs={'class': 'f-inp'}),
            'par_soni': forms.NumberInput(attrs={'class': 'f-inp', 'min': 1}),
            'izoh':     forms.Textarea(attrs={'class': 'f-inp', 'rows': 2}),
            'sana':     forms.DateInput(attrs={'class': 'f-inp', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hodim'].queryset    = User.objects.all().order_by('name')
        self.fields['hodim'].empty_label = 'Hodimni tanlang'
        self.fields['tosh'].queryset     = Tosh.objects.filter(is_active=True)
        self.fields['tosh'].empty_label  = 'Tosh turini tanlang'

    def clean_par_soni(self):
        val = self.cleaned_data.get('par_soni', 1)
        if val < 1:
            raise forms.ValidationError('Par soni kamida 1 bo\'lishi kerak.')
        return val


class KleyRasxodForm(forms.ModelForm):
    class Meta:
        model  = KleyRasxod
        fields = ('smena', 'kley_gramm', 'sana', 'izoh')
        widgets = {
            'smena':      forms.Select(attrs={'class': 'f-inp'}),
            'kley_gramm': forms.NumberInput(attrs={'class': 'f-inp', 'min': 0, 'step': '0.01'}),
            'sana':       forms.DateInput(attrs={'class': 'f-inp', 'type': 'date'}),
            'izoh':       forms.Textarea(attrs={'class': 'f-inp', 'rows': 2}),
        }

    def clean_kley_gramm(self):
        val = self.cleaned_data.get('kley_gramm', 0)
        if val <= 0:
            raise forms.ValidationError('Kley miqdori 0 dan katta bo\'lishi kerak.')
        return val


class ToshRasxodForm(forms.ModelForm):
    class Meta:
        model  = ToshRasxod
        fields = ('tosh', 'smena', 'tosh_gramm', 'sana', 'izoh')
        widgets = {
            'tosh':       forms.Select(attrs={'class': 'f-inp'}),
            'smena':      forms.Select(attrs={'class': 'f-inp'}),
            'tosh_gramm': forms.NumberInput(attrs={'class': 'f-inp', 'min': 0, 'step': '0.01'}),
            'sana':       forms.DateInput(attrs={'class': 'f-inp', 'type': 'date'}),
            'izoh':       forms.Textarea(attrs={'class': 'f-inp', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tosh'].queryset    = Tosh.objects.filter(is_active=True)
        self.fields['tosh'].empty_label = 'Tosh turini tanlang'

    def clean_tosh_gramm(self):
        val = self.cleaned_data.get('tosh_gramm', 0)
        if val <= 0:
            raise forms.ValidationError('Tosh miqdori 0 dan katta bo\'lishi kerak.')
        return val
