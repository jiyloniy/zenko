from django import forms
from apps.order.models import Order, Brujka


class BrujkaForm(forms.ModelForm):
    class Meta:
        model = Brujka
        fields = ('name', 'image', 'color', 'coating_type', 'description', 'is_active')
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('brujka', 'name', 'quantity', 'image', 'deadline', 'priority', 'status', 'note')
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = False
