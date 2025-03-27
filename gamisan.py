import streamlit as st
from PIL import Image
import pandas as pd
import sqlite3
import altair as alt
import datetime
from streamlit.column_config import NumberColumn
import os
from dotenv import load_dotenv
from openai import OpenAI
import httpx

# UTF-8でエンコード
# client = openai.OpenAI(
#     api_key="YOUR_API_KEY",
#     http_client=httpx.Client(headers={"Accept-Charset": "utf-8"})
# )

# --- APIキーの読み込み ---
load_dotenv(".env")  # .env ファイルから環境変数を読み込む
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# --- 松岡修造風コメント ---
def get_matsuoka_comment():
    """ChatGPT APIを使用して松岡修造風のコメントを取得する"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは松岡修造のように熱く励ますAIです。"},
            {"role": "user", "content": "80文字以内で資産を増やそうと頑張る人への応援コメントをください。"}
        ],
        max_tokens=50
    )
    return response.choices[0].message.content.strip()

# CSSで吹き出しデザインを入れる
st.markdown(
    """
    <style>
    .bubble {
        background-color: #FDE74C;
        padding: 10px;
        border-radius: 10px;
        width: fit-content;
        margin: 10px auto;
        text-align: center;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# アプリ名称
st.markdown('<div class="header">金融資産管理アプリ</div>', unsafe_allow_html=True)
# 松岡修造の応援コメントを取得
comment = get_matsuoka_comment()
# 吹き出し形式でコメントを表示
st.markdown(f'<div class="bubble"> {comment} </div>', unsafe_allow_html=True)
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
#スタイルの読み込み カスタムCSS
#ロゴをよみこみ
st.markdown(
    """
    <style>
    .header {
        font-size: 30px;
        color: #3EBEA1;
        text-align: center;
        padding-top: 20px;
        padding-bottom: 20px;
    }
    .h1 {
        font-size: 30px;
        color: white;
        text-align: left;
        background-color: #3EBEA1;
    }
    .image {
        width: 200px;
        margin-top: 50px;
        margin-bottom: 50px;
        }
    </style>
    """,
    unsafe_allow_html=True
)
# データベースに接続
conn = sqlite3.connect('famafinancial_250325.db')
c = conn.cursor()
#ロゴをよみこみ
file_path = st.file_uploader('', type=['png', 'jpg', 'jpeg'])
img = Image.open('logo.jpg')
st.image(img)
original_size = img.size
resize_width = 100
resized = img.resize((resize_width, int(original_size[1]/(original_size[0]/resize_width))))
#アプリ名称を記載
st.markdown('<div class="header">金融資産管理アプリ</div>', unsafe_allow_html=True)
#h1を追記
st.markdown('<div class="h1">　収支入力と現在保有の金融資産</div>', unsafe_allow_html=True)
# Streamlitでカレンダーを表示
min_date = datetime.date(1900, 1, 1)
max_date = datetime.date(2100, 12, 31)
d = st.date_input('今日の日付を入力してください。', datetime.date(2025, 3, 22), min_value=min_date, max_value=max_date)
# データベースから前回までの残高を取得する
c.execute("SELECT item, amount FROM finance WHERE item IN ('預金', '財形貯蓄', '社内積立')")
# 結果を取得
results = c.fetchall()
# DBの結果を辞書に変換
balance_dict = {item: amount for item, amount in results}
# # DBに値がなかった場合のデフォルト値を設定（必要に応じて変更）
# default_balances = {"預金": 1000000, "財形貯蓄": 200000, "社内積立": 100000}
# # 取得した値があればそれを、なければデフォルト値を使用
# balance_dict = {key: balance_dict.get(key, default_balances[key]) for key in default_balances.keys()}
# データフレームを作成
data = {
    "資産": ["預金" , "財形貯蓄", "社内積立"],
    "前回までの残高": [
        balance_dict["預金"],
        balance_dict["財形貯蓄"],
        balance_dict["社内積立"]
    ],
    "支出入": [0, 0, 0],  # 初期値は0
    "現在の残高":  [
        balance_dict["預金"],
        balance_dict["財形貯蓄"],
        balance_dict["社内積立"]
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
# Altairで積み上げ棒グラフを作成（軸の目盛りを10万円単位）
chart = (
    alt.Chart(chart_data)
    .mark_bar()
    .encode(
        x=alt.X("カテゴリ:N", title="金融資産"),
        y=alt.Y("金額:Q", title="金額（円）", scale=alt.Scale(domain=[0, max(df['現在の残高'].max() + 100000, 1500000)], nice=True)),
        color=alt.Color(
            "資産",
            scale=alt.Scale(range=["#BF99ED", "#F9DA25", "#40E8CB"]),
            ),
    )
    .properties(width=50, height=400)
    )
# Streamlitでグラフを表示
st.altair_chart(chart, use_container_width=True)
# データベースから過去ログ一覧を取得する関数
def fetch_datas():
    result = c.execute("SELECT * FROM finance").fetchall()
    return result
# 過去ログ一覧を表示
st.write("過去ログ一覧:")
users = fetch_datas()
for row in users:
    st.write(f"ID: {row[0]}, 資産/負債: {row[1]}, 金額: {row[3]}")
# データベース接続をクローズ
conn.close()
