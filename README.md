# Premium Padel

אתר לרישום ותפעול טורנירי פאדל: הרשמת משתמשים, הרשמה לטורנירים כזוגות, הגרלת בתים אוטומטית, מעקב אחרי תוצאות ועלייה לשלב הנוקאאוט עד לכתרת זוג מנצח.

## פריסה חינמית (Supabase + Render)

### 1. Supabase (בסיס נתונים)
1. היכנס ל-https://supabase.com וצור פרויקט חדש (חינמי).
2. בתפריט **SQL Editor** הרץ את התוכן של `padel_setup.sql` שבתיקייה הזו — זה יוצר את כל הטבלאות.
3. בתפריט **Project Settings → API** העתק:
   - `Project URL` → זה יהיה `SUPABASE_URL`
   - `service_role` / `secret` key (בסודי, שרת בלבד!) → זה יהיה `SUPABASE_SERVICE_KEY`

### 2. GitHub
1. צור ריפו חדש (למשל `premium-padel`) והעלה אליו את כל התיקייה הזו.

### 3. Render (שרת)
1. היכנס ל-https://render.com, **New → Web Service**, חבר את הריפו מ-GitHub.
2. Build command: (ריק, לא נדרש) · Start command: נלקח אוטומטית מה-`Procfile`.
3. הגדר את משתני הסביבה הבאים ב-**Environment**:
   - `SUPABASE_URL` — מ-Supabase שלב 1
   - `SUPABASE_SERVICE_KEY` — מ-Supabase שלב 1 (ה-service_role, לא ה-anon key)
   - `SECRET_KEY` — כל מחרוזת אקראית ארוכה (למשל: `openssl rand -hex 32`)
   - `ADMIN_USERNAME` — שם המשתמש שתירשם איתו, יקבל אוטומטית הרשאות ניהול
4. פרסם. השירות החינמי של Render "נרדם" אחרי חוסר פעילות ומתעורר תוך כמה שניות בבקשה הבאה — תקין ל-MVP.

### 4. שימוש ראשוני
1. היכנס לאתר, לחץ "הרשמה" והירשם עם שם המשתמש שהגדרת ב-`ADMIN_USERNAME` — תקבל אוטומטית הרשאות אדמין.
2. כאדמין תוכל ליצור טורניר חדש, להוסיף זוגות ישירות, ולנהל את הטורניר עד הסוף.

## הרצה מקומית

```bash
pip install -r requirements.txt
export SUPABASE_URL=...
export SUPABASE_SERVICE_KEY=...
export SECRET_KEY=dev-secret
export ADMIN_USERNAME=admin
python app.py
```

השרת יעלה בכתובת http://localhost:5000
