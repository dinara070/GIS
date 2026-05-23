import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(
    page_title="ГІС Диспетчерська Система Регіональних Електромереж v2.0",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Темна тема для графіків Matplotlib, щоб пасувала до інтерфейсу
plt.style.use('dark_background')

# --- ДАНІ ПРОЕКТУ ---
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

if "selected_object" not in st.session_state:
    st.session_state.selected_object = st.session_state.objects[2]  # За замовчуванням ТП-245

if "task_closed" not in st.session_state:
    st.session_state.task_closed = False

# --- ГОЛОВНЕ МЕНЮ (ВКЛАДКИ) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏢 Диспетчер мапи", 
    "📱 Мобільний клієнт", 
    "📊 Аналітика та KPI", 
    "📋 Журнал подій", 
    "📅 Планування ТО"
])

# ==========================================
# ВКАДКА 1: ДИСПЕТЧЕР МАПИ
# ==========================================
with tab1:
    st.title("🏢 Оперативний диспетчерський пульт")
    
    col_map, col_side = st.columns([3, 1])
    
    with col_map:
        st.subheader("Карта мережі (ГІС об'єкти)")
        # Створюємо інтерактивні кнопки-маркери заміни живої карти
        st.markdown("##### Оберіть об'єкт для інспекції:")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("⚡ ТП-12", use_container_width=True):
                st.session_state.selected_object = st.session_state.objects[0]
        with c2:
            if st.button("⚡ ТП-28", use_container_width=True):
                st.session_state.selected_object = st.session_state.objects[1]
        with c3:
            if st.button("🚨 ТП-245 (АВАРІЯ)", use_container_width=True):
                st.session_state.selected_object = st.session_state.objects[2]
        with c4:
            if st.button("⚡ ТП-67", use_container_width=True):
                st.session_state.selected_object = st.session_state.objects[3]
                
        c5, c6, c7, _ = st.columns(4)
        with c5:
            if st.button("📍 Опора №8", use_container_width=True):
                st.session_state.selected_object = st.session_state.objects[4]
        with c6:
            if st.button("⚠️ Опора №9", use_container_width=True):
                st.session_state.selected_object = st.session_state.objects[5]
        with c7:
            if st.button("📍 Опора №10", use_container_width=True):
                st.session_state.selected_object = st.session_state.objects[6]

        st.info("💡 У Streamlit-версії карти вище представлені вузли розподільчої мережі. Клікніть по будь-якому з них для виведення телеметрії в бічну панель.")

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
        st.markdown("**Екіпажі бригад:**")
        st.caption("🟢 Бригада 1: В роботі (ТП-245)")
        st.caption("🔵 Бригада 2: Вільна")
        if st.button("Призначити Бригаду 2 ↗", use_container_width=True):
            st.toast("Бригаду 2 успішно відправлено на об'єкт!")

# ==========================================
# ВКАДКА 2: МОБІЛЬНИЙ КЛІЄНТ
# ==========================================
with tab2:
    st.title("📱 Інтерфейс лінійної бригади")
    
    # Центруємо мобільний пристрій
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
                st.write("**Маршрут побудовано:**")
                st.write("⏱️ Час в дорозі: 13 хв")
                st.write("📏 Відстань: 2.4 км")
                
            with sub_tab2:
                st.write("**Технічні характеристики ТП-245:**")
                st.code("Тип: ВН-10 кВ\nТрансформатор: ТМ-400/10\nРік встановлення: 2001\nЗапобіжники: ПК-10, 3×25А", language="text")
                
            with sub_tab3:
                st.write("**Закриття наряду:**")
                comment = st.text_area("Коментар щодо усунення пошкодження", placeholder="Наприклад: Замінено високовольтні запобіжники...")
                if st.button("✅ Виконано", use_container_width=True):
                    if comment:
                        st.session_state.task_closed = True
                        st.rerun()
                    else:
                        st.error("Будь ласка, заповніть звіт перед закриттям!")
        st.markdown("---")

