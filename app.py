import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import io

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(
    page_title="ГІС Диспетчерська Система Регіональних Електромереж v2.0",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Темна тема для графіків Matplotlib
plt.style.use('dark_background')

# --- ІНІЦІАЛІЗАЦІЯ ДАНИХ У СЕСІЇ ---
if "objects" not in st.session_state:
    st.session_state.objects = [
        {"name": "ТП-12", "type": "Підстанція", "status": "Нормальна", "desc": "ВН-110 кВ, Навантаження: 70%. Ремонтів: 3. Останній: 2023-06"},
        {"name": "ТП-28", "type": "Підстанція", "status": "Нормальна", "desc": "ВН-35 кВ, Навантаження: 45%. Ремонтів: 1. Останній: 2024-03"},
        {"name": "ТП-245", "type": "Підстанція", "status": "АВАРІЯ", "desc": "ВН-10 кВ, Навантаження: 95%! Потребує термінової заміни! Ремонтів: 7."},
        {"name": "ТП-67", "type": "Підстанція", "status": "Нормальна", "desc": "ВН-35 кВ, Навантаження: 30%. Новий об'єкт."},
        {"name": "Оп. №8", "type": "Опора", "status": "Норма", "desc": "ЖБ СВ-110. Задовільний стан. Огляд: 2024-01"},
        {"name": "Оп. №9", "type": "Опора", "status": "Попередження", "desc": "Пошкоджено ізолятор після грози. Рекомендовано ремонт."},
        {"name": "Оп. №10", "type": "Опора", "status": "Норма", "desc": "ЖБ СВ-110. Огляд: 2024-05. Норма"},
    ]

if "log_data" not in st.session_state:
    st.session_state.log_data = [
        {"Час": "23.05 09:14", "Тип": "Аварія", "Об'єкт": "ТП-245", "Опис": "Відключення трансформатора, немає напруги"},
        {"Час": "23.05 08:52", "Тип": "Аварія", "Об'єкт": "Оп. №9", "Опис": "Пошкоджено ізолятор після грози"},
        {"Час": "23.05 07:30", "Тип": "Планове ТО", "Об'єкт": "ТП-12", "Опис": "Регламентне обслуговування трансформатора"},
        {"Час": "22.05 18:45", "Тип": "Ремонт", "Об'єкт": "КЛ-3", "Опис": "Замінено кабельну муфту 10 кВ"},
        {"Час": "22.05 15:20", "Тип": "Інспекція", "Об'єкт": "Оп. №11", "Опис": "Виявлено корозію на опорі 1988 р."}
    ]

if "selected_object" not in st.session_state:
    st.session_state.selected_object = st.session_state.objects[2]

if "task_closed" not in st.session_state:
    st.session_state.task_closed = False

# --- ГОЛОВНЕ МЕНЮ (ВКЛАДКИ) ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏢 Диспетчер мапи", 
    "📱 Мобільний клієнт", 
    "📊 Аналітика та KPI", 
    "📋 Журнал подій", 
    "📅 Планування ТО",
    "💾 Data Центр (Імпорт/Експорт)"
])

# ==========================================
# ВКАДКА 1: ДИСПЕТЧЕР МАПИ
# ==========================================
with tab1:
    st.title("🏢 Оперативний диспетчерський пульт")
    col_map, col_side = st.columns([3, 1])
    
    with col_map:
        st.subheader("Карта мережі (ГІС об'єкти)")
        st.markdown("##### Оберіть об'єкт для інспекції:")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("⚡ ТП-12", use_container_width=True): st.session_state.selected_object = st.session_state.objects[0]
        with c2:
            if st.button("⚡ ТП-28", use_container_width=True): st.session_state.selected_object = st.session_state.objects[1]
        with c3:
            if st.button("🚨 ТП-245 (АВАРІЯ)", use_container_width=True): st.session_state.selected_object = st.session_state.objects[2]
        with c4:
            if st.button("⚡ ТП-67", use_container_width=True): st.session_state.selected_object = st.session_state.objects[3]
                
        c5, c6, c7, _ = st.columns(4)
        with c5:
            if st.button("📍 Опора №8", use_container_width=True): st.session_state.selected_object = st.session_state.objects[4]
        with c6:
            if st.button("⚠️ Опора №9", use_container_width=True): st.session_state.selected_object = st.session_state.objects[5]
        with c7:
            if st.button("📍 Опора №10", use_container_width=True): st.session_state.selected_object = st.session_state.objects[6]

        st.info("💡 Клікніть по вузлах мережі для виведення телеметрії та швидкої генерації документів.")

    with col_side:
        obj = st.session_state.selected_object
        st.subheader("ℹ️ Панель об'єкта")
        st.markdown(f"### {obj['name']}")
        
        if "АВАРІЯ" in obj['status']:
            st.error(f"Статус: {obj['status']}")
        elif "Попередження" in obj['status']:
            st.warning(f"Статус: {obj['status']}")
        else:
            st.success(f"Статус: {obj['status']}")
            
        st.markdown(f"**Тип:** {obj['type']}")
        st.markdown(f"**Специфікація:** {obj['desc']}")
        
        st.divider()
        st.markdown("📄 **Генератор документів:**")
        
        # ДОДАНО НА МІЙ РОЗСУД: Автоматичне формування офіційного наряду-допуску
        permit_text = f"НАРЯД-ДОПУСК №{obj['name']}-2026\nНа виконання робіт на об'єкті: {obj['name']} ({obj['type']})\nСтатус: {obj['status']}\nСпецифікація: {obj['desc']}\nВідповідальний керівник: Іваненко М.\nДата створення: 23.05.2026"
        st.download_button(
            label="📄 Скачати Наряд-Допуск (.TXT)",
            data=permit_text,
            file_name=f"permit_{obj['name']}.txt",
            mime="text/plain",
            use_container_width=True
        )

