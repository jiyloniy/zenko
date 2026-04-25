from django import forms
from apps.casting.models import Stanok, QuyishRasxod


class StanokForm(forms.ModelForm):
    """
    Stanok yaratish va tahrirlash uchun Django Form klasi.
    """
    
    class Meta:
        model = Stanok
        fields = ['name', 'status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'f-input',
                'placeholder': 'masalan: Stanok №1',
                'required': True,
                'autofocus': True,
            }),
            'status': forms.RadioSelect(attrs={
                'class': 'status-radio',
            }),
        }
        labels = {
            'name': 'Nomi',
            'status': 'Holat',
        }
    
    def clean_name(self):
        """Nomi bo'sh bo'lmasligi va unikalligi tekshiramiz."""
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Nomi majburiy.')
        
        # Update holatida eski nomni tekshiramiz
        if self.instance.pk:
            if Stanok.objects.exclude(pk=self.instance.pk).filter(name=name).exists():
                raise forms.ValidationError('Bu nomi bilan stanok allaqachon mavjud.')
        else:
            if Stanok.objects.filter(name=name).exists():
                raise forms.ValidationError('Bu nomi bilan stanok allaqachon mavjud.')
        
        return name
    
    def clean_status(self):
        """Status faqat to'g'ri qiymatlardan bo'lishi kerak."""
        status = self.cleaned_data.get('status')
        if not status:
            raise forms.ValidationError("Holatni tanlang.")
        
        valid_statuses = dict(Stanok.Status.choices).keys()
        if status not in valid_statuses:
            raise forms.ValidationError("Noto'g'ri holat tanlanmoqda.")
        
        return status


class QuyishRasxodForm(forms.ModelForm):
    """Quyish rasxodi yaratish va tahrirlash uchun forma."""

    class Meta:
        model = QuyishRasxod
        fields = ['nomi', 'miqdor', 'sana', 'izoh']
        widgets = {
            'nomi': forms.TextInput(attrs={
                'class': 'f-inp',
                'placeholder': 'Rasxod nomi',
                'required': True,
            }),
            'miqdor': forms.NumberInput(attrs={
                'class': 'f-inp',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'required': True,
            }),
            'sana': forms.DateInput(attrs={
                'class': 'f-inp',
                'type': 'date',
                'required': True,
            }),
            'izoh': forms.Textarea(attrs={
                'class': 'f-inp',
                'placeholder': 'Ixtiyoriy izoh...',
                'rows': 2,
            }),
        }
        labels = {
            'nomi': 'Rasxod nomi',
            'miqdor': 'Miqdor',
            'sana': 'Sana',
            'izoh': 'Izoh',
        }

    def clean_nomi(self):
        nomi = self.cleaned_data.get('nomi', '').strip()
        if not nomi:
            raise forms.ValidationError('Rasxod nomi majburiy.')
        return nomi

    def clean_miqdor(self):
        miqdor = self.cleaned_data.get('miqdor')
        if miqdor is not None and miqdor < 0:
            raise forms.ValidationError('Miqdor manfiy bo\'lishi mumkin emas.')
        return miqdor

