import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import json

# ============================================================
# 1. НАСТРОЙКИ СТРАНИЦЫ
# ============================================================
st.set_page_config(
    page_title="Нейросети в творчестве",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# 2. ПОДКЛЮЧЕНИЕ К FIREBASE (работает и локально, и в облаке)
# ============================================================
if not firebase_admin._apps:
    key_loaded = False
    
    # СПОСОБ 1: Для Streamlit Cloud — читаем ключ из Secrets
    try:
        key_dict = json.loads(st.secrets["firebase_key"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
        key_loaded = True
    except Exception:
        pass
    
    # СПОСОБ 2: Для локального запуска — читаем из файла
    if not key_loaded:
        KEY_PATH = "serviceAccountKey.json"
        if os.path.exists(KEY_PATH):
            try:
                cred = credentials.Certificate(KEY_PATH)
                firebase_admin.initialize_app(cred)
                key_loaded = True
            except Exception as e:
                st.error(f"❌ Ошибка инициализации Firebase: {e}")
                st.stop()
        else:
            st.error("❌ Файл serviceAccountKey.json не найден! Проверьте инструкцию.")
            st.stop()

db = firestore.client()

# ============================================================
# 3. ЗАГОЛОВОК И ВКЛАДКИ
# ============================================================
st.title("🎨 Отношение к нейросетям в творчестве")
st.caption("Анонимный опрос для учебной практики. Данные сохраняются в облако.")

tab_survey, tab_analytics = st.tabs(["📝 Пройти опрос", "📊 Аналитика"])

# ============================================================
# 4. ВКЛАДКА «ОПРОС»
# ============================================================
with tab_survey:
    st.markdown("### Заполните форму — это займёт 2 минуты")

    with st.form("survey_form"):
        col1, col2 = st.columns(2)

        with col1:
            age = st.number_input("Ваш возраст", min_value=14, max_value=80, step=1)
            creativity_field = st.selectbox(
                "Ваша сфера творчества",
                ["Художник / иллюстратор", "Музыкант", "Писатель / поэт",
                 "Фотограф", "Дизайнер", "Видеограф", "Программист / кодер",
                 "Другое", "Не занимаюсь творчеством"]
            )
            ai_usage = st.radio(
                "Используете ли вы нейросети в работе?",
                ["Да, регулярно", "Иногда", "Пробовал(а) один раз", "Нет, не использую"]
            )

        with col2:
            ai_tasks = st.multiselect(
                "Для каких задач применяете ИИ?",
                ["Генерация изображений", "Написание текстов", "Создание музыки",
                 "Монтаж видео", "Написание кода", "Перевод", "Не применяю"]
            )
            attitude = st.slider(
                "Ваше общее отношение к ИИ в творчестве (1 — резко против, 10 — в восторге)",
                1, 10, 5
            )
            coauthor = st.radio(
                "Можно ли считать ИИ соавтором произведения?",
                ["Да, полноценным соавтором", "Скорее да, чем нет",
                 "Скорее нет, чем да", "Нет, это просто инструмент"]
            )

        copyright_owner = st.selectbox(
            "Кому должны принадлежать авторские права на работу, созданную с помощью ИИ?",
            ["Пользователю, который ввёл промпт",
             "Разработчикам нейросети",
             "Разделить между пользователем и разработчиками",
             "Никому — это общественное достояние",
             "Затрудняюсь ответить"]
        )

        impact = st.radio(
            "Как ИИ влияет на качество творчества?",
            ["Улучшает, даёт новые идеи", "Не влияет существенно",
             "Ухудшает — убивает оригинальность", "Затрудняюсь ответить"]
        )

        main_fear = st.multiselect(
            "Главные страхи / проблемы, связанные с ИИ в творчестве",
            ["Потеря работы / дохода", "Плагиат и копирование стиля",
             "Засилие однотипного контента", "Снижение ценности человеческого труда",
             "Юридическая неопределённость", "Меня это не беспокоит"]
        )

        comment = st.text_area("Ваши мысли по теме (необязательно)", height=100)

        submitted = st.form_submit_button("✅ Отправить ответ", use_container_width=True)

    # --- Сохранение в Firebase ---
    if submitted:
        record = {
            "age": int(age),
            "creativity_field": creativity_field,
            "ai_usage": ai_usage,
            "ai_tasks": ai_tasks,
            "attitude": int(attitude),
            "coauthor": coauthor,
            "copyright_owner": copyright_owner,
            "impact": impact,
            "main_fear": main_fear,
            "comment": comment,
            "timestamp": datetime.utcnow()
        }
        try:
            db.collection("neuro_creativity_responses").add(record)
            st.success("🎉 Спасибо! Ваш ответ сохранён.")
            st.balloons()
        except Exception as e:
            st.error(f"❌ Ошибка сохранения: {e}")

# ============================================================
# 5. ВКЛАДКА «АНАЛИТИКА»
# ============================================================
with tab_analytics:
    st.markdown("### 📊 Дашборд по собранным ответам")

    if st.button("🔄 Обновить данные"):
        st.cache_data.clear()

    try:
        docs = db.collection("neuro_creativity_responses").stream()
        data = [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        data = []

    if not data:
        st.info("Пока нет ответов. Пройдите опрос несколько раз для теста.")
    else:
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp", ascending=False)

        # --- KPI-карточки ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Всего ответов", len(df))
        c2.metric("📈 Средняя оценка отношения", f"{df['attitude'].mean():.1f} / 10")
        c3.metric("🤖 Используют ИИ",
                  f"{len(df[df['ai_usage'].str.contains('Да|Иногда', na=False)])} чел.")
        c4.metric("📅 Последний ответ",
                  df["timestamp"].max().strftime("%d.%m.%Y"))

        st.markdown("---")

        # --- Графики ---
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Распределение отношения к ИИ")
            fig1 = px.histogram(
                df, x="attitude", nbins=10,
                title="Оценки от 1 до 10",
                color_discrete_sequence=["#6366f1"]
            )
            fig1.update_layout(xaxis_title="Оценка", yaxis_title="Количество")
            st.plotly_chart(fig1, use_container_width=True)

        with col_b:
            st.subheader("Частота использования ИИ")
            usage_counts = df["ai_usage"].value_counts().reset_index()
            usage_counts.columns = ["Ответ", "Количество"]
            fig2 = px.pie(
                usage_counts, values="Количество", names="Ответ",
                title="Кто использует нейросети?",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig2, use_container_width=True)

        col_c, col_d = st.columns(2)

        with col_c:
            st.subheader("Влияние ИИ на качество творчества")
            impact_counts = df["impact"].value_counts().reset_index()
            impact_counts.columns = ["Мнение", "Количество"]
            fig3 = px.bar(
                impact_counts, x="Мнение", y="Количество",
                color="Мнение",
                title="Как ИИ влияет на творчество?"
            )
            fig3.update_layout(showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

        with col_d:
            st.subheader("Сферы творчества респондентов")
            field_counts = df["creativity_field"].value_counts().reset_index()
            field_counts.columns = ["Сфера", "Количество"]
            fig4 = px.bar(
                field_counts, x="Количество", y="Сфера",
                orientation="h",
                color="Сфера",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig4.update_layout(showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

        # --- Таблица с ответами ---
        with st.expander("🗂 Посмотреть сырые данные"):
            st.dataframe(df, use_container_width=True)

        # --- Кнопка экспорта ---
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Скачать данные в CSV",
            csv,
            "survey_data.csv",
            "text/csv",
            use_container_width=True
        )
