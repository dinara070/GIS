import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import io
import datetime

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(
    page_title="ГІС Диспетчерська Система Регіональних Електромереж v2.5",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Темна тема для графіків Matplotlib
plt.style.use('dark_background')

# --- ІНІЦІАЛІЗАЦІЯ ДАНИХ У СЕСІЇ ---
if "objects" not in st.session_state:
    st.session_state.objects = [
        {"name": "ТП-12", "type": "Підстанція", "status": "Нормальна", "desc": "ВН-110 кВ, Навантаження: 70%. Ремонтів: 3.", "latitude": 49.2331, "longitude": 28.4682, "criticality": "Висока"},
        {"name": "ТП-28", "type": "Підстанція", "status": "Нормальна", "desc": "ВН-35 кВ, Навантаження: 45%. Ремонтів: 1.", "latitude": 49.2425, "longitude": 28.4810, "criticality": "Середня"},
        {"name": "ТП-245", "type": "Підстанція", "status": "АВАРІЯ", "desc": "ВН-10 кВ, Навантаження: 95%! Потребує термінової заміни!", "latitude": 49.2210, "longitude": 28.4422, "criticality": "Критична"},
        {"name": "ТП-67", "type": "Підстанція", "status": "Нормальна", "desc": "ВН-35 кВ, Навантаження: 30%. Новий об'єкт.", "latitude": 49.2512, "longitude": 28.4935, "criticality": "Середня"},
        {"name": "Оп. №8", "type": "Опора", "status": "Норма", "desc": "ЖБ СВ-110. Задовільний стан. Огляд: 2024-01", "latitude": 49.2295, "longitude": 28.4550, "criticality": "Низька"},
        {"name": "Оп. №9", "type": "Опора", "status": "Попередження", "desc": "Пошкоджено ізолятор після грози. Рекомендовано ремонт.", "latitude": 49.2310, "longitude": 28.4585, "criticality": "Середня"},
        {"name": "Оп. №10", "type": "Опора", "status": "Норма", "desc": "ЖБ СВ-110. Огляд: 2024-05. Норма", "latitude": 49.2325, "longitude": 28.4610, "criticality": "Низька"},
    ]

if "log_data" not in st.session_state:
    st.session_state.log_data = [
        {"Час": "23.05 09:14", "Тип": "Аварія", "Об'єкт": "ТП-245", "Опис": "Відключення трансформатора, немає напруги", "Критичність": "Критична"},
        {"Час": "23.05 08:52", "Тип": "Аварія", "Об'єкт": "Оп. №9", "Опис": "Пошкоджено ізолятор після грози", "Критичність": "Середня"},
        {"Час": "23.05 07:30", "Тип": "Планове ТО", "Об'єкт": "ТП-12", "Опис": "Регламентне обслуговування трансформатора", "Критичність": "Висока"},
        {"Час": "22.05 18:45", "Тип": "Ремонт", "Об'єкт": "КЛ-3", "Опис": "Замінено кабельну муфту 10 кВ", "Критичність": "Висока"},
        {"Час": "22.05 15:20", "Тип": "Інспекція", "Об'єкт": "Оп. №11", "Опис": "Виявлено корозію на опорі 1988 р.", "Критичність": "Низька"}
    ]

if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = [
        {"Дата": "2026-05-24", "Об'єкт": "ТП-12", "Вид робіт": "Регламентне ТО силового трансформатора", "Статус": "Заплановано"},
        {"Дата": "2026-05-26", "Об'єкт": "КЛ-3", "Вид робіт": "Діагностика ізоляції кабелю 10 кВ", "Статус": "Підготовка"},
        {"Дата": "2026-05-28", "Об'єкт": "Оп. №11", "Вид робіт": "Заміна застарілої стійки опори", "Статус": "Заплановано"},
    ]

if "selected_object" not in st.session_state:
    st.session_state.selected_object = st.session_state.objects[2]

if "task_closed" not in st.session_state:
    st.session_state.task_closed = False

# --- ГОЛОВНЕ МЕНЮ ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏢 Диспетчер мапи", 
    "📱 Мобільний клієнт", 
    "📊 Аналітика та KPI", 
    "📋 Журнал подій", 
    "📅 Планування ТО",
    "💾 Data Центр"
])

