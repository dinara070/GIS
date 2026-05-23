import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import io
import datetime

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(
    page_title="ГІС Диспетчерська Система Регіональних Електромереж v3.0",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Темна тема для графіків Matplotlib
plt.style.use('dark_background')

# --- ІНІЦІАЛІЗАЦІЯ ДАНИХ ОРГСТРУКТУРИ ---
if "org_structure" not in st.session_state:
    st.session_state.org_structure = {
        "СО «Вінницькі міські ЕМ»": {"база": "м. Вінниця", "дільниці": ["Вінницька міська дільниця"]},
        "СО «Вінницькі центральні ЕМ»": {"база": "м. Вінниця", "дільниці": ["Вінницька", "Літинська", "Тиврівська"]},
        "СО «Вінницькі східні ЕМ»": {"база": "м. Іллінці", "дільниці": ["Іллінецька", "Липовецька", "Немирівська", "Оратівська", "Погребищенська"]},
        "СО «Гайсинські ЕМ»": {"база": "м. Гайсин", "дільниці": ["Гайсинська", "Бершадська", "Теплицька", "Тростянецька", "Чечельницька"]},
        "СО «Жмеринські ЕМ»": {"база": "м. Жмеринка", "дільниці": ["Жмеринська", "Барська", "Шаргородська (повне охоплення громади)"]},
        "СО «Хмільницькі ЕМ»": {"база": "м. Хмільник", "дільниці": ["Хмільницька", "Калинівська", "Козятинська"]},
        "СО «Могилів-Подільські ЕМ»": {"база": "м. Могилів-Подільський", "дільниці": ["Могилів-Подільська", "Мурованокуриловецька", "Чернівецька", "Ямпільська"]},
        "СО «Тульчинські ЕМ»": {"база": "м. Тульчин", "дільниці": ["Тульчинська", "Крижопільська", "Піщанська", "Томашпільська"]}
    }

# --- ІНІЦІАЛІЗАЦІЯ ГІС ОБ'ЄКТІВ ---
if "objects" not in st.session_state:
    st.session_state.objects = [
        {"name": "ТП-12", "type": "Підстанція", "status": "Нормальна", "desc": "ВН-110 кВ. Обслуговує: СО Вінницькі міські ЕМ", "latitude": 49.2331, "longitude": 28.4682, "criticality": "Висока", "subdivision": "СО «Вінницькі міські ЕМ»"},
        {"name": "ТП-28", "type": "Підстанція", "status": "Нормальна", "desc": "ВН-35 кВ. Літинський напрямок", "latitude": 49.2425, "longitude": 28.4810, "criticality": "Середня", "subdivision": "СО «Вінницькі центральні ЕМ»"},
        {"name": "ТП-245", "type": "Підстанція", "status": "АВАРІЯ", "desc": "ВН-10 кВ. Потребує термінової заміни обладнання", "latitude": 49.2210, "longitude": 28.4422, "criticality": "Критична", "subdivision": "СО «Вінницькі міські ЕМ»"},
        {"name": "ТП-Шаргород-100", "type": "Підстанція", "status": "Нормальна", "desc": "ВН-35/10 кВ. Шаргородська дільниця. Технічне обслуговування мереж та ліній громади.", "latitude": 48.7364, "longitude": 28.0822, "criticality": "Висока", "subdivision": "СО «Жмеринські ЕМ»"},
        {"name": "ЦОК Шаргород", "type": "Центр клієнтів", "status": "Нормальна", "desc": "Фізичне звернення громадян: приєднання, техумови, документація.", "latitude": 48.7390, "longitude": 28.0805, "criticality": "Низька", "subdivision": "СО «Жмеринські ЕМ»"},
        {"name": "Оп. №9", "type": "Опора", "status": "Попередження", "desc": "Пошкоджено ізолятор після грози. Калинівський напрямок", "latitude": 49.4410, "longitude": 28.5122, "criticality": "Середня", "subdivision": "СО «Хмільницькі ЕМ»"}
    ]

if "log_data" not in st.session_state:
    st.session_state.log_data = [
        {"Час": "23.05 09:14", "Тип": "Аварія", "Об'єкт": "ТП-245", "Опис": "Відключення трансформатора, немає напруги", "Критичність": "Критична"},
        {"Час": "23.05 08:52", "Тип": "Аварія", "Об'єкт": "Оп. №9", "Опис": "Пошкоджено ізолятор після грози у Калинівському районі", "Критичність": "Середня"},
        {"Час": "23.05 07:30", "Тип": "Планове ТО", "Об'єкт": "ТП-Шаргород-100", "Опис": "Профілактичний огляд вимикачів лінії Шаргородської дільниці", "Критичність": "Висока"},
        {"Час": "22.05 18:45", "Тип": "Ремонт", "Об'єкт": "КЛ-3", "Опис": "Замінено кабельну муфту 10 кВ", "Критичність": "Висока"},
        {"Час": "22.05 15:20", "Тип": "Інспекція", "Об'єкт": "Оп. №11", "Опис": "Виявлено корозію на опорі 1988 р.", "Критичність": "Низька"}
    ]

if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = [
        {"Дата": "2026-05-24", "Об'єкт": "ТП-12", "Вид робіт": "Регламентне ТО силового трансформатора", "Статус": "Заплановано"},
        {"Дата": "2026-05-26", "Об'єкт": "ТП-Шаргород-100", "Вид робіт": "Діагностика шин розподільчого пристрою", "Статус": "Підготовка"},
        {"Дата": "2026-05-28", "Об'єкт": "Оп. №11", "Вид робіт": "Заміна застарілої стійки опори", "Статус": "Заплановано"}
    ]

if "selected_object" not in st.session_state:
    st.session_state.selected_object = st.session_state.objects[3] # Шаргород за замовчуванням

if "task_closed" not in st.session_state:
    st.session_state.task_closed = False

# --- ГОЛОВНЕ МЕНЮ ПРОГРАМИ ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏢 Диспетчер мапи", 
    "📱 Мобільний клієнт",
    "🏛️ Структура компанії (ЕМ)", 
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
        mode = st.radio("🛠️ Шари візуалізації мережі:", ["Стандартний ГІС", "Зони структурних одиниць (СО)"], horizontal=True)
        
        map_df = pd.DataFrame(st.session_state.objects)
        st.map(map_df, size=40)
        
        st.markdown("##### 🔍 Швидкий вибір ГІС об'єкта області:")
        obj_names = [o["name"] for o in st.session_state.objects]
        try:
            curr_index = obj_names.index(st.session_state.selected_object["name"])
        except ValueError:
            curr_index = 0
            
        selected_name = st.selectbox("Оберіть вузол для виведення телеметрії:", obj_names, index=curr_index)
        
        for o in st.session_state.objects:
            if o["name"] == selected_name:
                st.session_state.selected_object = o

    with col_side:
        obj = st.session_state.selected_object
        st.subheader("ℹ️ Телеметрія та Управління")
        st.markdown(f"### {obj.get('name', 'Невідомий об\'єкт')}")
        
        status = obj.get('status', 'Нормальна')
        if "АВАРІЯ" in status: st.error(f"Статус: {status}")
        elif "Попередження" in status: st.warning(f"Статус: {status}")
        else: st.success(f"Статус: {status}")
            
        criticality = obj.get('criticality', 'Середня')
        st.markdown(f"**Підпорядкування:** `{obj.get('subdivision', 'Центральний апарат')}`")
        st.markdown(f"**Важливість вузла:** `{criticality}`")
        st.markdown(f"**Координати:** `{obj.get('latitude', 0.0):.4f}° N, {obj.get('longitude', 0.0):.4f}° E`")
        st.markdown(f"**Технічні параметри:** {obj.get('desc', 'Немає опису')}")
        
        st.divider()
        st.markdown("🎛️ **Команди дистанційного керування:**")
        if st.button("⚡ Вимкнути фідер (SCADA)", use_container_width=True):
            st.toast(f"🚨 Сигнал оперативної комутації надіслано на {obj.get('name')}!")
            st.session_state.log_data.insert(0, {
                "Час": datetime.datetime.now().strftime("%d.%m %H:%M"),
                "Тип": "Ремонт",
                "Об'єкт": obj.get('name'),
                "Опис": f"Дистанційне оперативне керування комутаційним апаратом з пульта.",
                "Критичність": "Висока"
            })
            
        if st.button("📲 Передати наряд черговому майстру дільниці", use_container_width=True):
            st.toast(f"📡 Дані надіслано в базу відповідної структурної одиниці ЕМ!")
            
        permit_text = f"НАРЯД-ДОПУСК №{obj.get('name', 'ТП')}-2026\nОб'єкт: {obj.get('name')} ({obj.get('type')})\nПідрозділ: {obj.get('subdivision')}\nКритичність: {criticality}\nКоординати: {obj.get('latitude')}, {obj.get('longitude')}\nОпис: {obj.get('desc')}\nЗгенеровано системою Вінницяобленерго."
        st.download_button(
            label="📄 Завантажити Наряд-Допуск (.txt)",
            data=permit_text,
            file_name=f"permit_{obj.get('name', 'TP')}.txt",
            mime="text/plain",
            use_container_width=True
        )

# ==========================================
# ВКАДКА 2: МОБІЛЬНИЙ КЛІЄНТ
# ==========================================
with tab2:
    st.title("📱 Цифровий кабінет лінійної бригади")
    _, phone_col, _ = st.columns([1, 2, 1])
    with phone_col:
        st.markdown("---")
        st.markdown("<h3 style='text-align: center; color: #185FA5;'>📱 Мобільна бригада АТ «Вінницяобленерго»</h3>", unsafe_allow_html=True)
        st.info("👷 Бригада №1 (ОВБ Центр) | GPS: Активний")
        
        if st.session_state.task_closed:
            st.success("🎉 Наряд успішно закрито та підписано ЕЦП!")
            if st.button("🔄 Оновити стрічку завдань"):
                st.session_state.task_closed = False
                st.rerun()
        else:
            st.warning("📋 **Поточна задача СО «Жмеринські ЕМ» (Шаргородська дільниця):**")
            st.markdown("**Об'єкт:** ТП-Шаргород-100  \n**Завдання:** Планова діагностика шин та огляд вимикачів лінії.")
            
            tb_1 = st.checkbox("Заземлення встановлено")
            tb_2 = st.checkbox("Плакати з техніки безпеки розвішано")
            
            comment = st.text_area("Звіт про виконану роботу:")
            if st.button("🚀 Закрити наряд-допуск", use_container_width=True):
                if tb_1 and tb_2 and comment:
                    st.session_state.task_closed = True
                    st.session_state.log_data.insert(0, {
                        "Час": datetime.datetime.now().strftime("%d.%m %H:%M"),
                        "Тип": "Планове ТО",
                        "Об'єкт": "ТП-Шаргород-100",
                        "Опис": f"[Шаргородська дільниця]: {comment}",
                        "Критичність": "Висока"
                    })
                    st.rerun()
                else: st.error("Заповніть чек-лист безпеки та коментар!")
        st.markdown("---")

# ==========================================
# ВКАДКА 3: СТРУКТУРА КОМПАНІЇ (ЕМ та ДІЛЬНИЦІ)
# ==========================================
with tab3:
    st.title("🏛️ Організаційна структура та зони обслуговування АТ «Вінницяобленерго»")
    st.markdown("Розподіл компанії за напрямками на базі адміністративних районів області:")
    
    col_str, col_shargorod = st.columns([1.8, 1.2])
    
    with col_str:
        st.subheader("📁 Структурні Одиниці (СО)")
        for em, info in st.session_state.org_structure.items():
            with st.expander(f"📌 {em} (База: {info['база']})"):
                st.markdown("**Зона обслуговування (Покриття дільниць):**")
                for sub in info["дільниці"]:
                    st.write(f"• {sub} дільниця")
                    
    with col_shargorod:
        st.subheader("📍 Особливий статус: Шаргородський регіон")
        st.info("ℹ️ Шаргород та колишній Шаргородський район повністю охоплюються АТ «Вінницяобленерго». Адміністративно Шаргородська дільниця входить до складу структури СО «Жмеринські електричні мережі», оскільки Жмеринка є більшим опорним вузлом для цього регіону.")
        
        box_sh = st.container(border=True)
        box_sh.markdown("### 🏢 Безпосередньо у місті Шаргород діють:")
        box_sh.markdown("""
        * **🔧 Шаргородська дільниця** — відповідає за технічне обслуговування мереж, поточний та капітальний ремонт ліній і підстанцій у межах громади.
        * **👥 Центр обслуговування клієнтів (ЦОК)** — розташований безпосередньо у місті Шаргород. Здійснює фізичний прийом споживачів (фізичних та юридичних осіб) для вирішення питань щодо:
          * Нових приєднань до мереж
          * Отримання технічних умов (ТУ)
          * Встановлення та параметризації лічильників
          * Узгодження договірної документації
        """)
        
        st.caption("🗺️ Локація сервісної інфраструктури в м. Шаргород:")
        sh_df = pd.DataFrame([
            {"name": "ТП-Шаргород-100", "latitude": 48.7364, "longitude": 28.0822},
            {"name": "ЦОК Шаргород", "latitude": 48.7390, "longitude": 28.0805}
        ])
        st.map(sh_df, zoom=13, size=45)

# ==========================================
# ВКАДКА 4: АНАЛІТИКА ТА KPI
# ==========================================
with tab4:
    st.title("📊 Апарат інтелектуальної аналітики")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Індекс надійності SAIDI", "42.5 хв/рік", "-3.2 хв від плану", delta_color="inverse")
    m2.metric("Індекс частоти вимкнень SAIFI", "1.14 од/рік", "+0.02", delta_color="inverse")
    m3.metric("Загальна потужність споживання області", "148.5 МВт", "Норма")
    m4.metric("Коефіцієнт корисного використання", "94.2%", "+0.5%")
    
    st.markdown("### 📈 Прогнозування добового навантаження мережі та Аварійність")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    
    hours = [f"{i}:00" for i in range(0, 25, 4)]
    actual_load = [65, 50, 85, 110, 140, 148, 90]
    predicted_load = [62, 53, 80, 115, 138, 145, 95]
    ax1.plot(hours, actual_load, label="Фактичне навантаження (МВт)", color="#38bdf8", marker="o", linewidth=2)
    ax1.plot(hours, predicted_load, label="Прогноз SmartGrid AI", color="#a855f7", linestyle="--")
    ax1.set_title("Прогноз графіка навантаження", fontsize=10)
    ax1.legend()
    ax1.grid(True, alpha=0.2)
    
    current_logs_df = pd.DataFrame(st.session_state.log_data)
    types_distribution = current_logs_df["Тип"].value_counts()
    ax2.pie(types_distribution.values, labels=types_distribution.index, colors=['#ef4444', '#f59e0b', '#10b981', '#38bdf8', '#bc5090'], autopct='%1.1f%%', startangle=90)
    ax2.set_title("Розподіл подій у журналі", fontsize=10)
    st.pyplot(fig)

# ==========================================
# ВКАДКА 5: ЖУРНАЛ ПОДІЙ
# ==========================================
with tab5:
    st.title("📋 Цифровий журнал подій диспетчера")
    
    df = pd.DataFrame(st.session_state.log_data)
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: search_query = st.text_input("🔍 Швидкий фільтр за назвою об'єкта", "")
    with col_f2: type_filter = st.selectbox("Тип події", ["Усі типи", "Аварія", "Планове ТО", "Ремонт", "Інспекція"])
    with col_f3: crit_filter = st.selectbox("Ступінь критичності", ["Усі рівні", "Критична", "Висока", "Середня", "Низька"])
        
    if type_filter != "Усі типи": df = df[df["Тип"] == type_filter]
    if crit_filter != "Усі рівні" and "Критичність" in df.columns: df = df[df["Критичність"] == crit_filter]
    if search_query: df = df[df["Об'єкт"].str.contains(search_query, case=False)]
        
    st.dataframe(df, use_container_width=True, hide_index=True)

# ==========================================
# ВКАДКА 6: ПЛАНУВАННЯ ТО
# ==========================================
with tab6:
    st.title("📅 Графік планового технічного обслуговування")
    
    st.subheader("➕ Додати нове завдання до плану:")
    col_in1, col_in2, col_in3 = st.columns(3)
    with col_in1: plan_obj = st.selectbox("Вузол для ТО:", [o["name"] for o in st.session_state.objects])
    with col_in2: plan_date = st.date_input("Дата робіт", datetime.date.today() + datetime.timedelta(days=1))
    with col_in3: plan_desc = st.text_input("Опис регламентних робіт:", placeholder="Введіть опис робіт...")
        
    if st.button("➕ Додати до графіка робіт", use_container_width=True):
        if plan_desc:
            st.session_state.schedule_data.append({
                "Дата": str(plan_date), 
                "Об'єкт": plan_obj, 
                "Вид робіт": plan_desc, 
                "Статус": "Заплановано"
            })
            st.success(f"✅ Роботи по {plan_obj} успішно додано!")
            st.rerun()
        else:
            st.error("Будь ласка, вкажіть вид робіт.")
            
    st.divider()
    st.subheader("📋 Поточний графік робіт:")
    st.table(pd.DataFrame(st.session_state.schedule_data))

# ==========================================
# ВКАДКА 7: DATA ЦЕНТР
# ==========================================
with tab7:
    st.title("💾 Data-Центр синхронізації та обміну (Імпорт/Експорт)")
    
    curr_df = pd.DataFrame(st.session_state.log_data)
    exp_col, imp_col = st.columns(2)
    
    with exp_col:
        st.subheader("📤 Експорт даних із системи")
        
        csv_data = curr_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачати Excel CSV (.csv)",
            data=csv_data,
            file_name="vinnitsaoblenergo_export.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            curr_df.to_excel(writer, index=False, sheet_name='Журнал Подій')
        st.download_button(
            label="📥 Скачати книгу MS Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="vinnitsaoblenergo_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with imp_col:
        st.subheader("📥 Імпорт зовнішніх даних")
        uploaded_file = st.file_uploader("Оберіть файл конфігурації мережі", type=["csv", "xlsx", "json"])
        if uploaded_file is not None:
            st.success("✅ Структуру файлу успішно розпізнано! Дані готові до інтеграції.")
