import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import io
import datetime
import random as _rnd

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

st.set_page_config(
    page_title="ГІС Диспетчерська Система Регіональних Електромереж v5.0",
    layout="wide",
    initial_sidebar_state="expanded"
)

plt.style.use('dark_background')

# ==========================================
# СИСТЕМА АВТОРИЗАЦІЇ
# ==========================================
USERS_DB = {
    "dispatcher": {
        "password": "disp2026",
        "role": "dispatcher",
        "display_name": "Диспетчер Коваленко О.В.",
        "subdivision": "Центральний диспетчерський пункт"
    },
    "admin": {
        "password": "admin2026",
        "role": "admin",
        "display_name": "Адміністратор Петренко І.М.",
        "subdivision": "ІТ-відділ АТ «Вінницяобленерго»"
    },
    "brigade1": {
        "password": "brigade1",
        "role": "brigade",
        "display_name": "Бригадир Сидоренко В.П.",
        "subdivision": "Бригада №1 (ОВБ Центр)"
    },
    "brigade2": {
        "password": "brigade2",
        "role": "brigade",
        "display_name": "Бригадир Мельник Т.С.",
        "subdivision": "Бригада №2 (Шаргородська дільниця)"
    },
}

ROLE_LABELS = {
    "dispatcher": "👷 Диспетчер",
    "admin": "🔑 Адміністратор",
    "brigade": "🪖 Монтер / Мобільна бригада"
}

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "login_error" not in st.session_state:
    st.session_state.login_error = ""

def do_login(username, password):
    user = USERS_DB.get(username.strip().lower())
    if user and user["password"] == password:
        st.session_state.authenticated = True
        st.session_state.current_user = {
            "login": username, "role": user["role"],
            "display_name": user["display_name"], "subdivision": user["subdivision"]
        }
        st.session_state.login_error = ""
    else:
        st.session_state.login_error = "❌ Невірний логін або пароль. Спробуйте ще раз."

def do_logout():
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.login_error = ""

if not st.session_state.authenticated:
    col_l, col_center, col_r = st.columns([1, 1.4, 1])
    with col_center:
        st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1rem 0;'>
            <div style='font-size: 3rem;'>⚡</div>
            <h2 style='color: #185FA5; margin-bottom: 0;'>АТ «Вінницяобленерго»</h2>
            <p style='color: #555; font-size: 0.9rem; margin-top: 0.3rem;'>
                ГІС Диспетчерська Система v5.0 — Вхід до системи
            </p>
        </div>
        """, unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### 🔐 Авторизація")
            username_input = st.text_input("Логін користувача", placeholder="Введіть логін...")
            password_input = st.text_input("Пароль", type="password", placeholder="Введіть пароль...")
            if st.session_state.login_error:
                st.error(st.session_state.login_error)
            if st.button("▶️ Увійти до системи", use_container_width=True, type="primary"):
                do_login(username_input, password_input)
                st.rerun()
        st.markdown("""
        <div style='text-align:center; margin-top: 1.5rem;'>
            <p style='color: #888; font-size: 0.78rem;'>
                🔒 Система розмежування доступу за ролями.<br>
                Для отримання облікових даних зверніться до ІТ-відділу.
            </p>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("ℹ️ Тестові облікові записи (для демо)", expanded=False):
            st.markdown("""
            | Логін | Пароль | Роль |
            |---|---|---|
            | `dispatcher` | `disp2026` | 👷 Диспетчер |
            | `admin` | `admin2026` | 🔑 Адміністратор |
            | `brigade1` | `brigade1` | 🪖 Монтер (Бригада №1) |
            | `brigade2` | `brigade2` | 🪖 Монтер (Бригада №2) |
            """)
    st.stop()

current_user = st.session_state.current_user
user_role = current_user["role"]

with st.sidebar:
    st.markdown(f"### {ROLE_LABELS.get(user_role, '👤 Користувач')}")
    st.markdown(f"**{current_user['display_name']}**")
    st.markdown(f"*{current_user['subdivision']}*")
    st.divider()
    st.markdown(f"🟢 Сеанс активний  \n`{datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}`")
    if st.button("🚪 Вийти з системи", use_container_width=True):
        do_logout()
        st.rerun()

# ==========================================
# ІНІЦІАЛІЗАЦІЯ ДАНИХ
# ==========================================
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
    st.session_state.selected_object = st.session_state.objects[3]
if "task_closed" not in st.session_state:
    st.session_state.task_closed = False

# ==========================================
# ГОЛОВНЕ МЕНЮ
# ==========================================
TAB_DEFINITIONS = {
    "dispatcher_tabs": [
        ("🏠 Головна", "home"), ("🗺️ Диспетчер мапи", "map"), ("📱 Мобільний клієнт", "mobile"),
        ("🏛️ Структура компанії", "structure"), ("📊 Аналітика та KPI", "analytics"),
        ("📋 Журнал подій", "log"), ("📅 Планування ТО", "schedule"),
    ],
    "admin_tabs": [
        ("🏠 Головна", "home"), ("🗺️ Диспетчер мапи", "map"), ("📱 Мобільний клієнт", "mobile"),
        ("🏛️ Структура компанії", "structure"), ("📊 Аналітика та KPI", "analytics"),
        ("📋 Журнал подій", "log"), ("📅 Планування ТО", "schedule"),
        ("💾 Data Центр", "data"), ("👥 Управління доступом", "users"),
    ],
    "brigade_tabs": [
        ("🏠 Головна", "home"), ("📱 Мобільний клієнт", "mobile"),
    ],
}
ROLE_TO_TAB_SET = {"dispatcher": "dispatcher_tabs", "admin": "admin_tabs", "brigade": "brigade_tabs"}
active_tabs = TAB_DEFINITIONS[ROLE_TO_TAB_SET.get(user_role, "brigade_tabs")]
tab_labels = [t[0] for t in active_tabs]
tab_keys   = [t[1] for t in active_tabs]
rendered_tabs = st.tabs(tab_labels)
tab_map = dict(zip(tab_keys, rendered_tabs))

# ==========================================
# ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ FOLIUM ГІС
# ==========================================
def get_marker_color(status):
    if "АВАРІЯ" in status:        return "red"
    if "Попередження" in status:  return "orange"
    return "green"

def get_marker_icon(obj_type):
    return {"Підстанція": "bolt", "Опора": "map-pin", "Центр клієнтів": "users"}.get(obj_type, "circle-info")

def build_popup_html(obj):
    status = obj.get("status", "Нормальна")
    color_map = {"АВАРІЯ": "#ef4444", "Попередження": "#f59e0b", "Нормальна": "#10b981"}
    badge_color = next((v for k, v in color_map.items() if k in status), "#10b981")
    return f"""
    <div style="font-family:sans-serif;min-width:230px;padding:4px 2px">
      <b style="font-size:14px">{obj['name']}</b>
      <span style="float:right;background:{badge_color};color:#fff;border-radius:4px;
                   padding:1px 7px;font-size:11px">{status}</span>
      <hr style="margin:6px 0">
      <table style="width:100%;font-size:12px;border-collapse:collapse">
        <tr><td style="color:#666;padding:2px 0">Тип:</td><td><b>{obj.get('type','—')}</b></td></tr>
        <tr><td style="color:#666;padding:2px 0">Критичність:</td><td><b>{obj.get('criticality','—')}</b></td></tr>
        <tr><td style="color:#666;padding:2px 0">СО:</td><td>{obj.get('subdivision','—')}</td></tr>
        <tr><td style="color:#666;padding:2px 0;vertical-align:top">Опис:</td>
            <td style="color:#333">{obj.get('desc','—')}</td></tr>
        <tr><td style="color:#666;padding:2px 0">Координати:</td>
            <td>{obj.get('latitude',0):.4f}° N, {obj.get('longitude',0):.4f}° E</td></tr>
      </table>
    </div>"""