# ==========================================
# ВКЛАДКА 1: ДИСПЕТЧЕР МАПИ
# ==========================================
with tab1:
    st.title("🏢 Оперативний диспетчерський пульт ГІС")
    col_map, col_side = st.columns([2.3, 1])
    
    with col_map:
        # Нова фіча: Симуляція режимів відображення мережі
        mode = st.radio("🛠️ Режим відображення шарів мережі:", ["Стандартний ГІС", "Вечірній максимум (Навантаження)", "Аварійні ділянки"], horizontal=True)
        
        # Безпечна конвертація та рендеринг карти
        map_df = pd.DataFrame(st.session_state.objects)
        st.map(map_df, size=35)
        
        st.markdown("##### 🔍 Швидкий вибір об'єкта зі списку:")
        obj_names = [o["name"] for o in st.session_state.objects]
        try:
            curr_index = obj_names.index(st.session_state.selected_object["name"])
        except ValueError:
            curr_index = 2
            
        selected_name = st.selectbox("Оберіть вузол для виведення телеметрії та SCADA систем:", obj_names, index=curr_index)
        
        for o in st.session_state.objects:
            if o["name"] == selected_name:
                st.session_state.selected_object = o

    with col_side:
        obj = st.session_state.selected_object
        st.subheader("ℹ️ Телеметрія та Управління")
        
        st.markdown(f"### {obj['name']}")
        if "АВАРІЯ" in obj['status']: st.error(f"Статус: {obj['status']}")
        elif "Попередження" in obj['status']: st.warning(f"Статус: {obj['status']}")
        else: st.success(f"Статус: {obj['status']}")
            
        st.markdown(f"**Важливість вузла:** `{obj['criticality']}`")
        st.markdown(f"**Координати:** `{obj['latitude']:.4f}° N, {obj['longitude']:.4f}° E`")
        st.markdown(f"**Опис та параметри:** {obj['desc']}")
        
        # Нова фіча: Інструменти телеуправління SCADA для диспетчера
        st.divider()
        st.markdown("🎛️ **Дистанційне керування (SCADA):**")
        c1, c2 = st.columns(2)
        if c1.button("⚡ Вимкнути вимикач ВВ", use_container_width=True):
            st.toast(f"🚨 Надіслано сигнал вимкнення на {obj['name']}!")
            st.session_state.log_data.insert(0, {"Час": datetime.datetime.now().strftime("%d.%m %H:%M"), "Тип": "Ремонт", "Об'єкт": obj['name'], "Опис": "Дистанційне оперативне вимкнення вимикача диспетчером.", "Критичність": "Висока"})
        if c2.button("🟢 Увімкнути АВР", use_container_width=True):
            st.success(f"Автоматика резерву на {obj['name']} активна.")
            
        st.divider()
        st.markdown("📲 **Комунікаційний хаб:**")
        if st.button("📲 Надіслати оперативний наряд бригаді", use_container_width=True):
            st.toast(f"📡 API: Наряд для {obj['name']} надіслано в польовий додаток!")
            
        permit_text = f"НАРЯД-ДОПУСК №{obj['name']}-2026\nОб'єкт: {obj['name']} ({obj['type']})\nКритичність: {obj['criticality']}\nКоординати: {obj['latitude']}, {obj['longitude']}\nОпис: {obj['desc']}\nЗгенеровано системою Вінницяобленерго."
        st.download_button(
            label="📄 Завантажити Наряд-Допуск (.txt)",
            data=permit_text,
            file_name=f"permit_{obj['name']}.txt",
            mime="text/plain",
            use_container_width=True
        )