# ==========================================
# ВКАДКА 2: МОБІЛЬНИЙ КЛІЄНТ
# ==========================================
with tab2:
    st.title("📱 Інтерфейс лінійної бригади")
    _, phone_col, _ = st.columns([1, 2, 1])
    with phone_col:
        st.markdown("---")
        st.markdown("<h3 style='text-align: center; color: #185FA5;'>📱 Польовий ГІС-Клієнт</h3>", unsafe_allow_html=True)
        st.info("👷 Бригада 1 | GPS: Активний (49.5521 N, 27.9612 E)")
        
        if st.session_state.task_closed:
            st.success("🎉 Завдання закрито! Звіт надіслано диспетчеру.")
            if st.button("Отримати нове завдання"):
                st.session_state.task_closed = False
                st.rerun()
        else:
            st.warning("🚨 **Поточна задача:** Аварія на ТП-245 (вул. Польова, 2.4 км)")
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🗺️ Навігація", "📄 ГІС Паспорт", "📥 Звіт"])
            with sub_tab1:
                st.write("⏱️ Час в дорозі: 13 хв | 📏 Відстань: 2.4 км")
            with sub_tab2:
                st.code("Тип: ВН-10 кВ\nТрансформатор: ТМ-400/10\nРік встановлення: 2001\nЗапобіжники: ПК-10, 3×25А", language="text")
            with sub_tab3:
                comment = st.text_area("Коментар щодо усунення пошкодження", placeholder="Наприклад: Замінено високовольтні запобіжники...")
                if st.button("✅ Виконано", use_container_width=True):
                    if comment:
                        st.session_state.task_closed = True
                        # Додаємо запис у журнал автоматично
                        st.session_state.log_data.insert(0, {"Час": "23.05 09:40", "Тип": "Ремонт", "Об'єкт": "ТП-245", "Опис": comment})
                        st.rerun()
                    else: st.error("Будь ласка, заповніть звіт перед закриттям!")
        st.markdown("---")

# ==========================================
# ВКАДКА 3: АНАЛІТИКА ТА KPI
# ==========================================
with tab3:
    st.title("📊 Аналітика надійності мережі")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Аварій цього місяця", "12", "+3 vs мин.міс")
    m2.metric("Закрито нарядів", "47", "+8")
    m3.metric("Сер. час реагування", "38 хв", "-6 хв від плану", delta_color="inverse")
    m4.metric("Об'єктів на ТО", "7", "Прострочено: 2", delta_color="off")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    categories = ['Підстанції', 'Кабелі', 'Опори', 'Трансф.']
    values = [12, 8, 5, 4]
    ax1.bar(categories, values, color=['#ef4444', '#f59e0b', '#38bdf8', '#10b981'])
    ax1.set_title("Аварії за типами об'єктів (2026)", fontsize=10)
    
    labels = ['Відкриті', 'В роботі', 'Закриті']
    sizes = [5, 8, 34]
    ax2.pie(sizes, labels=labels, colors=['#ef4444', '#f59e0b', '#10b981'], autopct='%1.1f%%', startangle=90)
    ax2.set_title("Статус поточних нарядів", fontsize=10)
    st.pyplot(fig)

    # ДОДАНО НА МІЙ РОЗСУД: Модуль прогнозування та оптимізації навантаження "SmartSport VDPU" / SmartGrid AI
    st.divider()
    st.subheader("🤖 Модуль предиктивного балансування SmartGrid AI")
    st.markdown("Система розраховує математичні моделі оптимального розподілу потужності мережі:")
    grid_slider = st.slider("Симулювати пікове навантаження на систему (%)", 50, 150, 95)
    if grid_slider > 110:
        st.error(f"🚨 КРИТИЧНИЙ РІВЕНЬ ({grid_slider}%). Рекомендовано автоматичне перепідключення резервних ліній ТП-12 -> ТП-28.")
    else:
        st.success(f"🟢 Стабільний рівень ({grid_slider}%). Магістральні ГІС лінії працюють в оптимізованому енергоефективному режимі.")