def build_folium_map(objects, active_layers):
    fmap = folium.Map(location=[49.0, 28.4], zoom_start=8, tiles="CartoDB dark_matter")
    if "Зони СО" in active_layers:
        SO_ZONES = [
            {"name": "СО «Вінницькі міські ЕМ»", "color": "#38bdf8",
             "coords": [[49.28,28.35],[49.28,28.58],[49.18,28.58],[49.18,28.35]]},
            {"name": "СО «Жмеринські ЕМ» (вкл. Шаргород)", "color": "#a855f7",
             "coords": [[48.85,27.75],[48.85,28.25],[48.60,28.25],[48.60,27.75]]},
            {"name": "СО «Хмільницькі ЕМ»", "color": "#f59e0b",
             "coords": [[49.60,28.35],[49.60,28.75],[49.35,28.75],[49.35,28.35]]},
            {"name": "СО «Гайсинські ЕМ»", "color": "#10b981",
             "coords": [[48.95,29.25],[48.95,29.75],[48.65,29.75],[48.65,29.25]]},
        ]
        zone_group = folium.FeatureGroup(name="🗺️ Зони обслуговування СО", show=True)
        for zone in SO_ZONES:
            folium.Polygon(locations=zone["coords"], color=zone["color"], fill=True,
                           fill_color=zone["color"], fill_opacity=0.10, weight=2,
                           dash_array="8 4", tooltip=folium.Tooltip(zone["name"], sticky=True),
                           popup=folium.Popup(f"<b>{zone['name']}</b>", max_width=200)).add_to(zone_group)
        zone_group.add_to(fmap)
    if "ЛЕП" in active_layers:
        lep_group = folium.FeatureGroup(name="⚡ Лінії ЛЕП", show=True)
        LEP_LINES = [
            {"coords":[[49.2331,28.4682],[49.2425,28.4810]],"color":"#facc15","weight":4,"dash":None,"label":"ЛЕП 110 кВ: ТП-12 → ТП-28"},
            {"coords":[[49.2425,28.4810],[49.2210,28.4422]],"color":"#fb923c","weight":3,"dash":"6 3","label":"ЛЕП 35 кВ: ТП-28 → ТП-245 (АВАРІЯ)"},
            {"coords":[[48.7364,28.0822],[48.7390,28.0805]],"color":"#4ade80","weight":2,"dash":"3 3","label":"КЛ 10 кВ: ТП-Шаргород-100 → ЦОК"},
            {"coords":[[49.2331,28.4682],[49.4410,28.5122]],"color":"#facc15","weight":4,"dash":None,"label":"ЛЕП 110 кВ: Вінниця → Калинів"},
            {"coords":[[49.2331,28.4682],[48.7364,28.0822]],"color":"#fb923c","weight":2,"dash":"8 4","label":"ЛЕП 35 кВ: Вінниця → Шаргород"},
        ]
        for lep in LEP_LINES:
            folium.PolyLine(locations=lep["coords"], color=lep["color"], weight=lep["weight"],
                            dash_array=lep.get("dash"), tooltip=folium.Tooltip(lep["label"], sticky=True),
                            opacity=0.85).add_to(lep_group)
        lep_group.add_to(fmap)
    if "Об'єкти" in active_layers:
        obj_group = folium.FeatureGroup(name="📍 Об'єкти мережі", show=True)
        for obj in objects:
            lat, lon = obj.get("latitude"), obj.get("longitude")
            if lat is None or lon is None:
                continue
            color = get_marker_color(obj.get("status","Нормальна"))
            icon  = get_marker_icon(obj.get("type",""))
            if "АВАРІЯ" in obj.get("status",""):
                folium.CircleMarker(location=[lat,lon], radius=18, color="#ef4444",
                                    fill=True, fill_color="#ef4444", fill_opacity=0.20, weight=2).add_to(obj_group)
            folium.Marker(location=[lat,lon],
                          tooltip=folium.Tooltip(f"<b>{obj['name']}</b><br>{obj.get('type','')}<br>Статус: {obj.get('status','')}", sticky=True),
                          popup=folium.Popup(build_popup_html(obj), max_width=300),
                          icon=folium.Icon(color=color, icon=icon, prefix="fa")).add_to(obj_group)
        obj_group.add_to(fmap)
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:#1e293b;color:#f1f5f9;
                padding:12px 16px;border-radius:8px;font-size:12px;border:1px solid #334155;
                box-shadow:0 2px 8px rgba(0,0,0,.5)">
      <b style="font-size:13px">Легенда</b><br>
      <span style="color:#ef4444">●</span> Аварія &nbsp;
      <span style="color:#f97316">●</span> Попередження &nbsp;
      <span style="color:#22c55e">●</span> Норма<br>
      <span style="color:#facc15">━━</span> ЛЕП 110 кВ &nbsp;
      <span style="color:#fb923c">╌╌</span> ЛЕП 35 кВ &nbsp;
      <span style="color:#4ade80">╌╌</span> КЛ 10 кВ
    </div>"""
    fmap.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap

# ==========================================
# ВКЛАДКА: ГОЛОВНА СТОРІНКА
# ==========================================
if "home" in tab_map:
    with tab_map["home"]:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 60%,#0f172a 100%);
                    border-radius:16px;padding:3rem 2.5rem 2.5rem;margin-bottom:2rem;
                    border:1px solid #1e3a5f;position:relative;overflow:hidden;">
            <div style="position:absolute;top:-40px;right:-40px;font-size:220px;opacity:0.04;line-height:1;">⚡</div>
            <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.8rem;">
                <span style="font-size:2.8rem;">⚡</span>
                <div>
                    <div style="color:#93c5fd;font-size:0.85rem;letter-spacing:3px;text-transform:uppercase;font-weight:600;">
                        АТ «ВІННИЦЯОБЛЕНЕРГО»
                    </div>
                    <h1 style="color:#f1f5f9;margin:0;font-size:2.1rem;line-height:1.2;">ГІС Диспетчерська Система</h1>
                    <div style="color:#60a5fa;font-size:1.1rem;margin-top:4px;">
                        Регіональних Електромереж&nbsp;&nbsp;
                        <span style="background:#1d4ed8;color:#fff;border-radius:6px;padding:2px 10px;font-size:0.8rem;vertical-align:middle;">v5.0</span>
                    </div>
                </div>
            </div>
            <p style="color:#94a3b8;font-size:1rem;max-width:700px;margin:1rem 0 0 0;line-height:1.7;">
                Єдина цифрова платформа оперативного управління, моніторингу та технічного обслуговування
                електричних мереж Вінницької області.
            </p>
        </div>
        """, unsafe_allow_html=True)

        s1, s2, s3, s4, s5 = st.columns(5)
        def stat_card(col, icon, value, label, color="#38bdf8"):
            col.markdown(f"""
            <div style="background:#1e293b;border-radius:10px;padding:1rem 0.8rem;text-align:center;border:1px solid #334155;">
                <div style="font-size:1.6rem;">{icon}</div>
                <div style="color:{color};font-size:1.5rem;font-weight:700;line-height:1.2;">{value}</div>
                <div style="color:#64748b;font-size:0.75rem;margin-top:3px;">{label}</div>
            </div>""", unsafe_allow_html=True)
        stat_card(s1,"🏭","8","Структурних одиниць")
        stat_card(s2,"🔌","26","Дільниць обслуговування")
        stat_card(s3,"⚡","148.5 МВт","Потужність мережі","#a78bfa")
        stat_card(s4,"🗺️","6","ГІС-об'єктів в БД","#34d399")
        stat_card(s5,"🚨","1","Активних аварій","#f87171")

        st.markdown("<div style='margin-top:2rem'></div>", unsafe_allow_html=True)
        col_feat, col_tech = st.columns([1.1, 0.9])
        with col_feat:
            st.markdown("### 🧩 Функціональні модулі системи")
            modules = [
                ("🗺️","Диспетчер ГІС-мапи","Інтерактивна Folium-карта з шарами ЛЕП, зонами СО та кольоровими маркерами аварій."),
                ("📱","Мобільний клієнт бригади","Цифровий наряд-допуск для виїзних бригад: чек-лист безпеки, звіт про виконану роботу."),
                ("🌡️","SmartGrid AI — Аналітика","Симуляція навантаження залежно від температури (-20°C…+40°C), детекція аномалій напруги, Threshold Alerts."),
                ("📋","Журнал подій","Повний аудит-лог з фільтрацією за типом події, критичністю та об'єктом."),
                ("📅","Планування ТО","Графік регламентного технічного обслуговування."),
                ("👥","Управління доступом","Рольова модель (Адмін / Диспетчер / Монтер). Тільки для адміністраторів."),
            ]
            for icon, title, desc in modules:
                with st.container(border=True):
                    st.markdown(f"**{icon} {title}**")
                    st.caption(desc)

        with col_tech:
            st.markdown("### 🛠️ Технічний стек")
            st.markdown("""
            <div style="background:#1e293b;border-radius:12px;padding:1.2rem 1.4rem;border:1px solid #334155;font-size:0.88rem;line-height:2;">
                <table style="width:100%;border-collapse:collapse;color:#cbd5e1;">
                    <tr><td style="color:#60a5fa;width:38%;padding:4px 0;">🐍 Мова</td><td>Python 3.11+</td></tr>
                    <tr><td style="color:#60a5fa;padding:4px 0;">🖥️ Фреймворк</td><td>Streamlit ≥ 1.35</td></tr>
                    <tr><td style="color:#60a5fa;padding:4px 0;">🗺️ Картографія</td><td>Folium + streamlit-folium</td></tr>
                    <tr><td style="color:#60a5fa;padding:4px 0;">🌡️ SmartGrid AI</td><td>Температурна модель + Anomaly Detection</td></tr>
                    <tr><td style="color:#60a5fa;padding:4px 0;">📊 Аналітика</td><td>Pandas + Matplotlib</td></tr>
                    <tr><td style="color:#60a5fa;padding:4px 0;">📦 Версія</td><td>v5.0 — травень 2026</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)
            st.markdown("### 🗂️ Охоплення мережі")
            coverage = {
                "СО «Вінницькі міські ЕМ»": 1, "СО «Вінницькі центральні ЕМ»": 3,
                "СО «Жмеринські ЕМ»": 3, "СО «Хмільницькі ЕМ»": 3,
                "СО «Гайсинські ЕМ»": 5, "СО «Могилів-Подільські ЕМ»": 4,
                "СО «Тульчинські ЕМ»": 4, "СО «Вінницькі східні ЕМ»": 5,
            }
            fig_h, ax_h = plt.subplots(figsize=(5, 3.2))
            fig_h.patch.set_facecolor("#1e293b")
            ax_h.set_facecolor("#1e293b")
            bars = ax_h.barh([k.replace("СО «","").replace("»","") for k in coverage.keys()],
                             list(coverage.values()), color="#3b82f6", height=0.55)
            ax_h.bar_label(bars, fmt="%d дільн.", color="#93c5fd", fontsize=8, padding=3)
            ax_h.tick_params(colors="#94a3b8", labelsize=8)
            ax_h.spines[:].set_color("#334155")
            ax_h.set_xlabel("Кількість дільниць", color="#64748b", fontsize=8)
            ax_h.set_xlim(0, 7)
            plt.tight_layout()
            st.pyplot(fig_h)
            plt.close(fig_h)

        st.markdown("""
        <div style="background:#0f172a;border:1px solid #1e3a5f;border-radius:10px;
                    padding:1rem 1.5rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;margin-top:1.5rem;">
            <span style="color:#475569;font-size:0.8rem;">© 2026 АТ «Вінницяобленерго» — ГІС ДС v5.0</span>
            <span style="color:#475569;font-size:0.8rem;">🔒 Конфіденційна інформація. Доступ суворо за ролями.</span>
            <span style="color:#475569;font-size:0.8rem;">ІТ-відділ: it@voe.com.ua</span>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# ВКЛАДКА: ДИСПЕТЧЕР МАПИ
# ==========================================
if "map" in tab_map:
    with tab_map["map"]:
        st.title("🗺️ Оперативний диспетчерський пульт ГІС")
        if not FOLIUM_AVAILABLE:
            st.warning("⚠️ Бібліотеки `folium` та `streamlit-folium` не встановлені. Виконайте: `pip install folium streamlit-folium`")
        col_map, col_side = st.columns([2.3, 1])
        with col_map:
            st.markdown("##### 🛠️ Активні шари карти:")
            layer_cols = st.columns(3)
            show_objects = layer_cols[0].checkbox("📍 Об'єкти мережі", value=True)
            show_lep     = layer_cols[1].checkbox("⚡ Лінії ЛЕП",      value=True)
            show_zones   = layer_cols[2].checkbox("🗺️ Зони СО",        value=False)
            active_layers = []
            if show_objects: active_layers.append("Об'єкти")
            if show_lep:     active_layers.append("ЛЕП")
            if show_zones:   active_layers.append("Зони СО")
            if FOLIUM_AVAILABLE:
                fmap = build_folium_map(st.session_state.objects, active_layers)
                map_result = st_folium(fmap, width="100%", height=520, returned_objects=["last_object_clicked_popup"])
                clicked_popup = (map_result or {}).get("last_object_clicked_popup")
                if clicked_popup:
                    for o in st.session_state.objects:
                        if o["name"] in str(clicked_popup):
                            st.session_state.selected_object = o
                            break
            else:
                map_df = pd.DataFrame(st.session_state.objects)
                st.map(map_df, size=40)
            st.markdown("##### 🔍 Вибір об'єкта для телеметрії:")
            obj_names = [o["name"] for o in st.session_state.objects]
            try:
                curr_index = obj_names.index(st.session_state.selected_object["name"])
            except ValueError:
                curr_index = 0
            selected_name = st.selectbox("Оберіть вузол:", obj_names, index=curr_index)
            for o in st.session_state.objects:
                if o["name"] == selected_name:
                    st.session_state.selected_object = o
        with col_side:
            obj = st.session_state.selected_object
            st.subheader("ℹ️ Телеметрія та Управління")
            st.markdown(f"### {obj.get('name', 'Невідомий об\'єкт')}")
            status = obj.get('status','Нормальна')
            if "АВАРІЯ" in status:          st.error(f"Статус: {status}")
            elif "Попередження" in status:  st.warning(f"Статус: {status}")
            else:                           st.success(f"Статус: {status}")
            criticality = obj.get('criticality','Середня')
            st.markdown(f"**Підпорядкування:** `{obj.get('subdivision','Центральний апарат')}`")
            st.markdown(f"**Важливість вузла:** `{criticality}`")
            st.markdown(f"**Координати:** `{obj.get('latitude',0.0):.4f}° N, {obj.get('longitude',0.0):.4f}° E`")
            st.markdown(f"**Технічні параметри:** {obj.get('desc','Немає опису')}")
            st.divider()
            st.markdown("🎛️ **Команди дистанційного керування:**")
            if st.button("⚡ Вимкнути фідер (SCADA)", use_container_width=True):
                st.toast(f"🚨 Сигнал оперативної комутації надіслано на {obj.get('name')}!")
                st.session_state.log_data.insert(0, {
                    "Час": datetime.datetime.now().strftime("%d.%m %H:%M"), "Тип": "Ремонт",
                    "Об'єкт": obj.get('name'),
                    "Опис": f"Дистанційне оперативне керування. Оператор: {current_user['display_name']}",
                    "Критичність": "Висока"
                })
            if st.button("📲 Передати наряд черговому майстру дільниці", use_container_width=True):
                st.toast("📡 Дані надіслано в базу відповідної структурної одиниці ЕМ!")
            permit_text = (
                f"НАРЯД-ДОПУСК №{obj.get('name','ТП')}-2026\n"
                f"Об'єкт: {obj.get('name')} ({obj.get('type')})\n"
                f"Підрозділ: {obj.get('subdivision')}\nКритичність: {criticality}\n"
                f"Координати: {obj.get('latitude')}, {obj.get('longitude')}\n"
                f"Опис: {obj.get('desc')}\nВидав: {current_user['display_name']}\n"
                f"Згенеровано системою Вінницяобленерго."
            )
            st.download_button(label="📄 Завантажити Наряд-Допуск (.txt)",
                               data=permit_text, file_name=f"permit_{obj.get('name','TP')}.txt",
                               mime="text/plain", use_container_width=True)

# ==========================================
# ВКЛАДКА: МОБІЛЬНИЙ КЛІЄНТ
# ==========================================

# Ініціалізація стану геолокації та фото
if "geo_arrived" not in st.session_state:
    st.session_state.geo_arrived = False
if "geo_lat" not in st.session_state:
    st.session_state.geo_lat = None
if "geo_lon" not in st.session_state:
    st.session_state.geo_lon = None
if "voice_transcript" not in st.session_state:
    st.session_state.voice_transcript = ""
if "uploaded_photos" not in st.session_state:
    st.session_state.uploaded_photos = []   # список dict {name, data, source}
if "camera_shots" not in st.session_state:
    st.session_state.camera_shots = []      # знімки зі st.camera_input
if "photo_input_mode" not in st.session_state:
    st.session_state.photo_input_mode = "auto"   # "auto" | "camera" | "upload"

# Координати ТП-Шаргород-100 (еталон для звірки)
TP_TARGET = {"name": "ТП-Шаргород-100", "lat": 48.7364, "lon": 28.0822}

def haversine_km(lat1, lon1, lat2, lon2):
    """Відстань між двома точками у км (формула Гаверсинусів)."""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

if "mobile" in tab_map:
    with tab_map["mobile"]:
        st.title("📱 Цифровий кабінет лінійної бригади")

        # ── Верхня панель статусу ────────────────────────────────────────
        hdr1, hdr2, hdr3 = st.columns(3)
        hdr1.markdown(f"""
        <div style="background:#1e293b;border-radius:8px;padding:0.7rem 1rem;border:1px solid #334155;">
            <div style="color:#64748b;font-size:0.75rem;">👷 Оператор</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:0.9rem;">{current_user['display_name']}</div>
            <div style="color:#94a3b8;font-size:0.75rem;">{current_user['subdivision']}</div>
        </div>""", unsafe_allow_html=True)
        geo_status_color = "#22c55e" if st.session_state.geo_arrived else "#f59e0b"
        geo_status_label = "📍 Прибуття зафіксовано" if st.session_state.geo_arrived else "⏳ Очікування прибуття"
        hdr2.markdown(f"""
        <div style="background:#1e293b;border-radius:8px;padding:0.7rem 1rem;border:1px solid #334155;">
            <div style="color:#64748b;font-size:0.75rem;">🛰️ GPS-статус</div>
            <div style="color:{geo_status_color};font-weight:600;font-size:0.9rem;">{geo_status_label}</div>
            <div style="color:#94a3b8;font-size:0.75rem;">{"%.4f° N, %.4f° E" % (st.session_state.geo_lat, st.session_state.geo_lon) if st.session_state.geo_lat else "Координати не визначено"}</div>
        </div>""", unsafe_allow_html=True)
        _hdr_photo_count = len(st.session_state.camera_shots) + len(st.session_state.uploaded_photos)
        hdr3.markdown(f"""
        <div style="background:#1e293b;border-radius:8px;padding:0.7rem 1rem;border:1px solid #334155;">
            <div style="color:#64748b;font-size:0.75rem;">📸 Фотозвіт</div>
            <div style="color:#60a5fa;font-weight:600;font-size:0.9rem;">{_hdr_photo_count} фото прикріплено</div>
            <div style="color:#94a3b8;font-size:0.75rem;">{"✅ Готово до відправки" if _hdr_photo_count > 0 else "Фото не додано"}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

        # ── Поточний наряд ───────────────────────────────────────────────
        st.markdown("""
        <div style="background:#1e3a5f;border-radius:10px;padding:0.9rem 1.2rem;
                    border:1px solid #1e4f8a;margin-bottom:1rem;">
            <div style="color:#93c5fd;font-size:0.78rem;font-weight:600;letter-spacing:2px;text-transform:uppercase;">
                📋 Активний наряд-допуск
            </div>
            <div style="color:#f1f5f9;font-weight:700;font-size:1.05rem;margin-top:4px;">
                ТП-Шаргород-100 — Планова діагностика шин
            </div>
            <div style="display:flex;gap:1.5rem;margin-top:6px;flex-wrap:wrap;">
                <span style="color:#94a3b8;font-size:0.82rem;">🏢 СО «Жмеринські ЕМ» / Шаргородська дільниця</span>
                <span style="color:#94a3b8;font-size:0.82rem;">📍 48.7364° N, 28.0822° E</span>
                <span style="color:#fbbf24;font-size:0.82rem;">⚡ Критичність: Висока</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.task_closed:
            st.success("🎉 Наряд успішно закрито, підписано ЕЦП та відправлено до диспетчерського центру!")
            col_reopen, _ = st.columns([1, 2])
            with col_reopen:
                if st.button("🔄 Нове завдання"):
                    st.session_state.task_closed = False
                    st.session_state.geo_arrived = False
                    st.session_state.geo_lat = None
                    st.session_state.geo_lon = None
                    st.session_state.voice_transcript = ""
                    st.session_state.uploaded_photos = []
                    st.session_state.camera_shots = []
                    st.rerun()
        else:
            # ── 4 блоки розташовані у 2 колонки ─────────────────────────
            col_left, col_right = st.columns([1, 1], gap="medium")

            with col_left:
                # ── БЛОК 1: Геолокація ───────────────────────────────────
                with st.container(border=True):
                    st.markdown("### 🛰️ Геолокація — «Я на місці»")
                    st.caption("Натисніть кнопку після прибуття до об'єкта. Система звірить ваші координати з розташуванням ТП.")

                    if st.session_state.geo_arrived:
                        dist = haversine_km(
                            st.session_state.geo_lat, st.session_state.geo_lon,
                            TP_TARGET["lat"], TP_TARGET["lon"]
                        )
                        if dist < 0.5:
                            st.success(f"✅ Прибуття підтверджено! Відстань до {TP_TARGET['name']}: **{dist*1000:.0f} м**")
                        else:
                            st.warning(f"⚠️ Ви зафіксовані, але далеко від об'єкта: **{dist:.2f} км**")
                        st.markdown(f"""
                        <div style="background:#0f172a;border-radius:8px;padding:0.6rem 0.9rem;
                                    font-size:0.82rem;color:#94a3b8;margin-top:0.5rem;">
                            🕐 Час прибуття: <b style="color:#f1f5f9">{st.session_state.geo_time}</b><br>
                            📍 Координати: <b style="color:#60a5fa">{st.session_state.geo_lat:.4f}° N, {st.session_state.geo_lon:.4f}° E</b>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("🔄 Оновити геопозицію", use_container_width=True):
                            st.session_state.geo_arrived = False
                            st.rerun()
                    else:
                        st.markdown("""
                        <div style="background:#0f172a;border-radius:8px;padding:0.7rem;
                                    font-size:0.82rem;color:#64748b;text-align:center;margin-bottom:0.5rem;">
                            ℹ️ Для демо-режиму координати симулюються поблизу ТП-Шаргород-100
                        </div>""", unsafe_allow_html=True)

                        geo_mode = st.radio("Режим визначення координат:", 
                                            ["📡 Симуляція (поблизу ТП)", "📝 Ввести вручну"],
                                            horizontal=True, label_visibility="collapsed")

                        if geo_mode == "📝 Ввести вручну":
                            g1, g2 = st.columns(2)
                            manual_lat = g1.number_input("Широта (N)", value=48.7364, format="%.4f")
                            manual_lon = g2.number_input("Довгота (E)", value=28.0822, format="%.4f")
                        else:
                            # Симуляція: точка поряд з ТП ±0.001°
                            manual_lat = TP_TARGET["lat"] + _rnd.uniform(-0.002, 0.002)
                            manual_lon = TP_TARGET["lon"] + _rnd.uniform(-0.002, 0.002)

                        if st.button("📍 Я на місці — зафіксувати прибуття", use_container_width=True, type="primary"):
                            now_str = datetime.datetime.now().strftime("%d.%m %H:%M")
                            st.session_state.geo_lat   = round(manual_lat, 4)
                            st.session_state.geo_lon   = round(manual_lon, 4)
                            st.session_state.geo_time  = now_str
                            st.session_state.geo_arrived = True
                            dist = haversine_km(manual_lat, manual_lon, TP_TARGET["lat"], TP_TARGET["lon"])
                            st.session_state.log_data.insert(0, {
                                "Час": now_str,
                                "Тип": "Інспекція",
                                "Об'єкт": TP_TARGET["name"],
                                "Опис": (
                                    f"[{current_user['display_name']}] 📍 ПРИБУТТЯ зафіксовано. "
                                    f"Координати: {manual_lat:.4f}° N, {manual_lon:.4f}° E. "
                                    f"Відстань до об'єкта: {dist*1000:.0f} м."
                                ),
                                "Критичність": "Висока"
                            })
                            st.rerun()

                # ── БЛОК 2: Чек-лист безпеки ────────────────────────────
                with st.container(border=True):
                    st.markdown("### ✅ Чек-лист безпеки (ПУЕ)")
                    tb_1 = st.checkbox("⚡ Заземлення встановлено на всіх фазах")
                    tb_2 = st.checkbox("🪧 Плакати з техніки безпеки розвішано")
                    tb_3 = st.checkbox("🔒 Комутаційні апарати заблоковано")
                    tb_4 = st.checkbox("👷 Склад бригади проінструктовано")

                    safety_ok = tb_1 and tb_2 and tb_3 and tb_4
                    if safety_ok:
                        st.success("✅ Чек-лист повністю виконано")
                    else:
                        remaining = sum(1 for x in [tb_1, tb_2, tb_3, tb_4] if not x)
                        st.warning(f"⚠️ Залишилось пунктів: {remaining}")

            with col_right:
                # ── БЛОК 3: Фотозвіт (розумний вибір камера / файл) ─────
                with st.container(border=True):
                    st.markdown("### 📸 Фотозвіт (до та після робіт)")

                    # --- Детектор user-agent для автовизначення мобільного ---
                    # Читаємо заголовок через st.context (Streamlit ≥ 1.37)
                    # або через query_params як fallback
                    try:
                        ua = st.context.headers.get("user-agent", "").lower()
                    except Exception:
                        ua = ""
                    is_mobile = any(kw in ua for kw in [
                        "android", "iphone", "ipad", "mobile", "ipod"
                    ])

                    # --- Перемикач режиму ---
                    mode_labels = {
                        "auto":   f"🤖 Авто ({'📱 Камера' if is_mobile else '🖥️ Файл'})",
                        "camera": "📷 Камера (camera_input)",
                        "upload": "🗂️ Файл / Галерея (file_uploader)",
                    }
                    chosen_mode = st.radio(
                        "Режим введення фото:",
                        options=list(mode_labels.keys()),
                        format_func=lambda k: mode_labels[k],
                        horizontal=True,
                        key="photo_mode_radio",
                        label_visibility="collapsed",
                    )
                    st.session_state.photo_input_mode = chosen_mode

                    # Ефективний режим після авто-детекції
                    effective = (
                        ("camera" if is_mobile else "upload")
                        if chosen_mode == "auto"
                        else chosen_mode
                    )

                    # Підказка чому обрано цей режим
                    if chosen_mode == "auto":
                        if is_mobile:
                            st.caption("📱 Виявлено мобільний пристрій — увімкнено пряму камеру.")
                        else:
                            st.caption("🖥️ Десктоп — активовано завантаження файлів. Переключіться на «Камера» для веб-камери.")

                    # ═══════════════════════════════════════════════════════
                    # РЕЖИМ A: st.camera_input  (пряма камера)
                    # ═══════════════════════════════════════════════════════
                    if effective == "camera":
                        st.markdown("""
                        <div style="background:#0f172a;border-radius:8px;padding:6px 12px;
                                    font-size:0.78rem;color:#64748b;margin-bottom:6px;">
                            📷 <b style="color:#60a5fa;">st.camera_input</b> — натисніть кнопку щоб зробити знімок.
                            Кожен знімок додається до фотозвіту.
                        </div>""", unsafe_allow_html=True)

                        new_shot = st.camera_input(
                            "Зробіть знімок об'єкта:",
                            key="cam_shot",
                            help="Натисніть 'Take Photo' — знімок одразу додасться до наряду"
                        )

                        if new_shot is not None:
                            # Перевіряємо чи цей знімок вже доданий (по байтах)
                            new_bytes = new_shot.getvalue()
                            already = any(
                                s.get("bytes") == new_bytes
                                for s in st.session_state.camera_shots
                            )
                            if not already:
                                ts = datetime.datetime.now().strftime("%H:%M:%S")
                                st.session_state.camera_shots.append({
                                    "name": f"Знімок_{ts}.jpg",
                                    "bytes": new_bytes,
                                    "source": "camera",
                                    "ts": ts,
                                })
                                st.toast(f"📸 Знімок {len(st.session_state.camera_shots)} додано до наряду!")

                        # Галерея накопичених знімків
                        if st.session_state.camera_shots:
                            n = len(st.session_state.camera_shots)
                            st.success(f"✅ У фотозвіті: **{n} знімків**")
                            with st.expander(f"🖼️ Галерея знімків ({n} шт.)", expanded=(n <= 3)):
                                gcols = st.columns(2)
                                for i, shot in enumerate(st.session_state.camera_shots):
                                    with gcols[i % 2]:
                                        st.image(shot["bytes"], caption=f"📷 {shot['name']}", use_container_width=True)
                                        # Кнопка видалення окремого знімка
                                        if st.button(f"🗑️ Видалити", key=f"del_shot_{i}"):
                                            st.session_state.camera_shots.pop(i)
                                            st.rerun()
                            if st.button("🗑️ Очистити всі знімки", use_container_width=True):
                                st.session_state.camera_shots = []
                                st.rerun()
                        else:
                            st.markdown("""
                            <div style="border:2px dashed #334155;border-radius:10px;
                                        padding:1.2rem;text-align:center;color:#475569;margin-top:0.3rem;">
                                <div style="font-size:2rem;">📷</div>
                                <div style="font-size:0.82rem;margin-top:0.4rem;">
                                    Натисніть <b>«Take Photo»</b> вище — кожен знімок<br>
                                    автоматично додається до звіту наряду.
                                </div>
                            </div>""", unsafe_allow_html=True)

                    # ═══════════════════════════════════════════════════════
                    # РЕЖИМ B: st.file_uploader  (файли / галерея)
                    # ═══════════════════════════════════════════════════════
                    else:
                        st.markdown("""
                        <div style="background:#0f172a;border-radius:8px;padding:6px 12px;
                                    font-size:0.78rem;color:#64748b;margin-bottom:6px;">
                            🗂️ <b style="color:#60a5fa;">st.file_uploader</b> — оберіть файли з галереї або файлової системи.
                            На мобільному браузері також пропонується камера.
                        </div>""", unsafe_allow_html=True)

                        uploaded_files = st.file_uploader(
                            "Оберіть фото (можна кілька):",
                            type=["jpg", "jpeg", "png", "webp", "heic"],
                            accept_multiple_files=True,
                            key="photo_uploader",
                            help="Оберіть 1 або кілька фото з пристрою"
                        )

                        if uploaded_files:
                            st.session_state.uploaded_photos = [
                                {"name": f.name, "bytes": f.getvalue(), "source": "upload"}
                                for f in uploaded_files
                            ]
                            n = len(uploaded_files)
                            st.success(f"✅ Прикріплено {n} фото з файлової системи")
                            if n <= 4:
                                pcols = st.columns(min(n, 2))
                                for i, f in enumerate(uploaded_files):
                                    with pcols[i % 2]:
                                        st.image(f, caption=f"📷 {f.name}", use_container_width=True)
                            else:
                                with st.expander(f"🖼️ Переглянути всі {n} фото"):
                                    gc2 = st.columns(2)
                                    for i, f in enumerate(uploaded_files):
                                        with gc2[i % 2]:
                                            st.image(f, caption=f.name, use_container_width=True)
                        else:
                            st.markdown("""
                            <div style="border:2px dashed #334155;border-radius:10px;
                                        padding:1.5rem;text-align:center;color:#475569;margin-top:0.3rem;">
                                <div style="font-size:2rem;">📁</div>
                                <div style="font-size:0.85rem;margin-top:0.4rem;">
                                    Перетягніть фото або натисніть <b>«Browse files»</b><br>
                                    <span style="color:#60a5fa;">Підтримуються JPG, PNG, WEBP, HEIC</span>
                                </div>
                            </div>""", unsafe_allow_html=True)

                    # --- Підсумковий лічильник фото (обидва режими) ---
                    total_photos = len(st.session_state.camera_shots) + len(st.session_state.uploaded_photos)
                    photo_count = total_photos  # передаємо далі для прогрес-бару

                # ── БЛОК 4: Голосовий / текстовий звіт ──────────────────
                with st.container(border=True):
                    st.markdown("### 🎙️ Звіт про виконану роботу")

                    report_mode = st.radio(
                        "Спосіб введення:", 
                        ["⌨️ Текстовий", "🎙️ Голосова замітка (транскрипція)"],
                        horizontal=True, label_visibility="collapsed"
                    )

                    if report_mode == "🎙️ Голосова замітка (транскрипція)":
                        st.markdown("""
                        <div style="background:#1e293b;border-radius:8px;padding:0.8rem 1rem;
                                    border-left:3px solid #60a5fa;margin-bottom:0.5rem;">
                            <div style="color:#60a5fa;font-weight:600;font-size:0.85rem;">🤖 AI Транскрипція (симуляція)</div>
                            <div style="color:#94a3b8;font-size:0.78rem;margin-top:3px;">
                                На реальному пристрої тут підключається Whisper API або Web Speech API.
                                Для демо — введіть текст у поле нижче, натисніть «Транскрибувати».
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        voice_input = st.text_input(
                            "🎤 Диктуйте (або введіть текст для симуляції):",
                            placeholder="Наприклад: Ізолятор замінено, кріплення перевірено, напруга в нормі...",
                            key="voice_raw_input"
                        )
                        v1, v2 = st.columns([1, 1])
                        with v1:
                            if st.button("🎙️ Транскрибувати", use_container_width=True):
                                if voice_input.strip():
                                    timestamp = datetime.datetime.now().strftime("%H:%M")
                                    st.session_state.voice_transcript = (
                                        f"[🎙️ Голосова замітка {timestamp}]: {voice_input.strip()}"
                                    )
                                    st.toast("✅ Транскрипцію завершено!")
                                else:
                                    st.warning("Спочатку введіть або продиктуйте текст.")
                        with v2:
                            quick_templates = st.selectbox(
                                "📝 Швидкий шаблон:",
                                ["— оберіть —", "Роботи виконано в повному обсязі", 
                                 "Замінено ізолятор, пошкоджень не виявлено",
                                 "Виявлено корозію кріплення, потребує заміни",
                                 "Вимикач перевірено, контакти в нормі"],
                                label_visibility="collapsed"
                            )
                            if quick_templates != "— оберіть —":
                                st.session_state.voice_transcript = quick_templates

                        if st.session_state.voice_transcript:
                            st.markdown(f"""
                            <div style="background:#0f172a;border-radius:8px;padding:0.7rem 0.9rem;
                                        border:1px solid #334155;font-size:0.85rem;color:#e2e8f0;
                                        margin-top:0.3rem;">
                                <span style="color:#a78bfa;">📝 Транскрипт:</span><br>{st.session_state.voice_transcript}
                            </div>
                            """, unsafe_allow_html=True)
                        comment = st.session_state.voice_transcript

                    else:
                        comment = st.text_area(
                            "Текстовий звіт:",
                            placeholder="Опишіть виконані роботи, виявлені дефекти, стан обладнання...",
                            height=120,
                            key="text_comment"
                        )

            # ── Кнопка закриття наряду (повна ширина) ───────────────────
            st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)

            all_checks = tb_1 and tb_2 and tb_3 and tb_4
            has_comment = bool(comment and comment.strip())
            has_geo = st.session_state.geo_arrived

            # Прогрес-індикатор готовності
            readiness = sum([all_checks, has_comment, has_geo, photo_count > 0])
            readiness_pct = int(readiness / 4 * 100)
            readiness_colors = {0: "#ef4444", 1: "#f59e0b", 2: "#fbbf24", 3: "#a3e635", 4: "#22c55e"}
            readiness_color = readiness_colors.get(readiness, "#64748b")

            st.markdown(f"""
            <div style="background:#1e293b;border-radius:10px;padding:0.8rem 1.2rem;
                        border:1px solid #334155;margin-bottom:0.8rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="color:#94a3b8;font-size:0.82rem;font-weight:600;">📊 Готовність наряду до закриття</span>
                    <span style="color:{readiness_color};font-weight:700;">{readiness_pct}%</span>
                </div>
                <div style="background:#0f172a;border-radius:6px;height:8px;overflow:hidden;">
                    <div style="background:{readiness_color};width:{readiness_pct}%;height:100%;
                                border-radius:6px;transition:width 0.3s;"></div>
                </div>
                <div style="display:flex;gap:1rem;margin-top:8px;font-size:0.75rem;flex-wrap:wrap;">
                    <span style="color:{'#22c55e' if all_checks else '#475569'};">{'✅' if all_checks else '⬜'} Чек-лист безпеки</span>
                    <span style="color:{'#22c55e' if has_geo else '#475569'};">{'✅' if has_geo else '⬜'} GPS-прибуття</span>
                    <span style="color:{'#22c55e' if has_comment else '#475569'};">{'✅' if has_comment else '⬜'} Звіт</span>
                    <span style="color:{'#22c55e' if photo_count > 0 else '#475569'};">{'✅' if photo_count > 0 else '⬜'} Фото ({photo_count})</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            btn_label = "🚀 Закрити наряд-допуск та відправити звіт" if readiness == 4 else f"🚀 Закрити наряд ({readiness_pct}% готовності)"
            if st.button(btn_label, use_container_width=True, type="primary"):
                if not all_checks:
                    st.error("❌ Заповніть усі пункти чек-листа безпеки (ПУЕ)!")
                elif not has_comment:
                    st.error("❌ Введіть або продиктуйте звіт про виконану роботу!")
                else:
                    now_str = datetime.datetime.now().strftime("%d.%m %H:%M")
                    geo_info = f" | GPS: {st.session_state.geo_lat:.4f}° N, {st.session_state.geo_lon:.4f}° E" if has_geo else " | GPS: не зафіксовано"
                    photo_info = f" | Фото: {photo_count} шт." if photo_count > 0 else ""
                    st.session_state.log_data.insert(0, {
                        "Час": now_str,
                        "Тип": "Планове ТО",
                        "Об'єкт": "ТП-Шаргород-100",
                        "Опис": f"[{current_user['display_name']}]{geo_info}{photo_info}: {comment.strip()}",
                        "Критичність": "Висока"
                    })
                    st.session_state.task_closed = True
                    st.rerun()

        st.markdown("---")

# ==========================================
# ВКЛАДКА: СТРУКТУРА КОМПАНІЇ
# ==========================================
if "structure" in tab_map:
    with tab_map["structure"]:
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
            st.info("ℹ️ Шаргород та колишній Шаргородський район повністю охоплюються АТ «Вінницяобленерго». Адміністративно Шаргородська дільниця входить до складу структури СО «Жмеринські електричні мережі».")
            box_sh = st.container(border=True)
            box_sh.markdown("### 🏢 Безпосередньо у місті Шаргород діють:")
            box_sh.markdown("""
            * **🔧 Шаргородська дільниця** — технічне обслуговування мереж, поточний та капітальний ремонт.
            * **👥 Центр обслуговування клієнтів (ЦОК)** — прийом споживачів з питань нових приєднань, технічних умов.
            """)
            st.caption("🗺️ Локація сервісної інфраструктури в м. Шаргород:")
            if FOLIUM_AVAILABLE:
                sh_map = folium.Map(location=[48.7377,28.0813], zoom_start=15, tiles="CartoDB dark_matter")
                sh_objects = [
                    {"name":"ТП-Шаргород-100","latitude":48.7364,"longitude":28.0822,"type":"Підстанція",
                     "status":"Нормальна","criticality":"Висока","subdivision":"СО «Жмеринські ЕМ»","desc":"ВН-35/10 кВ."},
                    {"name":"ЦОК Шаргород","latitude":48.7390,"longitude":28.0805,"type":"Центр клієнтів",
                     "status":"Нормальна","criticality":"Низька","subdivision":"СО «Жмеринські ЕМ»","desc":"Прийом споживачів."},
                ]
                for o in sh_objects:
                    folium.Marker(location=[o["latitude"],o["longitude"]], tooltip=o["name"],
                                  popup=folium.Popup(build_popup_html(o), max_width=280),
                                  icon=folium.Icon(color=get_marker_color(o["status"]),
                                                  icon=get_marker_icon(o["type"]), prefix="fa")).add_to(sh_map)
                folium.PolyLine([[48.7364,28.0822],[48.7390,28.0805]], color="#4ade80", weight=2,
                                dash_array="4 3", tooltip="КЛ 10 кВ: ТП-100 → ЦОК").add_to(sh_map)
                st_folium(sh_map, width="100%", height=300, returned_objects=[])
            else:
                sh_df = pd.DataFrame([
                    {"name":"ТП-Шаргород-100","latitude":48.7364,"longitude":28.0822},
                    {"name":"ЦОК Шаргород","latitude":48.7390,"longitude":28.0805}
                ])
                st.map(sh_df, zoom=13, size=45)

# ==========================================
# ВКЛАДКА: АНАЛІТИКА ТА KPI (SmartGrid AI)
# ==========================================
if "analytics" in tab_map:
    with tab_map["analytics"]:
        st.title("📊 SmartGrid AI — Інтелектуальна аналітика мережі")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Індекс надійності SAIDI", "42.5 хв/рік", "-3.2 хв від плану", delta_color="inverse")
        m2.metric("Індекс частоти вимкнень SAIFI", "1.14 од/рік", "+0.02", delta_color="inverse")
        m3.metric("Загальна потужність споживання", "148.5 МВт", "Норма")
        m4.metric("Коефіцієнт корисного використання", "94.2%", "+0.5%")

        st.markdown("---")

        # ── БЛОК 1: Симуляція навантаження ─────────────────────────────
        st.markdown("### 🌡️ SmartGrid AI — Симуляція навантаження за температурою")

        col_ctrl, col_info = st.columns([2, 1])
        with col_ctrl:
            temperature = st.slider(
                "🌡️ Температура зовнішнього середовища (°C)",
                min_value=-20, max_value=40, value=15, step=1,
                help="Зміна температури впливає на прогнозоване навантаження мережі"
            )
        with col_info:
            if temperature <= -10:
                season_label, season_color = "❄️ Сильні морози", "#60a5fa"
            elif temperature <= 0:
                season_label, season_color = "🌨️ Зима", "#93c5fd"
            elif temperature <= 10:
                season_label, season_color = "🌤️ Прохолодна погода", "#6ee7b7"
            elif temperature <= 20:
                season_label, season_color = "🌿 Весна / Осінь", "#34d399"
            elif temperature <= 30:
                season_label, season_color = "☀️ Тепло", "#fbbf24"
            else:
                season_label, season_color = "🔥 Спека / Кондиціонери", "#f87171"
            st.markdown(f"""
            <div style="background:#1e293b;border-radius:10px;padding:0.9rem 1.1rem;
                        border-left:4px solid {season_color};margin-top:0.4rem;">
                <div style="color:{season_color};font-weight:700;font-size:1rem;">{season_label}</div>
                <div style="color:#94a3b8;font-size:0.82rem;margin-top:4px;">
                    Поточна t°: <b style="color:#f1f5f9">{temperature}°C</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        BASE_LOAD = [65, 50, 85, 110, 140, 148, 90]
        hours = [f"{i}:00" for i in range(0, 25, 4)]
        LOAD_THRESHOLD_HIGH = 160.0
        LOAD_THRESHOLD_LOW  = 35.0

        def compute_load_for_temp(base_load, temp):
            if temp < 0:
                factor = 1.0 + 0.04 * abs(temp)
            elif temp <= 20:
                factor = 1.0 - 0.015 * (temp - 15)
            else:
                factor = 0.925 + 0.025 * (temp - 20)
            return [round(v * factor, 1) for v in base_load]

        predicted_load = compute_load_for_temp(BASE_LOAD, temperature)
        actual_load    = [v + (i % 3 - 1) * 2.5 for i, v in enumerate(predicted_load)]
        overload_hours  = [hours[i] for i, v in enumerate(predicted_load) if v > LOAD_THRESHOLD_HIGH]
        underload_hours = [hours[i] for i, v in enumerate(predicted_load) if v < LOAD_THRESHOLD_LOW]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.2))
        fig.patch.set_facecolor("#0f172a")
        ax1.set_facecolor("#1e293b")
        ax1.plot(hours, actual_load, label="Фактичне навантаження (МВт)",
                 color="#38bdf8", marker="o", linewidth=2.5, markersize=6)
        ax1.plot(hours, predicted_load, label=f"Прогноз SmartGrid AI ({temperature}°C)",
                 color="#a855f7", linestyle="--", linewidth=2)
        ax1.axhline(y=LOAD_THRESHOLD_HIGH, color="#ef4444", linestyle=":", linewidth=1.5,
                    label=f"Верхня межа ({LOAD_THRESHOLD_HIGH} МВт)")
        ax1.axhline(y=LOAD_THRESHOLD_LOW,  color="#f59e0b", linestyle=":", linewidth=1.5,
                    label=f"Нижня межа ({LOAD_THRESHOLD_LOW} МВт)")
        ax1.fill_between(range(len(hours)), LOAD_THRESHOLD_HIGH,
                         [max(v, LOAD_THRESHOLD_HIGH) for v in predicted_load],
                         color="#ef4444", alpha=0.15, label="⚠️ Перевантаження")
        ax1.fill_between(range(len(hours)), LOAD_THRESHOLD_LOW,
                         [min(v, LOAD_THRESHOLD_LOW) for v in predicted_load],
                         color="#f59e0b", alpha=0.15, label="⚠️ Недовантаження")
        ax1.set_xticks(range(len(hours)))
        ax1.set_xticklabels(hours, color="#94a3b8", fontsize=8)
        ax1.set_title(f"Прогноз навантаження при {temperature}°C", color="#f1f5f9", fontsize=10)
        ax1.legend(fontsize=7, facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1")
        ax1.grid(True, alpha=0.15, color="#334155")
        ax1.tick_params(colors="#64748b")
        ax1.spines[:].set_color("#334155")
        ax1.set_ylabel("МВт", color="#64748b", fontsize=9)
        ax1.set_ylim(0, 200)

        ax2.set_facecolor("#1e293b")
        current_logs_df = pd.DataFrame(st.session_state.log_data)
        types_distribution = current_logs_df["Тип"].value_counts()
        wedge_colors = ["#ef4444", "#f59e0b", "#10b981", "#38bdf8", "#bc5090"]
        wedges, texts, autotexts = ax2.pie(
            types_distribution.values, labels=types_distribution.index,
            colors=wedge_colors[:len(types_distribution)], autopct="%1.1f%%", startangle=90,
            wedgeprops=dict(edgecolor="#0f172a", linewidth=2)
        )
        for t in texts: t.set_color("#94a3b8"); t.set_fontsize(8)
        for at in autotexts: at.set_color("#f1f5f9"); at.set_fontsize(8)
        ax2.set_title("Розподіл подій у журналі", color="#f1f5f9", fontsize=10)
        plt.tight_layout(pad=2.0)
        st.pyplot(fig)
        plt.close(fig)

        # ── БЛОК 2: Детекція аномалій ───────────────────────────────────
        st.markdown("---")
        st.markdown("### 🚨 SmartGrid AI — Детекція аномалій та Threshold Alerts")

        _rnd.seed(temperature + 42)

        VOLTAGE_NORMS = {
            "Підстанція 110 кВ": {"nom": 110.0, "low": 100.0, "high": 120.0},
            "Підстанція 35 кВ":  {"nom": 35.0,  "low": 31.5,  "high": 38.5},
            "Підстанція 10 кВ":  {"nom": 10.0,  "low": 9.0,   "high": 11.0},
            "Лінія 10 кВ":       {"nom": 10.0,  "low": 8.8,   "high": 10.5},
        }

        def simulate_voltage(obj, temp):
            base_voltages = {
                "ТП-12":           ("Підстанція 110 кВ", 110.0),
                "ТП-28":           ("Підстанція 35 кВ",  35.0),
                "ТП-245":          ("Підстанція 10 кВ",  10.0),
                "ТП-Шаргород-100": ("Підстанція 35 кВ",  35.0),
                "ЦОК Шаргород":    ("Лінія 10 кВ",       10.0),
                "Оп. №9":          ("Лінія 10 кВ",       10.0),
            }
            vtype, vnom = base_voltages.get(obj["name"], ("Підстанція 10 кВ", 10.0))
            norm = VOLTAGE_NORMS[vtype]
            temp_stress = abs(temp - 15) / 55.0
            deviation_range = norm["nom"] * 0.12 * temp_stress
            deviation = _rnd.uniform(-deviation_range, deviation_range)
            if "АВАРІЯ" in obj.get("status", ""):
                deviation += norm["nom"] * _rnd.uniform(-0.15, -0.05)
            elif "Попередження" in obj.get("status", ""):
                deviation += norm["nom"] * _rnd.uniform(-0.08, 0.02)
            return vtype, norm, round(vnom + deviation, 2)

        alert_rows = []
        for obj in st.session_state.objects:
            vtype, norm, actual = simulate_voltage(obj, temperature)
            status_ok = norm["low"] <= actual <= norm["high"]
            deviation_pct = round((actual - norm["nom"]) / norm["nom"] * 100, 1)
            alert_rows.append({"obj": obj, "vtype": vtype, "norm": norm,
                                "actual": actual, "status_ok": status_ok, "deviation_pct": deviation_pct})

        n_crit = sum(1 for r in alert_rows if not r["status_ok"] and "АВАРІЯ" in r["obj"].get("status",""))
        n_warn = sum(1 for r in alert_rows if not r["status_ok"] and "Попередження" in r["obj"].get("status",""))
        n_volt = sum(1 for r in alert_rows if not r["status_ok"] and r["obj"].get("status","") == "Нормальна")
        n_ok   = sum(1 for r in alert_rows if r["status_ok"] and r["obj"].get("status","") == "Нормальна")

        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("🔴 Критичні аварії",   n_crit)
        ac2.metric("🟠 Попередження",       n_warn)
        ac3.metric("🟡 Аномалії напруги",   n_volt)
        ac4.metric("🟢 Об'єктів у нормі",   n_ok)

        anomaly_rows = [r for r in alert_rows
                        if not r["status_ok"] or r["obj"].get("status","") in ("АВАРІЯ","Попередження")]
        normal_rows  = [r for r in alert_rows
                        if r["status_ok"] and r["obj"].get("status","") == "Нормальна"]

        if anomaly_rows:
            st.markdown("#### ⚠️ Об'єкти поза межами норми:")
            for row in anomaly_rows:
                obj = row["obj"]
                actual_v = row["actual"]
                norm     = row["norm"]
                dev      = row["deviation_pct"]
                vtype    = row["vtype"]
                obj_status = obj.get("status","Нормальна")

                if "АВАРІЯ" in obj_status:
                    border_color="#ef4444"; badge_bg="#7f1d1d"; badge_text="🔴 АВАРІЯ"; icon="🚨"
                    rec = "Негайно направити ОВБ. Відключити пошкоджений вузол через SCADA. Перевірити живлення споживачів через резервне кільце."
                elif "Попередження" in obj_status:
                    border_color="#f59e0b"; badge_bg="#78350f"; badge_text="🟠 ПОПЕРЕДЖЕННЯ"; icon="⚠️"
                    rec = "Призначити позапланову інспекцію. Перевірити ізоляцію та контактні з'єднання."
                elif actual_v < norm["low"]:
                    border_color="#facc15"; badge_bg="#713f12"; badge_text="🟡 АНОМАЛІЯ НАПРУГИ"; icon="⚡"
                    rec = f"Напруга нижче норми ({actual_v} кВ < {norm['low']} кВ). Перевірити навантаження. Можливо потрібне секціонування."
                else:
                    border_color="#facc15"; badge_bg="#713f12"; badge_text="🟡 АНОМАЛІЯ НАПРУГИ"; icon="⚡"
                    rec = f"Напруга вище норми ({actual_v} кВ > {norm['high']} кВ). Перевірити РПН трансформатора."

                sign = "+" if dev >= 0 else ""
                st.markdown(f"""
                <div style="background:#1e293b;border-radius:10px;padding:0.9rem 1.2rem;
                            margin-bottom:0.7rem;border:1px solid #334155;border-left:5px solid {border_color};">
                  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
                    <div>
                      <span style="font-size:1.1rem;">{icon}</span>
                      <b style="color:#f1f5f9;font-size:1rem;margin-left:6px;">{obj["name"]}</b>
                      <span style="color:#64748b;font-size:0.82rem;margin-left:8px;">{vtype}</span>
                    </div>
                    <span style="background:{badge_bg};color:#fef2f2;border-radius:5px;padding:2px 10px;font-size:0.78rem;font-weight:600;">{badge_text}</span>
                  </div>
                  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;margin-top:0.7rem;font-size:0.83rem;">
                    <div style="background:#0f172a;border-radius:6px;padding:0.5rem 0.7rem;">
                      <div style="color:#64748b;">Напруга факт.</div>
                      <div style="color:{border_color};font-weight:700;font-size:1rem;">{actual_v} кВ</div>
                    </div>
                    <div style="background:#0f172a;border-radius:6px;padding:0.5rem 0.7rem;">
                      <div style="color:#64748b;">Норма (min–max)</div>
                      <div style="color:#94a3b8;font-weight:600;">{norm["low"]}–{norm["high"]} кВ</div>
                    </div>
                    <div style="background:#0f172a;border-radius:6px;padding:0.5rem 0.7rem;">
                      <div style="color:#64748b;">Відхилення</div>
                      <div style="color:{border_color};font-weight:700;">{sign}{dev}%</div>
                    </div>
                  </div>
                  <div style="margin-top:0.6rem;font-size:0.82rem;color:#94a3b8;">
                    <span style="color:#60a5fa;font-weight:600;">🤖 SmartGrid AI:</span> {rec}
                  </div>
                  <div style="margin-top:0.4rem;font-size:0.78rem;color:#475569;">
                    📌 {obj.get("subdivision","—")} · {obj.get("desc","—")[:90]}
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ SmartGrid AI: Усі об'єкти функціонують у межах норми.")

        if normal_rows:
            with st.expander(f"✅ Об'єкти в нормі ({len(normal_rows)} шт.) — розгорнути"):
                for row in normal_rows:
                    obj = row["obj"]
                    sign = "+" if row["deviation_pct"] >= 0 else ""
                    st.markdown(
                        f"**✅ {obj['name']}** — {row['vtype']} | "
                        f"Напруга: `{row['actual']} кВ` | "
                        f"Норма: `{row['norm']['low']}–{row['norm']['high']} кВ` | "
                        f"Відхилення: `{sign}{row['deviation_pct']}%`"
                    )

        # Гістограма напруги
        st.markdown("#### 📊 Гістограма напруги об'єктів vs Норма")
        fig2, ax = plt.subplots(figsize=(10, 3.5))
        fig2.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#1e293b")
        names2   = [r["obj"]["name"] for r in alert_rows]
        actuals2 = [r["actual"] / r["norm"]["nom"] * 100 for r in alert_rows]
        bar_colors = []
        for r in alert_rows:
            if "АВАРІЯ" in r["obj"].get("status",""):
                bar_colors.append("#ef4444")
            elif not r["status_ok"]:
                bar_colors.append("#f59e0b")
            else:
                bar_colors.append("#22c55e")
        bars2 = ax.bar(names2, actuals2, color=bar_colors, width=0.55, edgecolor="#0f172a")
        ax.axhline(y=100, color="#60a5fa", linestyle="--", linewidth=1.5, label="Номінал (100%)")
        ax.axhline(y=90,  color="#f59e0b", linestyle=":", linewidth=1, alpha=0.7, label="Нижня межа норми (~90%)")
        ax.axhline(y=110, color="#f59e0b", linestyle=":", linewidth=1, alpha=0.7, label="Верхня межа норми (~110%)")
        ax.bar_label(bars2, fmt="%.1f%%", color="#cbd5e1", fontsize=8, padding=3)
        ax.set_ylabel("% від номіналу", color="#64748b", fontsize=8)
        ax.set_title(f"Напруга об'єктів (% від номіналу) при {temperature}°C", color="#f1f5f9", fontsize=9)
        ax.tick_params(colors="#94a3b8", labelsize=8)
        ax.spines[:].set_color("#334155")
        ax.legend(fontsize=7.5, facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1")
        ax.set_ylim(75, 125)
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

        # Підсумковий алерт
        if overload_hours:
            st.error(f"🚨 **SmartGrid AI попередження:** Прогнозується перевантаження мережі в години: **{', '.join(overload_hours)}**. "
                     f"Рекомендується ввести обмеження навантаження або підключити резервні джерела живлення.")
        elif underload_hours:
            st.warning(f"⚠️ **SmartGrid AI:** Низьке навантаження в: **{', '.join(underload_hours)}**. Можливий аварійний режим.")
        elif temperature <= -10 or temperature >= 32:
            st.warning(f"⚠️ **SmartGrid AI:** Екстремальні погодні умови ({temperature}°C). "
                       f"Рекомендується посилений моніторинг та підвищена готовність ОВБ.")
        else:
            st.success(f"✅ **SmartGrid AI:** Прогнозоване навантаження при {temperature}°C в межах норми. "
                       f"Пікове навантаження: **{max(predicted_load)} МВт**.")

# ==========================================
# ВКЛАДКА: ЖУРНАЛ ПОДІЙ
# ==========================================
if "log" in tab_map:
    with tab_map["log"]:
        st.title("📋 Цифровий журнал подій диспетчера")
        df = pd.DataFrame(st.session_state.log_data)
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1: search_query = st.text_input("🔍 Швидкий фільтр за назвою об'єкта", "")
        with col_f2: type_filter = st.selectbox("Тип події", ["Усі типи","Аварія","Планове ТО","Ремонт","Інспекція"])
        with col_f3: crit_filter = st.selectbox("Ступінь критичності", ["Усі рівні","Критична","Висока","Середня","Низька"])
        if type_filter != "Усі типи": df = df[df["Тип"] == type_filter]
        if crit_filter != "Усі рівні" and "Критичність" in df.columns: df = df[df["Критичність"] == crit_filter]
        if search_query: df = df[df["Об'єкт"].str.contains(search_query, case=False)]
        st.dataframe(df, use_container_width=True, hide_index=True)

# ==========================================
# ВКЛАДКА: ПЛАНУВАННЯ ТО
# ==========================================
if "schedule" in tab_map:
    with tab_map["schedule"]:
        st.title("📅 Графік планового технічного обслуговування")
        st.subheader("➕ Додати нове завдання до плану:")
        col_in1, col_in2, col_in3 = st.columns(3)
        with col_in1: plan_obj = st.selectbox("Вузол для ТО:", [o["name"] for o in st.session_state.objects])
        with col_in2: plan_date = st.date_input("Дата робіт", datetime.date.today() + datetime.timedelta(days=1))
        with col_in3: plan_desc = st.text_input("Опис регламентних робіт:", placeholder="Введіть опис робіт...")
        if st.button("➕ Додати до графіка робіт", use_container_width=True):
            if plan_desc:
                st.session_state.schedule_data.append({
                    "Дата": str(plan_date), "Об'єкт": plan_obj,
                    "Вид робіт": plan_desc, "Статус": "Заплановано"
                })
                st.success(f"✅ Роботи по {plan_obj} успішно додано!")
                st.rerun()
            else:
                st.error("Будь ласка, вкажіть вид робіт.")
        st.divider()
        st.subheader("📋 Поточний графік робіт:")
        st.table(pd.DataFrame(st.session_state.schedule_data))

# ==========================================
# ВКЛАДКА: DATA ЦЕНТР (тільки Адмін)
# ==========================================
if "data" in tab_map:
    with tab_map["data"]:
        st.title("💾 Data-Центр синхронізації та обміну (Імпорт/Експорт)")
        curr_df = pd.DataFrame(st.session_state.log_data)
        exp_col, imp_col = st.columns(2)
        with exp_col:
            st.subheader("📤 Експорт даних із системи")
            csv_data = curr_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Скачати Excel CSV (.csv)", data=csv_data,
                               file_name="vinnitsaoblenergo_export.csv", mime="text/csv", use_container_width=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                curr_df.to_excel(writer, index=False, sheet_name='Журнал Подій')
            st.download_button(label="📥 Скачати книгу MS Excel (.xlsx)", data=buffer.getvalue(),
                               file_name="vinnitsaoblenergo_export.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        with imp_col:
            st.subheader("📥 Імпорт зовнішніх даних")
            uploaded_file = st.file_uploader("Оберіть файл конфігурації мережі", type=["csv","xlsx","json"])
            if uploaded_file is not None:
                st.success("✅ Структуру файлу успішно розпізнано! Дані готові до інтеграції.")

# ==========================================
# ВКЛАДКА: УПРАВЛІННЯ ДОСТУПОМ (тільки Адмін)
# ==========================================
if "users" in tab_map:
    with tab_map["users"]:
        st.title("👥 Управління правами доступу користувачів")
        st.info("ℹ️ Ця вкладка доступна виключно адміністраторам системи.")
        st.subheader("📋 Поточні облікові записи системи")
        users_display = []
        for login, data in USERS_DB.items():
            users_display.append({
                "Логін": login, "Ім'я та посада": data["display_name"],
                "Підрозділ": data["subdivision"], "Роль": ROLE_LABELS.get(data["role"], data["role"]),
                "Доступні вкладки": ", ".join(
                    t[0] for t in TAB_DEFINITIONS[ROLE_TO_TAB_SET.get(data["role"],"brigade_tabs")]
                )
            })
        st.dataframe(pd.DataFrame(users_display), use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("🔐 Матриця доступу за ролями")
        matrix_data = []
        all_tabs = list(dict.fromkeys(t[0] for tabs in TAB_DEFINITIONS.values() for t in tabs))
        for role_key, role_label in ROLE_LABELS.items():
            tab_set_key = ROLE_TO_TAB_SET.get(role_key, "brigade_tabs")
            role_tabs = [t[0] for t in TAB_DEFINITIONS[tab_set_key]]
            row = {"Роль": role_label}
            for tab in all_tabs:
                row[tab] = "✅" if tab in role_tabs else "🚫"
            matrix_data.append(row)
        st.dataframe(pd.DataFrame(matrix_data).set_index("Роль"), use_container_width=True)