# ==========================================
# ВКАДКА 2: МОБІЛЬНИЙ КЛІЄНТ (З ЧЕК-ЛИСТОМ ТБ)
# ==========================================
with tab2:
    st.title("📱 Цифровий кабінет лінійної бригади")
    _, phone_col, _ = st.columns([1, 2, 1])
    with phone_col:
        st.markdown("---")
        st.markdown("<h3 style='text-align: center; color: #185FA5;'>📱 Мобильний додаток ОВБ</h3>", unsafe_allow_html=True)
        st.info("👷 Бригада №1 (ОВБ Центр) | GPS: Активний")
        
        if st.session_state.task_closed:
            st.success("🎉 Звіт успішно відправлено на сервер! Очікуйте нових розпоряджень.")
            if st.button("🔄 Оновити та отримати нове завдання"):
                st.session_state.task_closed = False
                st.rerun()
        else:
            st.warning("🚨 **Поточне завдання:** Усунення пошкодження на ТП-245")
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🗺️ Навігатор", "🔒 Техніка безпеки", "📥 Звіт"])
            
            with sub_tab1:
                st.write("⏱️ Розрахунковий час приїзду: 8 хв")
                st.map(pd.DataFrame([{"latitude": 49.2210, "longitude": 28.4422}]), zoom=14)
                
            with sub_tab2:
                st.markdown("⚠️ **Обов'язковий чек-лист допуску до роботи:**")
                tb_1 = st.checkbox("Перевірено відсутність напруги покажчиком")
                tb_2 = st.checkbox("Встановлено переносні заземлення")
                tb_3 = st.checkbox("Вивішено плакати 'НЕ ВМИКАТИ! РОБОТА ТУТ!'")
                
            with sub_tab3:
                comment = st.text_area("Введіть технічний коментар виконаних робіт:", placeholder="Опишіть заміну запобіжників, ліквідацію КЗ...")
                if st.button("🚀 Надіслати звіт диспетчеру", use_container_width=True):
                    if not (tb_1 and tb_2 and tb_3):
                        st.error("❌ Роботу не можна завершити без виконання всіх правил техніки безпеки!")
                    elif not comment:
                        st.error("❌ Будь ласка, заповніть текстовий звіт про роботу.")
                    else:
                        st.session_state.task_closed = True
                        st.session_state.log_data.insert(0, {
                            "Час": datetime.datetime.now().strftime("%d.%m %H:%M"),
                            "Тип": "Ремонт",
                            "Об'єкт": "ТП-245",
                            "Опис": f"[Бригада 1]: {comment} (Правила ТБ дотримано)",
                            "Критичність": "Висока"
                        })
                        st.rerun()
        st.markdown("---")

# ==========================================
# ВКАДКА 3: АНАЛІТИКА ТА ГАЛУЗЕВІ KPI (SAIDI / SAIFI)
# ==========================================
with tab3:
    st.title("📊 Аналітичний комплекс та розрахунок надійності SAIDI/SAIFI")
    
    # Розрахунок метрик
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Індекс SAIDI (сер. час вимкнення)", "42.5 хв/рік", "-3.2 хв від плану", delta_color="inverse")
    m2.metric("Індекс SAIFI (сер. частота вимкнень)", "1.14 од/рік", "+0.02", delta_color="inverse")
    m3.metric("Загальна потужність споживання", "148.5 МВт", "Норма")
    m4.metric("Коефіцієнт корисного використання", "94.2%", "+0.5%")
    
    # Графіки
    st.markdown("### 📈 Прогнозування добового навантаження мережі та Аварійність")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    
    # Лінійний графік прогнозу споживання
    hours = [f"{i}:00" for i in range(0, 25, 4)]
    actual_load = [65, 50, 85, 110, 140, 148, 90]
    predicted_load = [62, 53, 80, 115, 138, 145, 95]
    ax1.plot(hours, actual_load, label="Фактичне навантаження (МВт)", color="#38bdf8", marker="o", linewidth=2)
    ax1.plot(hours, predicted_load, label="Прогноз SmartGrid AI", color="#a855f7", linestyle="--")
    ax1.set_title("Прогноз графіка навантаження", fontsize=10)
    ax1.legend()
    ax1.grid(True, alpha=0.2)
    
    # Діаграма структури подій
    current_logs_df = pd.DataFrame(st.session_state.log_data)
    types_distribution = current_logs_df["Тип"].value_counts()
    ax2.pie(types_distribution.values, labels=types_distribution.index, colors=['#ef4444', '#f59e0b', '#10b981', '#38bdf8', '#bc5090'], autopct='%1.1f%%', startangle=90)
    ax2.set_title("Розподіл подій у журналі", fontsize=10)
    
    st.pyplot(fig)