# ==========================================
# ВКАДКА 4: ЖУРНАЛ ПОДІЙ
# ==========================================
with tab4:
    st.title("📋 Цифровий журнал подій диспетчера")
    df = pd.DataFrame(st.session_state.log_data)
    col_f1, col_f2 = st.columns(2)
    with col_f1: search_query = st.text_input("🔍 Пошук події за об'єктом", "")
    with col_f2: type_filter = st.selectbox("Фільтр за типом", ["Усі типи", "Аварія", "Планове ТО", "Ремонт", "Інспекція"])
        
    if type_filter != "Усі типи": df = df[df["Тип"] == type_filter]
    if search_query: df = df[df["Об'єкт"].str.contains(search_query, case=False)]
        
    st.dataframe(df, use_container_width=True, hide_index=True)

# ==========================================
# ВКАДКА 5: ПЛАНУВАННЯ ТО
# ==========================================
with tab5:
    st.title("📅 Графік планового технічного обслуговування")
    st.info("📅 **[06.05.2026]** — **ТП-12** | Регламентне ТО силового трансформатора")
    st.success("📅 **[19.05.2026]** — **КЛ-3** | Діагностика ізоляції кабелю 10 кВ")
    st.error("📅 **[23.05.2026]** — **ТП-245** | Терміновий ремонт за результатами аварійного виїзду")
    st.warning("📅 **[28.05.2026]** — **Оп. №11** | Заміна застарілої стійки опори")

# ==========================================
# ВКАДКА 6: DATA ЦЕНТР (ІМПОРТ / ЕКСПОРТ) — НОВИЙ ФУНКЦІОНАЛ
# ==========================================
with tab6:
    st.title("💾 Центр синхронізації та обміну даними (Імпорт/Експорт)")
    st.markdown("Цей модуль дозволяє вивантажувати поточний стан журналу подій або завантажувати нові списки ГІС-об'єктів/подій у різних форматах.")
    
    curr_df = pd.DataFrame(st.session_state.log_data)
    
    exp_col, imp_col = st.columns(2)
    
    with exp_col:
        st.subheader("📤 Експорт даних із системи")
        st.write("Оберіть формат для вивантаження поточного журналу подій:")
        
        # 1. Експорт в CSV
        csv_data = curr_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачати у форматі Excel CSV (.csv)",
            data=csv_data,
            file_name="gis_log_export.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # 2. Експорт в Excel (через бінарний потік)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            curr_df.to_excel(writer, index=False, sheet_name='Журнал Подій')
        st.download_button(
            label="📥 Скачати у форматі MS Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="gis_log_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        # 3. Експорт в JSON
        json_string = json.dumps(st.session_state.log_data, indent=4, ensure_ascii=False)
        st.download_button(
            label="📥 Скачати у структурному форматі ГІС JSON (.json)",
            data=json_string.encode('utf-8'),
            file_name="gis_log_export.json",
            mime="application/json",
            use_container_width=True
        )

    with imp_col:
        st.subheader("📥 Імпорт зовнішніх даних")
        st.write("Завантажте файл (.csv, .xlsx або .json), щоб розширити або оновити поточний журнал системи:")
        
        uploaded_file = st.file_uploader("Оберіть файл для імпорту", type=["csv", "xlsx", "json"])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    imported_df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith('.xlsx'):
                    imported_df = pd.read_excel(uploaded_file)
                elif uploaded_file.name.endswith('.json'):
                    imported_data = json.load(uploaded_file)
                    imported_df = pd.DataFrame(imported_data)
                
                st.success("✅ Файл успішно зчитано!")
                st.markdown("**Попередній перегляд імпортованих даних:**")
                st.dataframe(imported_df.head(3), use_container_width=True)
                
                if st.button("🔄 Інтегрувати дані в робочий журнал системи"):
                    # Перетворюємо назад у список словників та додаємо до поточної сесії
                    new_records = imported_df.to_dict(orient='records')
                    st.session_state.log_data = new_records + st.session_state.log_data
                    st.success(f"Додано {len(new_records)} нових записів у журнал подій!")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Помилка зчитування файлу: {e}. Перевірте відповідність колонок ('Час', 'Тип', 'Об'єкт', 'Опис').")
