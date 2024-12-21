import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

# אינדיקטורים טכניים
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
from ta.volatility import BollingerBands

# ----------------------------------------------------
# 1) פונקציית fetch_stock_data (בעברית)
# ----------------------------------------------------
def fetch_stock_data(stock_symbol, period="2y"):
    """
    פונקציה לשליפת נתוני מניה בעזרת yfinance (ברירת מחדל שנתיים אחורה).
    מחזירה: DataFrame היסטורי + מילון סיכום מחירים (אחרון, לפני חודש/שנה).
    """
    try:
        ticker_obj = yf.Ticker(stock_symbol)
        hist_data = ticker_obj.history(period=period)

        if hist_data.empty:
            return {"Error": f"לא נמצאו נתונים עבור הסימבול {stock_symbol}."}

        # מחיר סגירה אחרון + תאריך
        most_recent_close = round(hist_data['Close'].iloc[-1], 2)
        most_recent_date = hist_data.index[-1]

        def get_closing_price(reference_date):
            try:
                # אם התאריך המבוקש לפני הטווח ההיסטורי הקיים, נחזיר None
                if reference_date < hist_data.index[0]:
                    return None, None
                nearest_idx = hist_data.index.get_indexer([reference_date], method='nearest')[0]
                nearest_date = hist_data.index[nearest_idx]
                price = round(hist_data.loc[nearest_date]['Close'], 2)
                return price, nearest_date
            except:
                return None, None

        # פונקציה פנימית לחישוב תאריך "חודש/שנה אחורה" עם טיפול בקצוות
        def adjust_date_for_months(date, months):
            target_month = (date.month - months - 1) % 12 + 1
            target_year = date.year + ((date.month - months - 1) // 12)
            try:
                return date.replace(year=target_year, month=target_month)
            except ValueError:
                # אם החודש היעד לא קיים (למשל 30 בפברואר), נבחר ביום האחרון של אותו חודש
                last_day_of_month = (
                    date.replace(day=1, month=target_month, year=target_year)
                    + timedelta(days=31)
                ).replace(day=1) - timedelta(days=1)
                return last_day_of_month

        # חישוב תאריכי רפרנס
        one_month_ago = adjust_date_for_months(most_recent_date, 1)
        one_year_ago = adjust_date_for_months(most_recent_date, 12)

        # מחירים עבור התאריכים המבוקשים
        price_one_month_ago, date_one_month_ago = get_closing_price(one_month_ago)
        price_one_year_ago, date_one_year_ago = get_closing_price(one_year_ago)

        summary_data = {
            "Most Recent Close": (most_recent_close, most_recent_date.strftime("%Y-%m-%d")),
            "One Month Ago": (
                price_one_month_ago,
                date_one_month_ago.strftime("%Y-%m-%d") if date_one_month_ago else None
            ),
            "One Year Ago": (
                price_one_year_ago,
                date_one_year_ago.strftime("%Y-%m-%d") if date_one_year_ago else None
            ),
        }

        return {
            "historical_data": hist_data,
            "summary": summary_data
        }
    except Exception as e:
        return {"Error": str(e)}

# ----------------------------------------------------
# 2) פונקציית analyze_dca_recommendation (בעברית)
# ----------------------------------------------------
def analyze_dca_recommendation(symbol, quantity, avg_cost, stock_data):
    """
    ניתוח מבוסס אינדיקטורים טכניים (RSI, SMA 50/200, MACD, Bollinger Bands) ומחיר ממוצע אישי,
    והפקת המלצה בסיסית האם להגדיל/להפחית/להמתין עם DCA.
    """
    if "Error" in stock_data:
        return [f"לא ניתן לתת המלצה עבור {symbol}: {stock_data['Error']}"]

    hist = stock_data["historical_data"]
    summary = stock_data["summary"]

    if hist.empty:
        return ["לא נמצאו נתונים היסטוריים עבור הסימבול."]

    # המחיר האחרון
    most_recent_close, _ = summary["Most Recent Close"]

    # חישוב אינדיקטורים
    hist['RSI'] = RSIIndicator(close=hist['Close'], window=14).rsi()
    hist['SMA_50'] = SMAIndicator(close=hist['Close'], window=50).sma_indicator()
    hist['SMA_200'] = SMAIndicator(close=hist['Close'], window=200).sma_indicator()

    macd_obj = MACD(close=hist['Close'], window_slow=26, window_fast=12, window_sign=9)
    hist['MACD'] = macd_obj.macd()
    hist['MACD_Signal'] = macd_obj.macd_signal()
    hist['MACD_Hist'] = macd_obj.macd_diff()

    bb_obj = BollingerBands(close=hist['Close'], window=20, window_dev=2)
    hist['BB_High'] = bb_obj.bollinger_hband()
    hist['BB_Low'] = bb_obj.bollinger_lband()

    # הנתונים האחרונים (שורה אחרונה)
    last_row = hist.iloc[-1]
    rsi_val = last_row['RSI']
    sma50_val = last_row['SMA_50']
    sma200_val = last_row['SMA_200']
    macd_val = last_row['MACD']
    macd_signal = last_row['MACD_Signal']
    bb_high = last_row['BB_High']
    bb_low = last_row['BB_Low']

    # פונקציית חישוב אחוז שינוי
    def percent_change(curr, ref):
        if curr is None or ref is None or ref == 0:
            return None
        return round((curr - ref) / ref * 100, 2)

    # הפרש מול המחיר הממוצע שלנו
    cost_diff_percent = percent_change(most_recent_close, avg_cost)
    # מחירים היסטוריים להשוואה
    one_month_ago_price, _ = summary["One Month Ago"]
    one_year_ago_price, _ = summary["One Year Ago"]

    monthly_change = percent_change(most_recent_close, one_month_ago_price)
    yearly_change = percent_change(most_recent_close, one_year_ago_price)

    recommendations = []

    # 1) יחס למחיר ממוצע אישי (avg_cost)
    if cost_diff_percent is not None:
        if cost_diff_percent > 10:
            recommendations.append("המחיר הנוכחי גבוה מעלות הקנייה ביותר מ־10% => אולי להיזהר מלבצע DCA.")
        elif cost_diff_percent < -10:
            recommendations.append("המחיר הנוכחי נמוך מעלות הקנייה ביותר מ־10% => ייתכן שזו הזדמנות להוזיל עלויות (DCA).")
        else:
            recommendations.append("המחיר הנוכחי קרוב לעלות הקנייה => אפשר לשקול להמשיך ב־DCA רגיל.")
    else:
        recommendations.append("לא ניתן לחשב יחס מול המחיר הממוצע שלך.")

    # 2) מגמת שינוי חודשית/שנתית
    if monthly_change is not None:
        if monthly_change > 0:
            recommendations.append("עלייה במחיר בחודש האחרון.")
        else:
            recommendations.append("ירידה במחיר בחודש האחרון.")
    if yearly_change is not None:
        if yearly_change > 0:
            recommendations.append("עלייה במחיר בשנה האחרונה.")
        else:
            recommendations.append("ירידה במחיר בשנה האחרונה.")

    # 3) RSI
    if rsi_val is not None:
        if rsi_val < 30:
            recommendations.append("RSI מתחת ל־30 => 'אובר-סולד' => ייתכן שכדאי לשקול קנייה.")
        elif rsi_val > 70:
            recommendations.append("RSI מעל 70 => 'אובר-בויט' => ייתכן שכדאי להימנע מהגדלה.")
        else:
            recommendations.append(f"RSI ברמה נייטרלית ({round(rsi_val,2)}).")
    else:
        recommendations.append("לא זמין מידע RSI.")

    # 4) ממוצעים נעים 50/200
    if sma50_val and sma200_val:
        if sma50_val > sma200_val:
            recommendations.append("SMA50 > SMA200 => Golden Cross => מגמה חיובית ארוכה.")
        else:
            recommendations.append("SMA50 < SMA200 => Death Cross => מגמה שלילית ארוכה.")

    # 5) MACD
    if macd_val is not None and macd_signal is not None:
        if macd_val > macd_signal:
            recommendations.append("MACD מעל ה־Signal => מומנטום חיובי לטווח קצר/בינוני.")
        else:
            recommendations.append("MACD מתחת ל־Signal => מומנטום שלילי לטווח קצר/בינוני.")
        if macd_val > 0:
            recommendations.append("MACD חיובי => מחזק סנטימנט חיובי.")
        else:
            recommendations.append("MACD שלילי => מחזק סנטימנט שלילי.")

    # 6) Bollinger Bands
    if bb_high and bb_low and most_recent_close:
        if most_recent_close > bb_high:
            recommendations.append("המחיר כעת מעל רצועת בולינגר העליונה => מצב 'אובר-בויט'.")
        elif most_recent_close < bb_low:
            recommendations.append("המחיר כעת מתחת לרצועת בולינגר התחתונה => מצב 'אובר-סולד'.")
        else:
            recommendations.append("המחיר נמצא בתוך רצועות Bollinger => אין איתות קיצוני.")

    return recommendations

# ----------------------------------------------------
# 3) אפליקציית Streamlit בתצוגה RTL עם המלצות בשורות נפרדות
# ----------------------------------------------------
def main():
    # הגדרת כותרת וחלון
    st.set_page_config(page_title="מערכת המלצות DCA", layout="wide")

    # הגדרת כיוון RTL באמצעות CSS
    st.markdown("""
    <style>
    /* הגדרת כיוון כללית לגוף האפליקציה */
    .main, .block-container {
        direction: rtl;
        text-align: right;
    }
    /* כותרת עליונה (title) */
    .css-18e3th9 {
        direction: rtl;
        text-align: right;
    }
    /* אזורים פנימיים כמו text_input וכד' */
    .css-1rle71b {
        direction: rtl;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("מערכת המלצות DCA")
    st.write("""
    אפליקציית דוגמה המאפשרת להזין סימבול מניה, כמות ומחיר ממוצע בתיק – ומציגה 
    ניתוח טכני בסיסי בעזרת ספריית `ta` ונתונים מ־yfinance.
    """)

    # **הוספת הסברים והגדרות**
    with st.expander("הסברים על אינדיקטורים"):
        st.markdown("""
        ### **RSI (Relative Strength Index)**
        **RSI** הוא אינדיקטור מוניטורי (Momentum Indicator) שמודד את המהירות והשינוי של תנועות המחיר של נכס פיננסי. הערכים נעים בין 0 ל-100:
        - **RSI מעל 70**: מצב **אובר-בויט** (Overbought) – המחיר עלה במהירות ובכמות, יתכן שהוא עלה מעבר לערכו האמיתי ועלול להתקיים תיקון במחיר.
        - **RSI מתחת ל-30**: מצב **אובר-סולד** (Oversold) – המחיר ירד במהירות ובכמות, יתכן שהוא נמוך מדי ועלול להתחיל לעלות שוב.
        - **RSI בין 30 ל-70**: מצב נייטרלי – אין איתות חזק לקנייה או מכירה.

        ### **SMA (Simple Moving Average)**
        **ממוצע נע פשוט (SMA)** הוא אינדיקטור שמחשב את הממוצע של מחירי הנכס לאורך תקופה מוגדרת:
        - **SMA 50**: ממוצע נע של 50 ימים – משמש לזיהוי מגמות קצרות ובינוניות.
        - **SMA 200**: ממוצע נע של 200 ימים – משמש לזיהוי מגמות ארוכות טווח.
        - **Golden Cross**: כאשר SMA 50 עולה מעל SMA 200 – סימן למגמה חיובית ארוכת טווח.
        - **Death Cross**: כאשר SMA 50 יורד מתחת SMA 200 – סימן למגמה שלילית ארוכת טווח.

        ### **MACD (Moving Average Convergence Divergence)**
        **MACD** הוא אינדיקטור שמודד את ההבדל בין שני ממוצעים נעים של מחירים:
        - **MACD**: הפרש בין ממוצע נע מהיר (Fast) לבין ממוצע נע איטי (Slow).
        - **MACD Signal**: ממוצע נע של MACD עצמו.
        - **MACD Hist**: ההפרש בין MACD ל-MACD Signal.
        - **התייחסות**:
            - **MACD מעל ה-Signal**: מומנטום חיובי לטווח קצר/בינוני.
            - **MACD מתחת ל-Signal**: מומנטום שלילי לטווח קצר/בינוני.

        ### **Bollinger Bands**
        **רצועות בולינגר** הן סטיות תקן מעל ומתחת לממוצע נע של מחירי הנכס:
        - **BB High**: רצועת העליונה.
        - **BB Low**: רצועת התחתונה.
        - **התייחסות**:
            - **מחיר מעל BB High**: מצב **אובר-בויט** לטווח קצר.
            - **מחיר מתחת BB Low**: מצב **אובר-סולד** לטווח קצר.
            - **מחיר בתוך הרצועות**: אין איתות קיצוני לטווח קצר.

        ### **המלצות אסטרטגיית DCA בהתבסס על אינדיקטורים**
        - **RSI מתחת ל-30**: שקול להגדיל את ההשקעה (DCA), שכן המחיר נמוך ואולי יתחיל לעלות.
        - **RSI מעל 70**: שקול להימנע מהגדלת ההשקעה, שכן המחיר גבוה מדי ואולי יתקיים תיקון.
        - **Golden Cross (SMA 50 מעל SMA 200)**: מצב חיובי ארוך טווח – אפשר לשקול להגדיל את ההשקעה.
        - **Death Cross (SMA 50 מתחת SMA 200)**: מצב שלילי ארוך טווח – שקול להימנע מהגדלת ההשקעה.
        - **MACD מעל Signal**: מומנטום חיובי – אפשר לשקול להגדיל את ההשקעה.
        - **MACD מתחת Signal**: מומנטום שלילי – שקול להימנע מהגדלת ההשקעה.
        - **מחיר מעל Bollinger High**: מצב אובר-בויט קצר טווח – שקול להימנע מהגדלת ההשקעה.
        - **מחיר מתחת Bollinger Low**: מצב אובר-סולד קצר טווח – שקול להגדיל את ההשקעה.

        **חשוב לזכור**: אינדיקטורים הם כלי עזר נוסף לקבלת החלטות השקעה. מומלץ לשלב אותם עם ניתוחים אחרים ולהתייעץ עם אנשי מקצוע לפני קבלת החלטות השקעה.
        """)

    # קליטת פרמטרים מהמשתמש (RTL)
    symbol = st.text_input("הקלד סימבול (למשל: AAPL, TSLA וכו')", "AAPL")
    quantity = st.number_input("כמות מניות בתיק", min_value=0, value=10)
    avg_cost = st.number_input("מחיר ממוצע בתיק", min_value=0.0, value=100.0)

    # כפתור להרצת ניתוח
    if st.button("בצע ניתוח DCA"):
        data = fetch_stock_data(symbol, period="2y")
        if "Error" in data:
            st.error(data["Error"])
        else:
            st.subheader("סיכום מחירי רפרנס")
            summary = data["summary"]
            st.write(f"**מחיר סגירה אחרון**: {summary['Most Recent Close'][0]} (תאריך: {summary['Most Recent Close'][1]})")
            st.write(f"**מחיר לפני חודש**: {summary['One Month Ago'][0]}")
            st.write(f"**מחיר לפני שנה**: {summary['One Year Ago'][0]}")

            # הפקת המלצה
            recommendations = analyze_dca_recommendation(symbol, quantity, avg_cost, data)
            st.subheader("המלצות:")
            if recommendations:
                # המרת רשימת ההמלצות לרשימה בפורמט Markdown עם נקודות
                markdown_recommendations = "\n".join([f"- {rec}" for rec in recommendations])
                st.markdown(markdown_recommendations)
            else:
                st.write("אין המלצות זמינות.")

            # תצוגה גרפית של המחירים ההיסטוריים
            hist_df = data["historical_data"]
            st.subheader("גרף מחירי סגירה לאורך זמן")
            st.line_chart(hist_df['Close'])

# הרצת האפליקציה
if __name__ == "__main__":
    main()
#  streamlit run stocks-dca.py