# ==========================================
# ВКАДКА 4: ЖУРНАЛ ПОДІЙ З СТУПЕНЕМ КРИТИЧНОСТІ
# ==========================================
with tab4:
    st.title("📋 Розширений журнал обліку подій")
    
    df = pd.DataFrame(st.session_state.log_data)
    
    # Фільтрація
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: search_query = st.text_input("🔍 Швидкий фільтр за назвою об'єкта", "")
    with col_f2: type_filter = st.selectbox("Тип події", ["Усі типи", "Аварія", "Планове ТО", "Ремонт", "Інспекція"])
    with col_f3: crit_filter = st.selectbox("Ступінь критичності", ["Усі рівні", "Критична", "Висока", "Середня", "Низька"])
        
    if type_filter != "Усі типи": df = df[df["Тип"] == type_filter]
    if crit_filter != "Усі рівні": df = df[df["Критичність"] == crit_filter]
    if search_query: df = df[df["Об'єкт"].str.contains(search_query, case=False)]
        
    # Виведення датафрейму
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Критичність": st.column_config.TextColumn("⚠️ Критичність", help="Рівень важливості для реагування"),
            "Тип": st.column_config.TextColumn("Категорія"),
        }
    )

# ==========================================
# ВКАДКА 5: ІНТЕРАКТИВНЕ ПЛАНУВАННЯ ТО
# ==========================================
with tab5:
    st.title("📅 Планувальник ремонтів та Технічного Обслуговування")
    
    st.subheader("➕ Додати нове завдання до плану:")
    col_in1, col_in2, col_in3 = st.columns(3)
    with col_in1: new_obj = st.selectbox("Оберіть об'єкт для планування", [o["name"] for o in st.session_state.objects])
    with col_in2: new_date = st.date_input("Дата проведення робіт", datetime.date.today() + datetime.timedelta(days=1))
    with col_in3: new_type = st.text_input("Вид робіт (напр. Заміна трансформатора)", placeholder="Введіть опис робіт...")
        
    if st.button("➕ Внести до календарного графіка", use_container_width=True):
        if new_type:
            st.session_state.schedule_data.append({
                "Дата": str(new_date),
                "Об'єкт": new_obj,
                "Вид робіт": new_type,
                "Статус": "Заплановано"
            })
            st.success(f"✅ Роботи по {new_obj} успішно заплановано на {new_date}!")
            st.rerun()
        else:
            st.error("Будь ласка, вкажіть вид робіт.")
            
    st.divider()
    st.subheader("📋 Поточний графік робіт:")
    sched_df = pd.DataFrame(st.session_state.schedule_data)
    st.table(sched_df)

# ==========================================
# ВКАДКА 6: DATA ЦЕНТР (ІМПОРТ / ЕКСПОРТ)
# ==========================================
with tab6:
    st.title("💾 Data-Центр синхронізації та обміну")
    st.markdown("Експорт поточного логу системи для звітності керівництву або завантаження сторонніх файлів конфігурацій.")
    
    curr_df = pd.DataFrame(st.session_state.log_data)
    exp_col, imp_col = st.columns(2)
    
    with exp_col:
        st.subheader("📤 Експорт даних")
        
        csv_data = curr_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачати Excel CSV (.csv)",
            data=csv_data,
            file_name="gis_system_export.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            curr_df.to_excel(writer, index=False, sheet_name='Лог')
        st.download_button(
            label="📥 Скачати книгу MS Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="gis_system_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with imp_col:
        st.subheader("📥 Імпорт зовнішніх даних")
        uploaded_file = st.file_uploader("Оберіть файл конфігурації мережі", type=["csv", "xlsx", "json"])
        if uploaded_file is not None:
            st.success("✅ Структуру файлу успішно розпізнано! Дані готові до інтеграції.")
