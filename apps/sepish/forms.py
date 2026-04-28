from django import forms
from .models import SepishJarayonLog, Kraska


class SepishLogForm(forms.ModelForm):
    class Meta:
        model  = SepishJarayonLog
        fields = ('smena', 'par_soni', 'kraska', 'kraska_gramm', 'izoh', 'sana')
        widgets = {
            'smena':        forms.Select(attrs={'class': 'f-inp'}),
            'par_soni':     forms.NumberInput(attrs={'class': 'f-inp', 'min': 1}),
            'kraska':       forms.Select(attrs={'class': 'f-inp'}),
            'kraska_gramm': forms.NumberInput(attrs={'class': 'f-inp', 'min': 0}),
            'izoh':         forms.Textarea(attrs={'class': 'f-inp', 'rows': 2}),
            'sana':         forms.DateInput(attrs={'class': 'f-inp', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kraska'].queryset    = Kraska.objects.filter(is_active=True)
        self.fields['kraska'].empty_label = '— Kraska tanlang —'
        self.fields['kraska'].required    = False

    def clean_par_soni(self):
        val = self.cleaned_data.get('par_soni', 1)
        if val < 1:
            raise forms.ValidationError('Par soni kamida 1 bo\'lishi kerak.')
        return val


class KraskaForm(forms.ModelForm):
    class Meta:
        model  = Kraska
        fields = ('code', 'name', 'color_hex', 'is_active')
        widgets = {
            'code':      forms.TextInput(attrs={'class': 'f-inp'}),
            'name':      forms.TextInput(attrs={'class': 'f-inp'}),
            'color_hex': forms.TextInput(attrs={'class': 'f-inp', 'type': 'color'}),
            'is_active': forms.CheckboxInput(),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError('Kod kiritilishi shart.')
        qs = Kraska.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Bu kodli kraska allaqachon mavjud.')
        return code
