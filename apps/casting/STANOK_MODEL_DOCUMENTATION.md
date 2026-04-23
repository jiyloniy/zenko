# 📋 Stanok Model - To'liq Dokumentatsiya

## 1. MODEL TAHLILI

### Fayl: `apps/casting/models.py`

```python
class Stanok(models.Model):
    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Faol'
        REPAIR   = 'repair',   "Ta'mirda"
        INACTIVE = 'inactive', 'Faol emas'

    name   = models.CharField('Nomi', max_length=200)
    status = models.CharField('Holat', max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name        = 'Stanok'
        verbose_name_plural = 'Stanoklar'
        ordering            = ['name']

    def __str__(self):
        return self.name
```

### Model Maydonchalari:
| Field | Type | Attributes | Description |
|-------|------|-----------|-------------|
| `id` | AutoField | PK | Database ID (auto) |
| `name` | CharField | max_length=200 | **[Majburiy]** Stanok nomi |
| `status` | CharField | choices, default=active | Stanok holati (Faol/Ta'mirda/Faol emas) |

### Status Variantlari:
| Value | Label (UZ) | Use Case |
|-------|------------|----------|
| `active` | ✅ Faol | Stanok ishlayapti |
| `repair` | 🔧 Ta'mirda | Stanok ta'mirda |
| `inactive` | ❌ Faol emas | Stanok ishlamaydi |

---

## 2. DJANGO FORM KLASI

### Fayl: `apps/casting/forms.py`

```python
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
        # Nomi unikalligi tekshirish
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Nomi majburiy.')
        
        if self.instance.pk:
            if Stanok.objects.exclude(pk=self.instance.pk).filter(name=name).exists():
                raise forms.ValidationError('Bu nomi bilan stanok allaqachon mavjud.')
        else:
            if Stanok.objects.filter(name=name).exists():
                raise forms.ValidationError('Bu nomi bilan stanok allaqachon mavjud.')
        
        return name
    
    def clean_status(self):
        # Status validatsiyasi
        status = self.cleaned_data.get('status')
        if not status:
            raise forms.ValidationError("Holatni tanlang.")
        
        valid_statuses = dict(Stanok.Status.choices).keys()
        if status not in valid_statuses:
            raise forms.ValidationError("Noto'g'ri holat tanlanmoqda.")
        
        return status
```

### Form Features:
✅ Automatic model field validation  
✅ Custom `clean_name()` - Nomi duplikatlari tekshirish  
✅ Custom `clean_status()` - Faqat haqiqiy status qiymatlarini qabul qilish  
✅ HTML5 attributes auto-generation  
✅ Bootstrap styling ready  

---

## 3. VIEWS (Ko'rinishlar)

### Fayl: `apps/casting/views.py`

#### 3.1 StanokListView
**URL:** `/casting/stanoklar/`  
**Method:** GET  
**Template:** `casting/stanok_list.html`

**Kontekst:**
```python
{
    'stanoklar': QuerySet,          # Filtered Stanok objects
    'q': str,                        # Search query
    'status_f': str,                 # Status filter
    'counts': {
        'total': int,
        'active': int,
        'repair': int,
        'inactive': int,
    },
    'statuses': choices,             # Status options
    'active_nav': 'stanoklar',
}
```

**Xususiyatlari:**
- Qidiruv: Nomi bo'yicha `name__icontains`
- Filter: Status bo'yicha
- Statistika: Har bir holat bo'yicha sonlar
- Pagination: Yo'q (barcha recordlar ko'rsatiladi)

---

#### 3.2 StanokCreateView
**URL:** `/casting/stanoklar/create/`  
**Methods:** GET, POST  
**Template:** `casting/stanok_form.html`

**GET - Kontekst:**
```python
{
    'title': 'Yangi stanok',
    'form': StanokForm(),
    'active_nav': 'stanoklar',
}
```

**POST - Validation:**
- Form validation `form.is_valid()` orqali
- Agar xatolar bo'lsa: Form qaytarish
- Agar OK: Yangi Stanok yaratish va redirect

---

#### 3.3 StanokUpdateView
**URL:** `/casting/stanoklar/<id>/edit/`  
**Methods:** GET, POST  
**Template:** `casting/stanok_form.html`

**GET - Kontekst:**
```python
{
    'title': f'{stanok.name} — tahrirlash',
    'form': StanokForm(instance=stanok),
    'active_nav': 'stanoklar',
}
```

**POST - Behavior:**
- Existing instance bilan form yaratish
- Form.save() orqali update qilish
- Muvaffaq bo'lsa: `stanok_list` ga redirect

---

#### 3.4 StanokDeleteView
**URL:** `/casting/stanoklar/<id>/delete/`  
**Methods:** GET, POST  
**Template:** `casting/stanok_confirm_delete.html`

**GET:** O'chirish tasdiqlash sahifasi  
**POST:** Stanokni database'dan o'chirish

---

## 4. HTML SHABLONLAR

### 4.1 stanok_list.html
**Maqsadi:** Barcha stanoklar ro'yxati, qidiruv va filtrlash