# ==========================================
# ВКАДКА 3: АНАЛІТИКА ТА KPI
# ==========================================
with tab3:
    st.title("📊 Аналітика надійності мережі")
    
    # KPIs
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Аварій цього місяця", "12", "+3 vs мин.міс")
    m2.metric("Закрито нарядів", "47", "+8")
    m3.metric("Сер. час реагування", "38 хв", "-6 хв від плану", delta_color="inverse")
    m4.metric("Об'єктів на ТО", "7", "Прострочено: 2", delta_color="off")
    
    st.write("")
    
    # Побудова графіків через Matplotlib
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    # Графік 1
    categories = ['Підстанції', 'Кабелі', 'Опори', 'Трансф.']
    values = [12, 8, 5, 4]
    ax1.bar(categories, values, color=['#ef4444', '#f59e0b', '#38bdf8', '#10b981'])
    ax1.set_title("Аварії за типами об'єктів (2026)", fontsize=10)
    
    # Графік 2
    labels = ['Відкриті', 'В роботі', 'Закриті']
    sizes = [5, 8, 34]
    ax2.pie(sizes, labels=labels, colors=['#ef4444', '#f59e0b', '#10b981'], autopct='%1.1f%%', startangle=90)
    ax2.set_title("Статус поточних нарядів", fontsize=10)
    
    st.pyplot(fig)

# ==========================================
# ВКАДКА 4: ЖУРНАЛ ПОДІЙ
# ==========================================
with tab4:
    st.title("📋 Цифровий журнал подій диспетчера")
    
    log_data = [
        {"Час": "23.05 09:14", "Тип": "Аварія", "Об'єкт": "ТП-245", "Опис": "Відключення трансформатора, немає напруги"},
        {"Час": "23.05 08:52", "Тип": "Аварія", "Об'єкт": "Оп. №9", "Опис": "Пошкоджено ізолятор після грози"},
        {"Час": "23.05 07:30", "Тип": "Планове ТО", "Об'єкт": "ТП-12", "Опис": "Регламентне обслуговування трансформатора"},
        {"Час": "22.05 18:45", "Тип": "Ремонт", "Об'єкт": "КЛ-3", "Опис": "Замінено кабельну муфту 10 кВ"},
        {"Час": "22.05 15:20", "Тип": "Інспекція", "Об'єкт": "Оп. №11", "Опис": "Виявлено корозію на опорі 1988 р."}
    ]
    df = pd.DataFrame(log_data)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        search_query = st.text_input("🔍 Пошук події за об'єктом", "")
    with col_f2:
        type_filter = st.selectbox("Фільтр за типом", ["Усі типи", "Аварія", "Планове ТО", "Ремонт", "Інспекція"])
        
    # Фільтрація даних dataframe
    if type_filter != "Усі типи":
        df = df[df["Тип"] == type_filter]
    if search_query:
        df = df[df["Об'єкт"].str.contains(search_query, case=False)]
        
    st.dataframe(df, use_container_width=True, hide_index=True)

# ==========================================
# ВКАДКА 5: ПЛАНУВАННЯ ТО
# ==========================================
with tab5:
    st.title("📅 Графік планового технічного обслуговування")
    
    st.markdown("### Найближчі регламентні роботи:")
    
    st.info("📅 **[06.05.2026]** — **ТП-12** | Регламентне ТО силового трансформатора (Статус: Заплановано)")
    st.success("📅 **[19.05.2026]** — **КЛ-3** | Діагностика ізоляції кабелю 10 кВ (Статус: Виконано успішно)")
    st.error("📅 **[23.05.2026]** — **ТП-245** | Терміновий ремонт за результатами аварійного виїзду")
    st.warning("📅 **[28.05.2026]** — **Оп. №11** | Заміна дерев'яної стійки опори (Статус: Підготовка тех.документації)")
    
    st.write("")
    if st.button("➕ Додати нову регламентну задачу в календар"):
        st.toast("Функція додавання подій активована диспетчером.")
