import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

# אינדיקטורים טכניים
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
from ta.volatility import BollingerBands

# ----------------------------------------------------
# פונקציית fetch_stock_data (בעברית)
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
                if reference_date < hist_data.index[0]:
                    return None, None
                nearest_idx = hist_data.index.get_indexer([reference_date], method='nearest')[0]
                nearest_date = hist_data.index[nearest_idx]
                price = round(hist_data.loc[nearest_date]['Close'], 2)
                return price, nearest_date
            except:
                return None, None

        def adjust_date_for_months(date, months):
            target_month = (date.month - months - 1) % 12 + 1
            target_year = date.year + ((date.month - months - 1) // 12)
            try:
                return date.replace(year=target_year, month=target_month)
            except ValueError:
                last_day_of_month = (
                    date.replace(day=1, month=target_month, year=target_year)
                    + timedelta(days=31)
                ).replace(day=1) - timedelta(days=1)
                return last_day_of_month

        one_month_ago = adjust_date_for_months(most_recent_date, 1)
        one_year_ago = adjust_date_for_months(most_recent_date, 12)

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
# פונקציית analyze_dca_recommendation
# ----------------------------------------------------
def analyze_dca_recommendation(symbol, quantity, avg_cost, monthly_investment, stock_data):
    if "Error" in stock_data:
        return [f"לא ניתן לתת המלצה עבור {symbol}: {stock_data['Error']}"], None

    hist = stock_data["historical_data"]
    summary = stock_data["summary"]

    if hist.empty:
        return ["לא נמצאו נתונים היסטוריים עבור הסימבול."], None

    most_recent_close, _ = summary["Most Recent Close"]

    hist['RSI'] = RSIIndicator(close=hist['Close'], window=14).rsi()
    hist['SMA_50'] = SMAIndicator(close=hist['Close'], window=50).sma_indicator()
    hist['SMA_200'] = SMAIndicator(close=hist['Close'], window=200).sma_indicator()

    macd_obj = MACD(close=hist['Close'], window_slow=26, window_fast=12, window_sign=9)
    hist['MACD'] = macd_obj.macd()
    hist['MACD_Signal'] = macd_obj.macd_signal()

    bb_obj = BollingerBands(close=hist['Close'], window=20, window_dev=2)
    hist['BB_High'] = bb_obj.bollinger_hband()
    hist['BB_Low'] = bb_obj.bollinger_lband()

    last_row = hist.iloc[-1]
    rsi_val = last_row['RSI']
    sma50_val = last_row['SMA_50']
    sma200_val = last_row['SMA_200']
    macd_val = last_row['MACD']
    macd_signal = last_row['MACD_Signal']
    bb_high = last_row['BB_High']
    bb_low = last_row['BB_Low']

    def percent_change(curr, ref):
        if curr is None or ref is None or ref == 0:
            return None
        return round((curr - ref) / ref * 100, 2)

    cost_diff_percent = percent_change(most_recent_close, avg_cost)

    recommendations = []
    total_investment = quantity * avg_cost

    if cost_diff_percent is not None:
        if cost_diff_percent > 10:
            recommendations.append("המחיר הנוכחי גבוה מעלות הקנייה ביותר מ־10% => אולי להיזהר מלבצע DCA.")
            recommended_investment = 0
        elif cost_diff_percent < -10:
            recommendations.append("המחיר הנוכחי נמוך מעלות הקנייה ביותר מ־10% => ייתכן שזו הזדמנות להוזיל עלויות (DCA).")
            recommended_investment = monthly_investment * 1.5
        else:
            recommendations.append("המחיר הנוכחי קרוב לעלות הקנייה => אפשר לשקול להמשיך ב־DCA רגיל.")
            recommended_investment = monthly_investment
    else:
        recommendations.append("לא ניתן לחשב יחס מול המחיר הממוצע שלך.")
        recommended_investment = monthly_investment

    if rsi_val is not None:
        if rsi_val < 30:
            recommendations.append("RSI מתחת ל־30 => 'אובר-סולד' => ייתכן שכדאי לשקול קנייה.")
        elif rsi_val > 70:
            recommendations.append("RSI מעל 70 => 'אובר-בויט' => ייתכן שכדאי להימנע מהגדלה.")
        else:
            recommendations.append(f"RSI ברמה נייטרלית ({round(rsi_val, 2)}).")

    if sma50_val and sma200_val:
        if sma50_val > sma200_val:
            recommendations.append("SMA50 > SMA200 => Golden Cross => מגמה חיובית ארוכה.")
        else:
            recommendations.append("SMA50 < SMA200 => Death Cross => מגמה שלילית ארוכה.")

    if macd_val is not None and macd_signal is not None:
        if macd_val > macd_signal:
            recommendations.append("MACD מעל ה־Signal => מומנטום חיובי לטווח קצר/בינוני.")
        else:
            recommendations.append("MACD מתחת ל־Signal => מומנטום שלילי לטווח קצר/בינוני.")
        if macd_val > 0:
            recommendations.append("MACD חיובי => מחזק סנטימנט חיובי.")
        else:
            recommendations.append("MACD שלילי => מחזק סנטימנט שלילי.")

    if bb_high and bb_low and most_recent_close:
        if most_recent_close > bb_high:
            recommendations.append("המחיר כעת מעל רצועת בולינגר העליונה => מצב 'אובר-בויט'.")
        elif most_recent_close < bb_low:
            recommendations.append("המחיר כעת מתחת לרצועת בולינגר התחתונה => מצב 'אובר-סולד'.")
        else:
            recommendations.append("המחיר נמצא בתוך רצועות Bollinger => אין איתות קיצוני.")

    return recommendations, recommended_investment

# ----------------------------------------------------
# אפליקציית Streamlit
# ----------------------------------------------------
def main():
    st.set_page_config(page_title="מערכת המלצות DCA", layout="wide")

    st.markdown("""
    <style>
    .main, .block-container {
        direction: rtl;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("מערכת המלצות DCA")

    symbol = st.text_input("הקלד סימבול (למשל: AAPL, TSLA וכו')", "AAPL")
    quantity = st.number_input("כמות מניות בתיק", min_value=0, value=10)
    avg_cost = st.number_input("מחיר ממוצע בתיק", min_value=0.0, value=100.0)
    monthly_investment = st.number_input("כמה אתה משקיע בכל חודש?", min_value=0.0, value=500.0)

    if st.button("בצע ניתוח DCA"):
        data = fetch_stock_data(symbol, period="2y")
        if "Error" in data:
            st.error(data["Error"])
        else:
            recommendations, recommended_investment = analyze_dca_recommendation(
                symbol, quantity, avg_cost, monthly_investment, data
            )

            st.subheader("המלצות: ")
            st.write("\n\n".join(recommendations))

            if recommended_investment:
                st.subheader("השקעה חודשית מומלצת:")
                st.write(f"₪{recommended_investment}")

            st.subheader("סיכום שורה תחתונה:")
            if recommended_investment == 0:
                st.write("כדאי להשהות את ההשקעה הנוכחית במניה זו.")
            else:
                st.write("אפשר להמשיך עם DCA בהתאם להמלצות.")

if __name__ == "__main__":
    main()
