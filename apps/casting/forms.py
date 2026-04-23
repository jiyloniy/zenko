from django import forms
from apps.casting.models import Stanok


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
