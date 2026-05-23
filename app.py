import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import io
import datetime

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(
    page_title="ГІС Диспетчерська Система Регіональних Електромереж v5.0",
    layout="wide",
    initial_sidebar_state="expanded"
)

plt.style.use('dark_background')

# ==========================================
# СИСТЕМА АВТОРИЗАЦІЇ
# ==========================================

# База користувачів: {логін: {пароль, роль, ім'я}}
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

# Ініціалізація стану авторизації
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "login_error" not in st.session_state:
    st.session_state.login_error = ""

def do_login(username: str, password: str):
    user = USERS_DB.get(username.strip().lower())
    if user and user["password"] == password:
        st.session_state.authenticated = True
        st.session_state.current_user = {
            "login": username,
            "role": user["role"],
            "display_name": user["display_name"],
            "subdivision": user["subdivision"]
        }
        st.session_state.login_error = ""
    else:
        st.session_state.login_error = "❌ Невірний логін або пароль. Спробуйте ще раз."

def do_logout():
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.login_error = ""

# --- ЕКРАН ЛОГІНА ---
if not st.session_state.authenticated:
    col_l, col_center, col_r = st.columns([1, 1.4, 1])
    with col_center:
        st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1rem 0;'>
            <div style='font-size: 3rem;'>⚡</div>
            <h2 style='color: #185FA5; margin-bottom: 0;'>АТ «Вінницяобленерго»</h2>
            <p style='color: #555; font-size: 0.9rem; margin-top: 0.3rem;'>
                ГІС Диспетчерська Система v4.0 — Вхід до системи
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

    st.stop()  # Нічого далі не показуємо без авторизації

# ==========================================
# АВТОРИЗОВАНИЙ КОРИСТУВАЧ — ДАНІ СЕСІЇ
# ==========================================
current_user = st.session_state.current_user
user_role = current_user["role"]

# --- БІЧНА ПАНЕЛЬ: інфо про користувача ---
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
# ГОЛОВНЕ МЕНЮ — ДИНАМІЧНЕ ЗА РОЛЛЮ
# ==========================================

# Визначаємо, які вкладки доступні для кожної ролі
TAB_DEFINITIONS = {
    "dispatcher_tabs": [
        ("🏢 Диспетчер мапи", "map"),
        ("📱 Мобільний клієнт", "mobile"),
        ("🏛️ Структура компанії", "structure"),
        ("📊 Аналітика та KPI", "analytics"),
        ("📋 Журнал подій", "log"),
        ("📅 Планування ТО", "schedule"),
    ],
    "admin_tabs": [
        ("🏢 Диспетчер мапи", "map"),
        ("📱 Мобільний клієнт", "mobile"),
        ("🏛️ Структура компанії", "structure"),
        ("📊 Аналітика та KPI", "analytics"),
        ("📋 Журнал подій", "log"),
        ("📅 Планування ТО", "schedule"),
        ("💾 Data Центр", "data"),
        ("👥 Управління доступом", "users"),
    ],
    "brigade_tabs": [
        ("📱 Мобільний клієнт", "mobile"),
    ],
}

ROLE_TO_TAB_SET = {
    "dispatcher": "dispatcher_tabs",
    "admin": "admin_tabs",
    "brigade": "brigade_tabs",
}

active_tab_set_key = ROLE_TO_TAB_SET.get(user_role, "brigade_tabs")
active_tabs = TAB_DEFINITIONS[active_tab_set_key]

tab_labels = [t[0] for t in active_tabs]
tab_keys = [t[1] for t in active_tabs]

rendered_tabs = st.tabs(tab_labels)
tab_map = dict(zip(tab_keys, rendered_tabs))

# ==========================================
# ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ FOLIUM ГІС
# ==========================================

# Кольори маркерів за статусом об'єкта
def get_marker_color(status: str) -> str:
    if "АВАРІЯ" in status:   return "red"
    if "Попередження" in status: return "orange"
    return "green"

# Іконки за типом об'єкта
def get_marker_icon(obj_type: str) -> str:
    icons = {
        "Підстанція":       "bolt",
        "Опора":            "map-pin",
        "Центр клієнтів":   "users",
    }
    return icons.get(obj_type, "circle-info")