**Maydonchalari:**
- Statistika kartalari (Jami, Faol, Ta'mirda, Faol emas)
- Qidiruv input
- Status filter select
- Jadval: #, Nomi, Holat, Amallar
- Bosh qatorlar uchun boshlang'ich sahifa linki

**Styling:**
```css
/* Responsive grid layout */
.stats-row { grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }

/* Table styling */
.stanok-table { width: 100%; border-collapse: collapse; }
.stanok-table tbody tr:hover td { background: #FAFAFA; }

/* Status badges */
.sp-active { background: #F0FDF4; color: #16A34A; }
.sp-repair { background: #FFF7ED; color: #C2410C; animation: blink; }
.sp-inactive { background: #F1F5F9; color: #64748B; }
```

---

### 4.2 stanok_form.html
**Maqsadi:** Yangi stanok yaratish va mavjud stanokni tahrirlash

**Form maydonchalari:**
1. **Nomi** (TextInput)
   - Placeholder: "masalan: Stanok №1"
   - Required: ✅
   - Autofocus: ✅
   - Error display: ✅

2. **Holat** (RadioSelect)
   - 3 variant: Faol, Ta'mirda, Faol emas
   - Visual indicators: Ranglar va ikonkalar
   - Default: Faol

**Dugmalar:**
- Saqlash (Create/Update uchun)
- Bekor qilish (Back to list)
- O'chirish (Faqat update sahifasida)

**Error Display:**
```html
{% if form.name.errors %}
  <span class="f-err">{{ form.name.errors.0 }}</span>
{% endif %}
```

---

### 4.3 stanok_confirm_delete.html
**Maqsadi:** O'chirish tasdiqlash

**Ma'lumotlar:**
- Stanok nomi
- Model (agar mavjud bo'lsa)
- Serial raqami (agar mavjud bo'lsa)
- Joylashuv (agar mavjud bo'lsa)
- Holat badge

**Xarakat:**
- Confirm dugmasi: POST orqali o'chirish
- Cancel link: Standartlar ro'yxatiga qaytish

---

## 5. URL ROUTING

### Fayl: `apps/casting/urls.py`

```python
path('stanoklar/', views.StanokListView.as_view(), name='stanok_list'),
path('stanoklar/create/', views.StanokCreateView.as_view(), name='stanok_create'),
path('stanoklar/<int:pk>/edit/', views.StanokUpdateView.as_view(), name='stanok_edit'),
path('stanoklar/<int:pk>/delete/', views.StanokDeleteView.as_view(), name='stanok_delete'),
```

---

## 6. ISHLASH JARAYONI (Workflow)

### Create (Yaratish):
1. GET `/stanoklar/create/` → Form ochiladi
2. POST `/stanoklar/create/` → Form validation
   - ✅ Muvaffaq → Yangi Stanok, redirect to list
   - ❌ Xatoli → Form errors ko'rsatish

### Read (O'qish):
1. GET `/stanoklar/` → List, filters, search
2. GET `/stanoklar/<id>/edit/` → Edit form (pre-filled)

### Update (Yangilash):
1. GET `/stanoklar/<id>/edit/` → Form with existing data
2. POST `/stanoklar/<id>/edit/` → Form validation
   - ✅ Muvaffaq → Updated Stanok, redirect to list
   - ❌ Xatoli → Form errors ko'rsatish

### Delete (O'chirish):
1. GET `/stanoklar/<id>/delete/` → Confirmation page
2. POST `/stanoklar/<id>/delete/` → Delete from DB
3. Redirect to list

---

## 7. FOYDALANISH NAMUNALARI

### Python Shell:
```python
from apps.casting.models import Stanok
from apps.casting.forms import StanokForm

# Yangi stanok yaratish
stanok = Stanok.objects.create(name="CNC №1", status="active")

# Form bilan validatsiya
form = StanokForm(data={
    'name': 'Laser №3',
    'status': 'repair'
})
if form.is_valid():
    new_stanok = form.save()
```

### Template (stanok_list.html):
```html
{% for st in stanoklar %}
    <tr>
        <td>{{ st.name }}</td>
        <td>{{ st.get_status_display }}</td>
        <td>
            <a href="{% url 'casting:stanok_edit' st.pk %}">Tahrirlash</a>
            <a href="{% url 'casting:stanok_delete' st.pk %}">O'chirish</a>
        </td>
    </tr>
{% endfor %}
```

---

## 8. SECURITY & BEST PRACTICES

✅ **CSRF Protection**: Barcha POST formalariga `{% csrf_token %}`  
✅ **Permission Checks**: `CastingManagerRequiredMixin` bilan  
✅ **SQL Injection Prevention**: ORM queries (filter, exclude)  
✅ **Data Validation**: Form validation + clean methods  
✅ **Error Handling**: Try-catch with get_object_or_404  
✅ **Messages Framework**: User feedback orqali  

---

## 9. KONFIGURATSIYA

### Admin Panel Integration:
```python
# apps/casting/admin.py
from django.contrib import admin
from .models import Stanok

@admin.register(Stanok)
class StanokAdmin(admin.ModelAdmin):
    list_display = ('name', 'status')
    list_filter = ('status',)
    search_fields = ('name',)
```

---

## 📝 Xulosa

| Komponent | Fayl | Status |
|-----------|------|--------|
| Model | `models.py` | ✅ Complete |
| Form | `forms.py` | ✅ Complete |
| Views | `views.py` | ✅ Updated |
| Templates | `templates/casting/*.html` | ✅ Updated |
| URLs | `urls.py` | ✅ Configured |
| Admin | `admin.py` | ⚠️ Optional |

---

**Tahrirlandi:** 2026-04-24  
**Versiya:** 1.0  
**Til:** Uzbek (O'zbek)
