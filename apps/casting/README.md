# 📖 STANOK MODEL - TEZKOR QO'LLANMA

## ✅ Bajarilgan Ishlar

| Item | Fayl | Status | Izoh |
|------|------|--------|------|
| **1. Model** | `models.py` | ✅ | 2 ta maydoni: `name`, `status` |
| **2. Django Form** | `forms.py` | ✅ **YANGI** | Validation + clean methods |
| **3. Views (CRUD)** | `views.py` | ✅ **YANGILANDI** | Form klasi bilan integratsiya |
| **4. List Template** | `stanok_list.html` | ✅ | Qidiruv + Filter + Statistika |
| **5. Form Template** | `stanok_form.html` | ✅ **YANGILANDI** | Form fields bilan integratsiya |
| **6. Delete Template** | `stanok_confirm_delete.html` | ✅ | Confirmation page |
| **7. URLs** | `urls.py` | ✅ | 4 ta route (list, create, edit, delete) |
| **8. Dokumentatsiya** | `STANOK_MODEL_DOCUMENTATION.md` | ✅ **YANGI** | To'liq hujjat |
| **9. API Namunalari** | `STANOK_API_EXAMPLES.md` | ✅ **YANGI** | 10+ amaliy misol |

---

## 🗂️ Fayl Strukturasi

```
apps/casting/
├── models.py                          # Stanok model
├── forms.py                          # ✨ YANGI: StanokForm
├── views.py                          # ✨ YANGILANDI: Views
├── urls.py                           # URL routing
├── admin.py                          # (Optional)
├── templates/casting/
│   ├── stanok_list.html             # Ro'yxat
│   ├── stanok_form.html             # ✨ YANGILANDI: Create/Edit
│   ├── stanok_confirm_delete.html   # O'chirish
│   └── base.html                    # Base template
├── STANOK_MODEL_DOCUMENTATION.md    # 📖 YANGI
└── STANOK_API_EXAMPLES.md          # 📖 YANGI
```

---

## 🎯 MODEL TUZILISHI

### Fields:
```python
- id: AutoField (PK)
- name: CharField(max_length=200) [Majburiy]
- status: CharField(choices) [Default: ACTIVE]
```

### Status Options:
| Value | Label |
|-------|-------|
| `active` | ✅ Faol |
| `repair` | 🔧 Ta'mirda |
| `inactive` | ❌ Faol emas |

---

## 📝 FORM VALIDATSIYA

```python
class StanokForm(forms.ModelForm):
    ✅ HTML5 attributes auto-generation
    ✅ Custom name validation (uniqueness)
    ✅ Custom status validation
    ✅ Bootstrap styling ready
```

**Validation Rules:**
- `name`: Majburiy, unikalli, 1-200 belgi
- `status`: Faqat [active, repair, inactive]

---

## 🌐 VIEWS (CRUD)

### 1️⃣ StanokListView
**URL:** `GET /casting/stanoklar/`
- Qidiruv: Nomi bo'yicha
- Filter: Status bo'yicha
- Statistika: Har bir holatning soni
- Amallar: Tahrirlash, O'chirish

### 2️⃣ StanokCreateView
**URL:** `GET/POST /casting/stanoklar/create/`
- Form renderelenadi (GET)
- Validation + Save (POST)
- Muvaffaq bo'lsa: Redirect to list

### 3️⃣ StanokUpdateView
**URL:** `GET/POST /casting/stanoklar/<id>/edit/`
- Form pre-filled with data (GET)
- Validation + Update (POST)
- Muvaffaq bo'lsa: Redirect to list

### 4️⃣ StanokDeleteView
**URL:** `GET/POST /casting/stanoklar/<id>/delete/`
- Confirmation page (GET)
- Delete + Redirect (POST)

---

## 🎨 TEMPLATE'LAR

### ✅ stanok_list.html
```
┌─────────────────────────────────────┐
│ Statistika Kartalar                 │
│ [Jami] [Faol] [Ta'mirda] [Emas]    │
├─────────────────────────────────────┤
│ Qidiruv Input | Status Select       │
├─────────────────────────────────────┤
│ Jadval:                             │
│ # | Nomi | Holat | Amallar        │
├─────────────────────────────────────┤
│ [Yangi stanok qo'shish]             │
└─────────────────────────────────────┘
```

### ✅ stanok_form.html
```
┌─────────────────────────────────────┐
│ Yangi Stanok / Tahrirlash           │
├─────────────────────────────────────┤
│ [Nomi] TextInput (required)         │
│                                     │
│ [Holat]                             │
│ ○ Faol  ○ Ta'mirda  ○ Faol emas    │
├─────────────────────────────────────┤
│ [Saqlash] [Bekor qilish]            │
│ [O'chirish] (faqat update)          │
└─────────────────────────────────────┘
```

### ✅ stanok_confirm_delete.html
```
┌─────────────────────────────────────┐
│ ⚠️ Stanokni o'chirish               │
├─────────────────────────────────────┤
│ Ma'lumotlar:                        │
│ Nomi: {{ object.name }}             │
│ Holat: {{ get_status_display() }}   │
├─────────────────────────────────────┤
│ [O'chirish] [Bekor qilish]          │
└─────────────────────────────────────┘
```

