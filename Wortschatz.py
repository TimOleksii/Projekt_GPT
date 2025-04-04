import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Файл
excel_file = "wortliste_train.xlsx"

# Если Excel есть — загружаем
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
else:
    df = pd.DataFrame(columns=["Wort", "Niveau", "Hinzugefügt am"])

# 🟢 Интерфейс
st.title("🧠 Тренажёр немецких слов")

st.subheader("➕ Добавить новое слово")
neues_wort = st.text_input("Введи слово:")

if st.button("Добавить в список"):
    if neues_wort:
        if neues_wort not in df["Wort"].values:
            new_row = {
                "Wort": neues_wort,
                "Niveau": 0,
                "Hinzugefügt am": datetime.now().strftime("%d.%m.%Y"),              
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(excel_file, index=False)
            st.success(f"✅ Слово '{neues_wort}' добавлено!")
        else:
            st.warning("⚠️ Это слово уже в списке.")
    else:
        st.warning("⚠️ Введи слово перед добавлением.")
import random
import requests

# Настройки OpenRouter
API_KEY = st.secrets["API_KEY"] 
API_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Функция: количество дней с последней тренировки
def tage_seit(datum):
    try:
        return (datetime.now() - datetime.strptime(str(datum), "%d.%m.%Y")).days
    except:
        return 9999  # если ошибка с датой

# Кнопка Старт тренировки
st.subheader("🎯 Старт тренировки")
if st.button("Начать тренировку"):
    candidates = []
    for index, row in df.iterrows():
        level = int(row["Niveau"])
        if level > 5:
            continue
        tage = tage_seit(row["Hinzugefügt am"])
        if tage >= level ** 2:
            candidates.append(row)

    if not candidates:
        st.info("😌 Пока нет слов, нуждающихся в тренировке.")
    else:
        wort_info = random.choice(candidates)
        wort = wort_info["Wort"]
        level = wort_info["Niveau"]

        st.write(f"🔍 Тренируем слово: **{wort}**")

        # Сохраняем в session_state
        st.session_state["wort"] = wort
        st.session_state["index"] = df[df["Wort"] == wort].index[0]
        st.session_state["Niveau"] = level

        # Сколько предложений (3–10)
        anzahl = 10

        # Генерация предложений через Gemini
        prompt = (
            f"Придумай {anzahl} коротких предложений из нескольких слов на русском языке, "
            f"с использованием слова '{wort}' (перевода этого немецкого слова). "
            f"Никаких заголовков, вводных фраз, подписей или нумерации — только сами фразы, каждая с новой строки. "
            f"Этот текст используется в API, так что ответ должен быть строго в формате:\n"
    f"фраза 1\nфраза 2\nфраза 3\n..."
        )

        data = {
            "model": "google/gemini-pro",
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(API_URL, headers=HEADERS, json=data)
        antwort_json = response.json()

        if "choices" in antwort_json:
            saetze = antwort_json["choices"][0]["message"]["content"].strip().split("\n")
            st.session_state["saetze"] = [s for s in saetze if s.strip()]
            st.session_state["übersetzt"] = []
        else:
            st.error("❌ Не удалось получить примеры.")


if "saetze" in st.session_state:
    st.markdown("### 📚 Примеры предложений:")
    for i, satz in enumerate(st.session_state["saetze"]):
        # Уже переведённые предложения отмечаем
        if i < len(st.session_state["übersetzt"]):
            st.markdown(f"- {satz}  \n👉 **{st.session_state['übersetzt'][i]}**")
        else:
            st.markdown(f"- {satz}")

    # Кнопка перевода одного предложения
if st.button("📘 Перевод следующего предложения"):
    noch_zu_übersetzen = st.session_state["saetze"][len(st.session_state["übersetzt"]):]
    if noch_zu_übersetzen:
        zu_übersetzen = noch_zu_übersetzen[0]
        wort = st.session_state["wort"]

        prompt = (
            f"Переведи на немецкий: '{zu_übersetzen}', c учетом того что я тренирую слово {wort}. "
            f"Учти, что это для API, потому никаких других подписей: исключительно "
            f"перевод на немецкий."
        )

        data = {
            "model": "google/gemini-pro",
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(API_URL, headers=HEADERS, json=data)
        übersetzung = response.json()["choices"][0]["message"]["content"].strip()
        st.session_state["übersetzt"].append(übersetzung)

        # 🚀 мгновенно перерисовать интерфейс
        st.experimental_rerun()

    # Кнопки "вспомнил / не вспомнил"
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("✅ Отлично"):
        neuer_wert = min(st.session_state["Niveau"] + 1, 5)
        df.at[st.session_state["index"], "Niveau"] = neuer_wert
        df.at[st.session_state["index"], "Hinzugefügt am"] = datetime.now().strftime("%d.%m.%Y")
        df.to_excel(excel_file, index=False)
        st.success(f"🎉 Отлично! Уровень слова повышен до {neuer_wert}")
        st.session_state.clear()

with col2:
    if st.button("➖ Средне"):
        # Ничего не меняем, только дату обновим
        df.at[st.session_state["index"], "Hinzugefügt am"] = datetime.now().strftime("%d.%m.%Y")
        df.to_excel(excel_file, index=False)
        st.info("ℹ️ Уровень не изменился, дата обновлена")
        st.session_state.clear()

with col3:
    if st.button("❌ Плохо"):
        neuer_wert = max(st.session_state["Niveau"] - 1, 0)
        df.at[st.session_state["index"], "Niveau"] = neuer_wert
        df.at[st.session_state["index"], "Hinzugefügt am"] = datetime.now().strftime("%d.%m.%Y")
        df.to_excel(excel_file, index=False)
        st.warning(f"📉 Уровень слова понижен до {neuer_wert}")
        st.session_state.clear()
    
