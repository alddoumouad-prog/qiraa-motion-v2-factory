# نشر المكتبة على GitHub

المستودع جاهز للنشر. لا يتضمن هذا الملف أي حساب أو رمز وصول، لذلك يتم الربط بحسابك أنت.

## المتطلبات

- Git.
- حساب GitHub.
- GitHub CLI (`gh`) مسجل الدخول، أو رابط مستودع فارغ أنشأته من حسابك.

## النشر باستخدام GitHub CLI

```bash
git init
git add .
git commit -m "Release Qiraa Tactile UI SFX v1.0.0"
git branch -M main
gh repo create qiraa-tactile-ui-sfx --public --source=. --push
```

## إنشاء إصدار رقمي

```bash
git tag -a v1.0.0 -m "Qiraa Tactile UI SFX v1.0.0"
git push origin v1.0.0
```

سيقوم workflow تلقائيًا بإنشاء Release وإرفاق ملف ZIP.

## تفعيل المشغّل عبر GitHub Pages

1. افتح إعدادات المستودع ثم Pages.
2. اجعل المصدر **GitHub Actions**.
3. workflow الموجود في `.github/workflows/pages.yml` سينشر `index.html` والأصوات.
4. بعد نجاح النشر ستجد رابط الصفحة في تبويب Actions أو إعدادات Pages.

## قبل النشر

```bash
python tools/validate_library.py
```

يجب أن يظهر `status: passed` مع 120 صوتًا و12 عائلة وصفر تكرارات.