---

## 🚀 FOYDALANISH

### Terminal / Python Shell:
```bash
# Virtual environment
python manage.py shell

# Model queries
from apps.casting.models import Stanok
stanok = Stanok.objects.create(name="CNC №1", status="active")

# Form
from apps.casting.forms import StanokForm
form = StanokForm(data={'name': 'Laser', 'status': 'repair'})
if form.is_valid():
    stanok = form.save()
```

### Web URLs:
```
🌐 GET  /casting/stanoklar/                 # List
🌐 GET  /casting/stanoklar/create/          # Create Form
🌐 POST /casting/stanoklar/create/          # Create
🌐 GET  /casting/stanoklar/<id>/edit/       # Edit Form
🌐 POST /casting/stanoklar/<id>/edit/       # Update
🌐 GET  /casting/stanoklar/<id>/delete/     # Delete Confirm
🌐 POST /casting/stanoklar/<id>/delete/     # Delete
```

---

## 🔐 SECURITY

✅ CSRF Protection (`{% csrf_token %}`)  
✅ Permission Checks (`CastingManagerRequiredMixin`)  
✅ SQL Injection Prevention (ORM queries)  
✅ Data Validation (Form validation)  
✅ get_object_or_404 (Safe queries)  

---

## 📊 DATABASE

```sql
-- Migration yaratish (auto)
python manage.py makemigrations casting

-- Database'ga qo'llash
python manage.py migrate

-- Table struktura:
CREATE TABLE casting_stanok (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' NOT NULL
);

-- Indexes (auto)
CREATE INDEX casting_stanok_name ON casting_stanok(name);
CREATE INDEX casting_stanok_status ON casting_stanok(status);
```

---

## 🧪 TESTING COMMANDS

```bash
# Model testi
python manage.py shell
>>> from apps.casting.models import Stanok
>>> Stanok.objects.all().count()
>>> s = Stanok.objects.create(name="Test", status="active")
>>> s.get_status_display()

# Form testi
>>> from apps.casting.forms import StanokForm
>>> form = StanokForm(data={'name': 'Test2', 'status': 'repair'})
>>> form.is_valid()

# Server testi
python manage.py runserver
# http://localhost:8000/casting/stanoklar/
```

---

## 📋 CHECKLIST

- [x] Model yaratildi
- [x] Form klasi yaratildi va validatsiya qo'shildi
- [x] Views modernizatsiya qilindi (Form orqali)
- [x] Templates Form klasiga moslandi
- [x] CRUD operatsiyalari to'liq
- [x] Qidiruv va filter mexanizmi
- [x] Error handling va messages
- [x] Permission checks
- [x] To'liq dokumentatsiya
- [x] Amaliy API namunalari

---

## 🔗 RELATED FILES

| Fayl | Maqsadi |
|------|---------|
| `apps/casting/models.py` | Model definition |
| `apps/casting/forms.py` | Form validation |
| `apps/casting/views.py` | CRUD views |
| `apps/casting/urls.py` | URL routing |
| `apps/casting/templates/` | HTML templates |
| `config/urls.py` | Main URL config |
| `apps/order/views/mixins.py` | Permission mixins |

---

## 💡 NEXT STEPS (Optional)

1. **Admin Panel Setup**
   ```python
   # apps/casting/admin.py
   @admin.register(Stanok)
   class StanokAdmin(admin.ModelAdmin):
       list_display = ('name', 'status')
       list_filter = ('status',)
       search_fields = ('name',)
   ```

2. **API (Django REST Framework)**
   - Serializers
   - ViewSets
   - Routers

3. **Testing**
   - Unit tests
   - Integration tests
   - Form tests

4. **Caching**
   - Redis caching
   - Query optimization

5. **Signals**
   - Post-save hooks
   - Audit logging

---

## 📚 DOKUMENTATSIYA

1. **STANOK_MODEL_DOCUMENTATION.md** - To'liq hujjat
2. **STANOK_API_EXAMPLES.md** - 10+ amaliy misol

---

## 👨‍💻 DEVELOPER NOTES

**Yangiliklari:**
- Form class bilan automatic validation
- Template'lar Form rendering bilan
- Views refactored for cleaner code
- Better error handling and messages
- Fully documented with examples

**Best Practices:**
- DRY (Don't Repeat Yourself) - Form klasi
- Separation of concerns - Views/Templates/Forms
- Semantic HTML - Accessible templates
- Security first - CSRF, permission checks

---

## 📞 SUPPORT

Agar savollari bo'lsa, quyidagi fayllarni ko'ring:
- `STANOK_MODEL_DOCUMENTATION.md` - To'liq tushuntirishlar
- `STANOK_API_EXAMPLES.md` - Kod namunalari
- Django Official Docs: https://docs.djangoproject.com

---

**Status:** ✅ Complete  
**Versiya:** 1.0  
**Oxirgi tahrir:** 2026-04-24  
**Til:** Uzbek (O'zbek)  

---

🎉 **Barcha tayyor! Bu endi production-ready code.**
