from django import forms
from apps.casting.models import Stanok, QuyishRasxod
from apps.order.models import Order, Brujka


class OrderForm(forms.ModelForm):
    """Casting manager uchun buyurtma yaratish/tahrirlash formasi."""

    class Meta:
        model = Order
        fields = ['name', 'brujka', 'quantity', 'deadline', 'priority', 'note', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'f-inp',
                'placeholder': 'Buyurtma nomi',
                'required': True,
                'autofocus': True,
            }),
            'brujka': forms.Select(attrs={'class': 'f-inp'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'f-inp',
                'placeholder': '0',
                'min': '1',
                'required': True,
            }),
            'deadline': forms.DateInput(attrs={
                'class': 'f-inp',
                'type': 'date',
                'required': True,
            }),
            'priority': forms.Select(attrs={'class': 'f-inp'}),
            'note': forms.Textarea(attrs={
                'class': 'f-inp',
                'placeholder': 'Ixtiyoriy izoh...',
                'rows': 3,
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'f-inp'}),
        }
        labels = {
            'name': 'Buyurtma nomi',
            'brujka': 'Brujka',
            'quantity': 'Miqdor (dona)',
            'deadline': 'Muddat',
            'priority': 'Muhimlik',
            'note': 'Izoh',
            'image': 'Rasm',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        brujka_field = self.fields['brujka']  # type: ignore[index]
        brujka_field.queryset = Brujka.objects.filter(is_active=True).order_by('name')  # type: ignore[attr-defined]
        brujka_field.empty_label = '— Brujka tanlang —'  # type: ignore[attr-defined]
        brujka_field.required = False

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is None or qty < 1:
            raise forms.ValidationError('Miqdor kamida 1 bo\'lishi kerak.')
        return qty

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if not deadline:
            raise forms.ValidationError('Muddat majburiy.')
        return deadline


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
        fields = ['nomi', 'miqdor', 'sana', 'izoh']
        model = QuyishRasxod
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

