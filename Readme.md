# מערכת המלצות DCA - RTL

אפליקציית Streamlit שמספקת המלצות על אסטרטגיית **DCA (Dollar Cost Averaging)** בעזרת ניתוח טכני של מניות באמצעות אינדיקטורים כמו RSI, SMA, MACD ורצועות Bollinger. האפליקציה מאפשרת להזין סימבול מניה, כמות ומחיר ממוצע בתיק, ומציגה המלצות מבוססות על הנתונים והאינדיקטורים.

## 📋 תכונות

- **שליפת נתוני מניה**: שימוש ב־yfinance לשליפת נתוני מחירי מניה היסטוריים.
- **ניתוח טכני**: חישוב אינדיקטורים טכניים כמו RSI, SMA 50/200, MACD ורצועות Bollinger.
- **המלצות DCA**: הפקת המלצות מבוססות על הערכים של האינדיקטורים והנתונים האישיים שלך.
- **ממשק משתמש בעברית**: האפליקציה מוצגת מימין לשמאל (RTL) עם הסברים בעברית.
- **גרפים אינטראקטיביים**: הצגת גרפים של מחירי סגירה לאורך זמן.

## 📦 התקנה

כדי להריץ את האפליקציה מקומית, בצע את השלבים הבאים:

1. **שמור את הקבצים**:
   - `stocks-dca.py`: קובץ הסקריפט הראשי.
   - `requirements.txt`: קובץ התלויות.
   - `README.md`: קובץ התיעוד.

2. **התקן את התלויות**:
   ודא שיש לך Python מותקן במחשב שלך. לאחר מכן, התקן את הספריות הדרושות באמצעות הפקודה:

   ```bash
   pip install -r requirements.txt
