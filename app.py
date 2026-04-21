import os
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from dotenv import load_dotenv

from update_rsi import update_rsi_data
from utils.envs import get_envs

load_dotenv()

DB_PATH = get_envs("DB_PATH", "data/rsi_data.db")


# check should update page data
def should_refresh():
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT MAX(last_updated) FROM rsi_data").fetchone()
        conn.close()

        if not row or not row[0]:
            return True

        last = datetime.fromisoformat(row[0])
        return (datetime.now() - last) > timedelta(minutes=30)

    except:
        return True


# page settings
st.set_page_config(
    page_title="RSI Heatmap Crypto",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Crypto RSI Heatmap")


@st.cache_data(ttl=1800)  # 30 minutes
def run_update():
    update_rsi_data()


if should_refresh():
    with st.spinner("Updating RSI data..."):
        run_update()
else:
    # ensure table exists even if no update
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1 FROM rsi_data LIMIT 1")
        conn.close()
    except:
        # table missing → create it
        run_update()

coins_limit = int(get_envs('UPDATE_LIMIT', 10))
st.markdown(f"### Real-time RSI for Top {coins_limit} Cryptocurrencies")

timeframe = get_envs("DEFAULT_RSI_INTERVAL", "1d")

# connect to database
conn = sqlite3.connect(DB_PATH)

# show data
try:
    df = pd.read_sql_query("SELECT * FROM rsi_data ORDER BY rsi DESC", conn)

    if not df.empty:

        def color_rsi(val):
            if val <= 30:
                return "background-color: #2ecc71; color: black;"  # strong green
            elif val <= 45:
                return "background-color: #a9dfbf; color: black;"  # light green
            elif val <= 55:
                return "background-color: transparent;"  # neutral gray
            elif val <= 70:
                return "background-color: #f5b7b1; color: black;"  # light red
            else:
                return "background-color: #e74c3c; color: white;"  # strong red


        st.data_editor(df, use_container_width=True)

        st.subheader("RSI Market Overview")


        # calculate category based on RSI
        def get_rsi_category(rsi):
            if rsi <= 25:
                return "Very Weak"
            elif rsi <= 30:
                return "Oversold"
            elif rsi <= 45:
                return "Weak"
            elif rsi >= 53:
                return "Overbought"
            else:
                return "Neutral"


        df['category'] = df['rsi'].apply(get_rsi_category)

        # select color for each category
        color_map = {
            "Very Weak": "#e74c3c",
            "Oversold": "#ff6b6b",
            "Weak": "#f4a261",
            "Neutral": "#95a5a6",
            "Overbought": "#2ecc71"
        }

        fig = px.scatter(
            df,
            x="rank",
            y="rsi",
            color="category",
            color_discrete_map=color_map,
            hover_name="name",
            hover_data={
                "symbol": True,
                "rsi": ":.2f",
                "rsi_last": ":.2f",
                "price": ":.4f",
                "percent_change_24h": ":.2f"
            },
            size="rsi",
            size_max=8,
            title=f"RSI Scatter - Top {coins_limit} Cryptocurrencies",
            labels={"rank": "Market Rank (Lower = Stronger)", "rsi": "Current RSI"}
        )

        for i, row in df.iterrows():

            fig.add_annotation(
                x=row['rank'],
                y=row['rsi'] - 3 if row['rsi_last'] > row['rsi'] else row['rsi'] + 3,  # کمی پایین‌تر از نقطه
                text=row['symbol'],
                showarrow=False,
                font=dict(size=10, color="#cccccc"),
                align="center"
            )

            if pd.notna(row.get('rsi_last')):
                color = "#2ecc71" if row['rsi'] > row['rsi_last'] else "#e74c3c"  # سبز = افزایش، قرمز = کاهش

                fig.add_shape(
                    type="line",
                    x0=row['rank'],
                    y0=row['rsi_last'],
                    x1=row['rank'],
                    y1=row['rsi'],
                    line=dict(
                        color=color,
                        width=2,
                        dash="dot"
                    )
                )

        # set styles for chart
        fig.update_traces(
            marker=dict(line=dict(width=1, color='white')),
            selector=dict(mode='markers')
        )

        # add lines for each category
        fig.add_hline(y=70, line_dash="dash", line_color="#e74c3c", opacity=0.3, annotation_text="Overbought (70)",
                      annotation_position="top right")
        fig.add_hline(y=30, line_dash="dash", line_color="#2ecc71", opacity=0.3, annotation_text="Oversold (30)",
                      annotation_position="bottom right")
        fig.add_hline(y=45, line_dash="dot", line_color="#f4a261", opacity=0.3, annotation_text="Weak Zone")

        # configuration for X,Y axis
        fig.update_layout(
            xaxis_title="Market Rank (Lower = Stronger)",
            yaxis_title="RSI Value",
            yaxis=dict(range=[0, 100]),
            height=650,
            legend_title="RSI Category",
            hovermode="closest"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available yet. Please wait for the first update.")

except Exception as e:
    st.error(f"Error loading data: {e}")

'''
    [![Repo](https://badgen.net/badge/icon/GitHub?icon=github&label)](https://github.com/mosiiisom/rsi-heatmap-crypto) 

'''
st.markdown("<br>", unsafe_allow_html=True)

conn.close()