# HTML-рядок для pop-up вікна
def build_popup_html(obj: dict) -> str:
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
        <tr><td style="color:#666;padding:2px 0">Тип:</td>
            <td><b>{obj.get('type','—')}</b></td></tr>
        <tr><td style="color:#666;padding:2px 0">Критичність:</td>
            <td><b>{obj.get('criticality','—')}</b></td></tr>
        <tr><td style="color:#666;padding:2px 0">СО:</td>
            <td>{obj.get('subdivision','—')}</td></tr>
        <tr><td style="color:#666;padding:2px 0;vertical-align:top">Опис:</td>
            <td style="color:#333">{obj.get('desc','—')}</td></tr>
        <tr><td style="color:#666;padding:2px 0">Координати:</td>
            <td>{obj.get('latitude',0):.4f}° N, {obj.get('longitude',0):.4f}° E</td></tr>
      </table>
    </div>
    """

# Побудова Folium-карти
def build_folium_map(objects: list, active_layers: list) -> "folium.Map":
    # Центр — Вінницька область
    fmap = folium.Map(
        location=[49.0, 28.4],
        zoom_start=8,
        tiles="CartoDB dark_matter"
    )

    # ---- ШАР: Зони обслуговування СО (приблизні полігони) ----
    if "Зони СО" in active_layers:
        SO_ZONES = [
            {
                "name": "СО «Вінницькі міські ЕМ»",
                "color": "#38bdf8",
                "coords": [
                    [49.28, 28.35], [49.28, 28.58],
                    [49.18, 28.58], [49.18, 28.35]
                ]
            },
            {
                "name": "СО «Жмеринські ЕМ» (вкл. Шаргород)",
                "color": "#a855f7",
                "coords": [
                    [48.85, 27.75], [48.85, 28.25],
                    [48.60, 28.25], [48.60, 27.75]
                ]
            },
            {
                "name": "СО «Хмільницькі ЕМ»",
                "color": "#f59e0b",
                "coords": [
                    [49.60, 28.35], [49.60, 28.75],
                    [49.35, 28.75], [49.35, 28.35]
                ]
            },
            {
                "name": "СО «Гайсинські ЕМ»",
                "color": "#10b981",
                "coords": [
                    [48.95, 29.25], [48.95, 29.75],
                    [48.65, 29.75], [48.65, 29.25]
                ]
            },
        ]
        zone_group = folium.FeatureGroup(name="🗺️ Зони обслуговування СО", show=True)
        for zone in SO_ZONES:
            folium.Polygon(
                locations=zone["coords"],
                color=zone["color"],
                fill=True,
                fill_color=zone["color"],
                fill_opacity=0.10,
                weight=2,
                dash_array="8 4",
                tooltip=folium.Tooltip(zone["name"], sticky=True),
                popup=folium.Popup(f"<b>{zone['name']}</b>", max_width=200)
            ).add_to(zone_group)
        zone_group.add_to(fmap)

    # ---- ШАР: Лінії ЛЕП ----
    if "ЛЕП" in active_layers:
        lep_group = folium.FeatureGroup(name="⚡ Лінії ЛЕП", show=True)
        LEP_LINES = [
            # 110 кВ  — ТП-12 → ТП-28
            {
                "coords": [[49.2331, 28.4682], [49.2425, 28.4810]],
                "color": "#facc15", "weight": 4, "dash": None,
                "label": "ЛЕП 110 кВ: ТП-12 → ТП-28"
            },
            # 35 кВ   — ТП-28 → ТП-245
            {
                "coords": [[49.2425, 28.4810], [49.2210, 28.4422]],
                "color": "#fb923c", "weight": 3, "dash": "6 3",
                "label": "ЛЕП 35 кВ: ТП-28 → ТП-245 (АВАРІЯ)"
            },
            # 10 кВ   — ТП-Шаргород-100 → ЦОК Шаргород
            {
                "coords": [[48.7364, 28.0822], [48.7390, 28.0805]],
                "color": "#4ade80", "weight": 2, "dash": "3 3",
                "label": "КЛ 10 кВ: ТП-Шаргород-100 → ЦОК"
            },
            # Магістраль 110 кВ — Вінниця → Хмільник
            {
                "coords": [[49.2331, 28.4682], [49.4410, 28.5122]],
                "color": "#facc15", "weight": 4, "dash": None,
                "label": "ЛЕП 110 кВ: Вінниця → Калинів (Хмільник)"
            },
            # Магістраль 35 кВ — Вінниця → Шаргород
            {
                "coords": [[49.2331, 28.4682], [48.7364, 28.0822]],
                "color": "#fb923c", "weight": 2, "dash": "8 4",
                "label": "ЛЕП 35 кВ: Вінниця → Шаргород"
            },
        ]
        for lep in LEP_LINES:
            folium.PolyLine(
                locations=lep["coords"],
                color=lep["color"],
                weight=lep["weight"],
                dash_array=lep.get("dash"),
                tooltip=folium.Tooltip(lep["label"], sticky=True),
                opacity=0.85
            ).add_to(lep_group)
        lep_group.add_to(fmap)

    # ---- ШАР: Маркери об'єктів ----
    if "Об'єкти" in active_layers:
        obj_group = folium.FeatureGroup(name="📍 Об'єкти мережі", show=True)
        for obj in objects:
            lat = obj.get("latitude")
            lon = obj.get("longitude")
            if lat is None or lon is None:
                continue

            color = get_marker_color(obj.get("status", "Нормальна"))
            icon  = get_marker_icon(obj.get("type", ""))

            # Пульсуюче коло для аварій
            if "АВАРІЯ" in obj.get("status", ""):
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=18,
                    color="#ef4444",
                    fill=True,
                    fill_color="#ef4444",
                    fill_opacity=0.20,
                    weight=2,
                ).add_to(obj_group)

            folium.Marker(
                location=[lat, lon],
                tooltip=folium.Tooltip(
                    f"<b>{obj['name']}</b><br>{obj.get('type','')}<br>Статус: {obj.get('status','')}",
                    sticky=True
                ),
                popup=folium.Popup(build_popup_html(obj), max_width=300),
                icon=folium.Icon(
                    color=color,
                    icon=icon,
                    prefix="fa"
                )
            ).add_to(obj_group)

        obj_group.add_to(fmap)

    # ---- Легенда ----
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;
                background:#1e293b;color:#f1f5f9;padding:12px 16px;
                border-radius:8px;font-size:12px;border:1px solid #334155;
                box-shadow:0 2px 8px rgba(0,0,0,.5)">
      <b style="font-size:13px">Легенда</b><br>
      <span style="color:#ef4444">●</span> Аварія &nbsp;
      <span style="color:#f97316">●</span> Попередження &nbsp;
      <span style="color:#22c55e">●</span> Норма<br>
      <span style="color:#facc15">━━</span> ЛЕП 110 кВ &nbsp;
      <span style="color:#fb923c">╌╌</span> ЛЕП 35 кВ &nbsp;
      <span style="color:#4ade80">╌╌</span> КЛ 10 кВ<br>
      <span style="opacity:.6">░░░</span> Зона обслуговування СО
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap


# ==========================================
# ВКЛАДКА: ДИСПЕТЧЕР МАПИ
# ==========================================
if "map" in tab_map:
    with tab_map["map"]:
        st.title("🗺️ Оперативний диспетчерський пульт ГІС")

        if not FOLIUM_AVAILABLE:
            st.warning(
                "⚠️ Бібліотеки `folium` та `streamlit-folium` не встановлені. "
                "Виконайте: `pip install folium streamlit-folium`"
            )

        col_map, col_side = st.columns([2.3, 1])

        with col_map:
            st.markdown("##### 🛠️ Активні шари карти:")
            layer_cols = st.columns(3)
            show_objects = layer_cols[0].checkbox("📍 Об'єкти мережі",   value=True)
            show_lep     = layer_cols[1].checkbox("⚡ Лінії ЛЕП",       value=True)
            show_zones   = layer_cols[2].checkbox("🗺️ Зони СО",         value=False)

            active_layers = []
            if show_objects: active_layers.append("Об'єкти")
            if show_lep:     active_layers.append("ЛЕП")
            if show_zones:   active_layers.append("Зони СО")

            if FOLIUM_AVAILABLE:
                fmap = build_folium_map(st.session_state.objects, active_layers)
                map_result = st_folium(fmap, width="100%", height=520, returned_objects=["last_object_clicked_popup"])

                # Якщо клацнули маркер — автовибір об'єкта в правій панелі
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

            status = obj.get('status', 'Нормальна')
            if "АВАРІЯ" in status:       st.error(f"Статус: {status}")
            elif "Попередження" in status: st.warning(f"Статус: {status}")
            else:                          st.success(f"Статус: {status}")

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
                    "Опис": f"Дистанційне оперативне керування. Оператор: {current_user['display_name']}",
                    "Критичність": "Висока"
                })

            if st.button("📲 Передати наряд черговому майстру дільниці", use_container_width=True):
                st.toast(f"📡 Дані надіслано в базу відповідної структурної одиниці ЕМ!")

            permit_text = (
                f"НАРЯД-ДОПУСК №{obj.get('name', 'ТП')}-2026\n"
                f"Об'єкт: {obj.get('name')} ({obj.get('type')})\n"
                f"Підрозділ: {obj.get('subdivision')}\n"
                f"Критичність: {criticality}\n"
                f"Координати: {obj.get('latitude')}, {obj.get('longitude')}\n"
                f"Опис: {obj.get('desc')}\n"
                f"Видав: {current_user['display_name']}\n"
                f"Згенеровано системою Вінницяобленерго."
            )
            st.download_button(
                label="📄 Завантажити Наряд-Допуск (.txt)",
                data=permit_text,
                file_name=f"permit_{obj.get('name', 'TP')}.txt",
                mime="text/plain",
                use_container_width=True
            )

# ==========================================
# ВКЛАДКА: МОБІЛЬНИЙ КЛІЄНТ
# ==========================================
if "mobile" in tab_map:
    with tab_map["mobile"]:
        st.title("📱 Цифровий кабінет лінійної бригади")
        _, phone_col, _ = st.columns([1, 2, 1])
        with phone_col:
            st.markdown("---")
            st.markdown("<h3 style='text-align: center; color: #185FA5;'>📱 Мобільна бригада АТ «Вінницяобленерго»</h3>", unsafe_allow_html=True)
            st.info(f"👷 {current_user['display_name']} | GPS: Активний")
            
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
                            "Опис": f"[{current_user['display_name']}]: {comment}",
                            "Критичність": "Висока"
                        })
                        st.rerun()
                    else: st.error("Заповніть чек-лист безпеки та коментар!")
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
            * **🔧 Шаргородська дільниця** — технічне обслуговування мереж, поточний та капітальний ремонт ліній і підстанцій.
            * **👥 Центр обслуговування клієнтів (ЦОК)** — прийом споживачів з питань нових приєднань, технічних умов, встановлення лічильників та договірної документації.
            """)
            
            st.caption("🗺️ Локація сервісної інфраструктури в м. Шаргород:")
            if FOLIUM_AVAILABLE:
                sh_map = folium.Map(location=[48.7377, 28.0813], zoom_start=15, tiles="CartoDB dark_matter")
                sh_objects = [
                    {"name": "ТП-Шаргород-100", "latitude": 48.7364, "longitude": 28.0822,
                     "type": "Підстанція", "status": "Нормальна", "criticality": "Висока",
                     "subdivision": "СО «Жмеринські ЕМ»", "desc": "ВН-35/10 кВ. Шаргородська дільниця."},
                    {"name": "ЦОК Шаргород", "latitude": 48.7390, "longitude": 28.0805,
                     "type": "Центр клієнтів", "status": "Нормальна", "criticality": "Низька",
                     "subdivision": "СО «Жмеринські ЕМ»", "desc": "Прийом споживачів."},
                ]
                for o in sh_objects:
                    folium.Marker(
                        location=[o["latitude"], o["longitude"]],
                        tooltip=o["name"],
                        popup=folium.Popup(build_popup_html(o), max_width=280),
                        icon=folium.Icon(color=get_marker_color(o["status"]),
                                        icon=get_marker_icon(o["type"]), prefix="fa")
                    ).add_to(sh_map)
                # КЛ між об'єктами
                folium.PolyLine(
                    [[48.7364, 28.0822], [48.7390, 28.0805]],
                    color="#4ade80", weight=2, dash_array="4 3",
                    tooltip="КЛ 10 кВ: ТП-100 → ЦОК"
                ).add_to(sh_map)
                st_folium(sh_map, width="100%", height=300, returned_objects=[])
            else:
                sh_df = pd.DataFrame([
                    {"name": "ТП-Шаргород-100", "latitude": 48.7364, "longitude": 28.0822},
                    {"name": "ЦОК Шаргород", "latitude": 48.7390, "longitude": 28.0805}
                ])
                st.map(sh_df, zoom=13, size=45)

# ==========================================
# ВКЛАДКА: АНАЛІТИКА ТА KPI
# ==========================================
if "analytics" in tab_map:
    with tab_map["analytics"]:
        st.title("📊 Апарат інтелектуальної аналітики")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Індекс надійності SAIDI", "42.5 хв/рік", "-3.2 хв від плану", delta_color="inverse")
        m2.metric("Індекс частоти вимкнень SAIFI", "1.14 од/рік", "+0.02", delta_color="inverse")
        m3.metric("Загальна потужність споживання", "148.5 МВт", "Норма")
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
# ВКЛАДКА: ЖУРНАЛ ПОДІЙ
# ==========================================
if "log" in tab_map:
    with tab_map["log"]:
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
                "Логін": login,
                "Ім'я та посада": data["display_name"],
                "Підрозділ": data["subdivision"],
                "Роль": ROLE_LABELS.get(data["role"], data["role"]),
                "Доступні вкладки": ", ".join(
                    t[0] for t in TAB_DEFINITIONS[ROLE_TO_TAB_SET.get(data["role"], "brigade_tabs")]
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
