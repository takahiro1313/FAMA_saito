import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import datetime
from streamlit.column_config import NumberColumn

# --- balance_summary テーブルのデータ更新関数 ---
def update_balance_summary(item, amount):
    with sqlite3.connect("famafinancial_250325.db") as conn:
        c = conn.cursor()

        # 既存のデータを取得
        c.execute("SELECT previous_balance, transactions FROM balance_summary WHERE item = ?", (item,))
        row = c.fetchone()

        if row:
            previous_balance, transactions = row
            new_transactions = transactions + amount
        else:
            previous_balance = 0
            new_transactions = amount

        # データを更新または挿入
        c.execute("""
            INSERT INTO balance_summary (item, previous_balance, transactions)
            VALUES (?, ?, ?)
            ON CONFLICT(item) DO UPDATE SET transactions = ?
        """, (item, previous_balance, new_transactions, new_transactions))

        conn.commit()

# スタイルの読み込み カスタムCSS
st.markdown(
    """
    <style>
    .header {
        font-size: 30px;
        color: #3EBEA1;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# データベースに接続
conn = sqlite3.connect('famafinancial_250325.db')
c = conn.cursor()

st.markdown('<div class="header">金融資産管理アプリ</div>', unsafe_allow_html=True)

# Streamlitでカレンダーを表示
min_date = datetime.date(1900, 1, 1)
max_date = datetime.date(2100, 12, 31)
d = st.date_input('今日の日付を入力してください。', datetime.date(2025, 3, 22), min_value=min_date, max_value=max_date)

# データベースから前回までの残高を取得する
c.execute("SELECT item, amount FROM finance WHERE item IN ('預金', '財形貯蓄', '社内積立')")
results = c.fetchall()

# DBの結果を辞書に変換
balance_dict = {item: amount for item, amount in results}

# データフレームを作成
data = {
    "資産": ["預金", "財形貯蓄", "社内積立"],
    "前回までの残高": [
        balance_dict.get("預金", 0),
        balance_dict.get("財形貯蓄", 0),
        balance_dict.get("社内積立", 0)
    ],
    "支出入": [0, 0, 0],  # 初期値は0
    "現在の残高":  [
        balance_dict.get("預金", 0),
        balance_dict.get("財形貯蓄", 0),
        balance_dict.get("社内積立", 0)
    ]
}
df = pd.DataFrame(data)

# ユーザーが支出入を入力できるようにする
for i in range(len(df)):
    df.loc[i, "支出入"] = st.number_input(
        f"{df.loc[i, '資産']}の増加額または減少額",
        value=df.loc[i, "支出入"],
        step=1000,
        format="%d"
    )

# 前回までの残高 + 支出入 = 現在の残高
df["現在の残高"] = df["前回までの残高"] + df["支出入"]

# --- ボタンを押してデータを確定 ---
if st.button("現在の資産を追加"):
    # 現在の残高を更新
    df["現在の残高"] = df["前回までの残高"] + df["支出入"]
    
    # 更新後のデータを表示
    st.success("データが確定しました！")
    st.dataframe(df.style.format({"前回までの残高": "¥{:,.0f}", "支出入": "¥{:,.0f}", "現在の残高": "¥{:,.0f}"}))

# --- 支出入の入力とデータベース保存機能 ---
st.subheader("支出入の入力")

# 入力フィールド
項目 = st.selectbox("項目を選択してください", ["預金", "財形貯蓄", "社内積立"])
金額 = st.number_input("金額を入力してください", min_value=0, step=1000)

# 資産 or 負債の選択肢
種類 = st.selectbox("タイプを選択してください", ["金融資産", "負債"])

# ボタンを押したときの処理
if st.button("支出入を追加"):
    if 項目 and 金額 > 0:
        # 負債ならマイナス値に変換
        if 種類 == "負債":
            金額 = -金額

        with sqlite3.connect("famafinancial_250325.db") as conn:
            c = conn.cursor()
            # finance テーブルへ追加
            c.execute("INSERT INTO finance (created_at, item, amount, type) VALUES (datetime('now'), ?, ?, ?)", 
                      (項目, 金額, 種類))
            conn.commit()

        # balance_summary テーブルを更新
        update_balance_summary(項目, 金額)

        st.success(f"「{項目}」に {金額} 円 ({種類}) を追加しました！")
    else:
        st.error("項目・金額・タイプをすべて入力してください！")

# データフレームを表示
st.dataframe(df.style.format({"前回までの残高": "¥{:,.0f}", "支出入": "¥{:,.0f}", "現在の残高": "¥{:,.0f}"}))

# データフレームを積み上げ棒グラフ用に整形
chart_data = pd.melt(df, id_vars=["資産"], value_vars=["現在の残高"], var_name="カテゴリ", value_name="金額")

# Altairで積み上げ棒グラフを作成
chart = (
    alt.Chart(chart_data)
    .mark_bar()
    .encode(
        x=alt.X("カテゴリ:N", title="金融資産"),
        y=alt.Y("金額:Q", title="金額（円）", scale=alt.Scale(domain=[0, max(df['現在の残高'].max() + 100000, 1500000)], nice=True)),
        color="資産:N"
    )
    .properties(width=50, height=400)
)

# Streamlitでグラフを表示
st.altair_chart(chart, use_container_width=True)

# --- 過去ログ一覧を取得・表示 ---
def fetch_datas():
    with sqlite3.connect("famafinancial_250325.db") as conn:
        c = conn.cursor()
        return c.execute("SELECT * FROM finance").fetchall()

st.write("過去ログ一覧:")
users = fetch_datas()
for row in users:
    st.write(f"ID: {row[0]}, 資産/負債: {row[1]}, 金額: {row[3]}")
