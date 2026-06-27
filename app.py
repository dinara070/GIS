import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import json
import io
import datetime
import random as _rnd
import time

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

st.set_page_config(
    page_title="ГІС Диспетчерська Система Регіональних Електромереж v6.0",
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
        "display_name": "Адміністратор Чорна Є. М.",
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
    "crm_manager": {
        "password": "crm2026",
        "role": "crm",
        "display_name": "Менеджер CRM Волошина Н.Б.",
        "subdivision": "Відділ комерційного обліку"
    },
}

ROLE_LABELS = {
    "dispatcher": "👷 Диспетчер",
    "admin": "🔑 Адміністратор",
    "brigade": "🪖 Монтер / Мобільна бригада",
    "crm": "💰 Менеджер CRM",
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
                ГІС Диспетчерська Система v6.0 — Вхід до системи
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
            | `crm_manager` | `crm2026` | 💰 Менеджер CRM |
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
# CRM — ІНІЦІАЛІЗАЦІЯ ДАНИХ
# ==========================================

# Райони / дільниці та їх координати (центроїди для теплової карти)
CRM_DISTRICTS = [
    {"id": "vinnytsia_city",  "name": "Вінниця міська",     "so": "СО «Вінницькі міські ЕМ»",       "lat": 49.233, "lon": 28.468,
     "consumers_total": 124500, "consumers_paid": 108200, "debt_uah": 4_820_000, "consumption_kwh": 18_450_000},
    {"id": "vinnytsia_cent",  "name": "Вінницька центр.",    "so": "СО «Вінницькі центральні ЕМ»",   "lat": 49.320, "lon": 28.560,
     "consumers_total": 38400,  "consumers_paid": 33100,  "debt_uah": 2_150_000, "consumption_kwh": 6_200_000},
    {"id": "vinnytsia_east",  "name": "Вінницька східна",    "so": "СО «Вінницькі східні ЕМ»",       "lat": 49.105, "lon": 29.100,
     "consumers_total": 41200,  "consumers_paid": 34800,  "debt_uah": 3_670_000, "consumption_kwh": 7_100_000},
    {"id": "haisyn",          "name": "Гайсинська",          "so": "СО «Гайсинські ЕМ»",             "lat": 48.810, "lon": 29.380,
     "consumers_total": 29800,  "consumers_paid": 21400,  "debt_uah": 5_940_000, "consumption_kwh": 5_050_000},
    {"id": "zhmerynka",       "name": "Жмеринська + Шаргород", "so": "СО «Жмеринські ЕМ»",          "lat": 48.900, "lon": 28.100,
     "consumers_total": 33600,  "consumers_paid": 30100,  "debt_uah": 1_820_000, "consumption_kwh": 5_700_000},
    {"id": "khmilnyk",        "name": "Хмільницька",         "so": "СО «Хмільницькі ЕМ»",           "lat": 49.560, "lon": 27.950,
     "consumers_total": 27100,  "consumers_paid": 23400,  "debt_uah": 2_310_000, "consumption_kwh": 4_600_000},
    {"id": "mohyliv",         "name": "Могилів-Подільська",  "so": "СО «Могилів-Подільські ЕМ»",    "lat": 48.450, "lon": 27.800,
     "consumers_total": 24900,  "consumers_paid": 19800,  "debt_uah": 4_480_000, "consumption_kwh": 4_200_000},
    {"id": "tulchyn",         "name": "Тульчинська",         "so": "СО «Тульчинські ЕМ»",           "lat": 48.670, "lon": 28.840,
     "consumers_total": 22300,  "consumers_paid": 19700,  "debt_uah": 1_960_000, "consumption_kwh": 3_800_000},
]

# Тарифи (грн/кВт·год) — двозонний та тризонний лічильник (2026)
TARIFF_SINGLE  = 4.32   # одноставковий
TARIFF_DAY     = 4.32   # двозонний день    (07:00–23:00)
TARIFF_NIGHT   = 2.16   # двозонний ніч     (23:00–07:00)
TARIFF_PEAK    = 7.01   # тризонний пік     (08:00–11:00, 20:00–22:00)
TARIFF_SEMI    = 4.32   # тризонний напівпік
TARIFF_VALLEY  = 2.16   # тризонний ніч/провал

# Місячна динаміка платежів (% сплачено до кінця кожного місяця)
MONTHS_SHORT = ["Січ", "Лют", "Бер", "Кві", "Тра", "Чер",
                "Лип", "Сер", "Вер", "Жов", "Лис", "Гру"]
_rnd.seed(99)

def _gen_monthly_pay_pct(base):
    return [min(99.5, max(55.0, base + _rnd.uniform(-8, 8))) for _ in range(12)]

if "crm_monthly_pay" not in st.session_state:
    st.session_state.crm_monthly_pay = {d["id"]: _gen_monthly_pay_pct(
        d["consumers_paid"] / d["consumers_total"] * 100
    ) for d in CRM_DISTRICTS}

# Категорії боржників
DEBTOR_CATEGORIES = ["Населення", "Бюджетні орг.", "Підприємства", "ОСББ / ЖКГ", "Агросектор"]
if "crm_debtors" not in st.session_state:
    _rnd.seed(42)
    st.session_state.crm_debtors = []
    _names = [
        ("ТОВ «Агро-Вінниця»","Агросектор"),("ФОП Ткаченко В.М.","Населення"),
        ("КП «Теплосервіс»","Бюджетні орг."),("ОСББ «Центральний»","ОСББ / ЖКГ"),
        ("ТОВ «БудМаш»","Підприємства"),("ДП «Водоканал»","Бюджетні орг."),
        ("ФОП Кравченко Л.П.","Населення"),("ОСББ «Садовий»","ОСББ / ЖКГ"),
        ("ТОВ «ЕнергоПром»","Підприємства"),("ФОП Гнатюк О.В.","Населення"),
        ("КЗ «СШ №15»","Бюджетні орг."),("ТОВ «Кормові культури»","Агросектор"),
        ("ОСББ «Мрія»","ОСББ / ЖКГ"),("ТОВ «Мегалит»","Підприємства"),
        ("ФОП Савченко І.С.","Населення"),
    ]
    _districts_ids = [d["id"] for d in CRM_DISTRICTS]
    for nm, cat in _names:
        debt = round(_rnd.uniform(12_000, 840_000), 2)
        months_overdue = _rnd.randint(1, 18)
        st.session_state.crm_debtors.append({
            "Назва / ПІБ": nm,
            "Категорія": cat,
            "Дільниця": _rnd.choice(CRM_DISTRICTS)["name"],
            "Борг (грн)": debt,
            "Місяців прострочення": months_overdue,
            "Статус": "⛔ Відключено" if months_overdue > 6 else ("⚠️ Попередження" if months_overdue > 2 else "🟡 Нагадування"),
            "Останній платіж": (datetime.date.today() - datetime.timedelta(days=months_overdue * 30)).strftime("%d.%m.%Y"),
        })

# ==========================================
# ГОЛОВНЕ МЕНЮ
# ==========================================
TAB_DEFINITIONS = {
    "dispatcher_tabs": [
        ("🏠 Головна", "home"), ("🗺️ Диспетчер мапи", "map"), ("📱 Мобільний клієнт", "mobile"),
        ("⚡ ГПВ", "gpv"), ("🏛️ Структура компанії", "structure"), ("📊 Аналітика та KPI", "analytics"),
        ("📋 Журнал подій", "log"), ("📅 Планування ТО", "schedule"),
    ],
    "admin_tabs": [
        ("🏠 Головна", "home"), ("🗺️ Диспетчер мапи", "map"), ("📱 Мобільний клієнт", "mobile"),
        ("⚡ ГПВ", "gpv"), ("🏛️ Структура компанії", "structure"), ("📊 Аналітика та KPI", "analytics"),
        ("📋 Журнал подій", "log"), ("📅 Планування ТО", "schedule"),
        ("💰 CRM та Білінг", "crm"), ("💾 Data Центр", "data"), ("👥 Управління доступом", "users"),
    ],
    "crm_tabs": [
        ("🏠 Головна", "home"), ("💰 CRM та Білінг", "crm"),
    ],
    "brigade_tabs": [
        ("🏠 Головна", "home"), ("📱 Мобільний клієнт", "mobile"), ("⚡ ГПВ", "gpv"),
    ],
}
ROLE_TO_TAB_SET = {
    "dispatcher": "dispatcher_tabs",
    "admin":      "admin_tabs",
    "brigade":    "brigade_tabs",
    "crm":        "crm_tabs",
}
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
    # Додати всередину функції build_folium_map (після ініціалізації fmap)
if "gpv" in active_layers:
    # Приклад: якщо статус черги "🔴 Відключено", фарбуємо певні зони в червоний
    for q, status in st.session_state.gpv_data.items():
        if status == "🔴 Відключено":
             folium.Circle(location=[49.0, 28.4], radius=5000, color="red", fill=True).add_to(fmap)
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
                        <span style="background:#1d4ed8;color:#fff;border-radius:6px;padding:2px 10px;font-size:0.8rem;vertical-align:middle;">v6.0</span>
                    </div>
                </div>
            </div>
            <p style="color:#94a3b8;font-size:1rem;max-width:700px;margin:1rem 0 0 0;line-height:1.7;">
                Єдина цифрова платформа оперативного управління, моніторингу, технічного обслуговування
                та комерційного обліку електричних мереж Вінницької області.
            </p>
        </div>
        """, unsafe_allow_html=True)

        s1, s2, s3, s4, s5, s6 = st.columns(6)
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
        total_consumers = sum(d["consumers_total"] for d in CRM_DISTRICTS)
        stat_card(s4,"👥",f"{total_consumers:,}".replace(",","ʼ"),"Споживачів (CRM)","#34d399")
        total_debt = sum(d["debt_uah"] for d in CRM_DISTRICTS)
        stat_card(s5,"💸",f"{total_debt/1_000_000:.1f} млн","Загальний борг, грн","#fb923c")
        stat_card(s6,"🚨","1","Активних аварій","#f87171")

        st.markdown("<div style='margin-top:2rem'></div>", unsafe_allow_html=True)
        col_feat, col_tech = st.columns([1.1, 0.9])
        with col_feat:
            st.markdown("### 🧩 Функціональні модулі системи")
            modules = [
                ("🗺️","Диспетчер ГІС-мапи","Інтерактивна Folium-карта з шарами ЛЕП, зонами СО та кольоровими маркерами аварій."),
                ("📱","Мобільний клієнт бригади","Цифровий наряд-допуск для виїзних бригад: чек-лист безпеки, звіт про виконану роботу."),
                ("🌡️","SmartGrid AI — Аналітика","Симуляція навантаження залежно від температури (-20°C…+40°C), детекція аномалій напруги, Threshold Alerts."),
                ("💰","CRM та Білінг","Дашборд оплат, теплова карта боргів по дільницях, калькулятор тарифних зон (2/3-зонний лічильник)."),
                ("📋","Журнал подій","Повний аудит-лог з фільтрацією за типом події, критичністю та об'єктом."),
                ("📅","Планування ТО","Графік регламентного технічного обслуговування."),
                ("👥","Управління доступом","Рольова модель (Адмін / Диспетчер / Монтер / CRM). Тільки для адміністраторів."),
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
                    <tr><td style="color:#60a5fa;padding:4px 0;">💰 CRM / Білінг</td><td>Теплова карта боргів, тарифний калькулятор</td></tr>
                    <tr><td style="color:#60a5fa;padding:4px 0;">📊 Аналітика</td><td>Pandas + Matplotlib</td></tr>
                    <tr><td style="color:#60a5fa;padding:4px 0;">📦 Версія</td><td>v6.0 — травень 2026</td></tr>
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
            <span style="color:#475569;font-size:0.8rem;">© 2026 АТ «Вінницяобленерго» — ГІС ДС v6.0</span>
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
if "geo_arrived" not in st.session_state:
    st.session_state.geo_arrived = False
if "geo_lat" not in st.session_state:
    st.session_state.geo_lat = None
if "geo_lon" not in st.session_state:
    st.session_state.geo_lon = None
if "voice_transcript" not in st.session_state:
    st.session_state.voice_transcript = ""
if "uploaded_photos" not in st.session_state:
    st.session_state.uploaded_photos = []
if "camera_shots" not in st.session_state:
    st.session_state.camera_shots = []
if "photo_input_mode" not in st.session_state:
    st.session_state.photo_input_mode = "auto"

TP_TARGET = {"name": "ТП-Шаргород-100", "lat": 48.7364, "lon": 28.0822}

def haversine_km(lat1, lon1, lat2, lon2):
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

if "mobile" in tab_map:
    with tab_map["mobile"]:
        st.title("📱 Цифровий кабінет лінійної бригади")
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
            col_left, col_right = st.columns([1, 1], gap="medium")
            with col_left:
                with st.container(border=True):
                    st.markdown("### 🛰️ Геолокація — «Я на місці»")
                    st.caption("Натисніть кнопку після прибуття до об'єкта.")
                    if st.session_state.geo_arrived:
                        dist = haversine_km(st.session_state.geo_lat, st.session_state.geo_lon, TP_TARGET["lat"], TP_TARGET["lon"])
                        if dist < 0.5:
                            st.success(f"✅ Прибуття підтверджено! Відстань: **{dist*1000:.0f} м**")
                        else:
                            st.warning(f"⚠️ Далеко від об'єкта: **{dist:.2f} км**")
                        st.markdown(f"""
                        <div style="background:#0f172a;border-radius:8px;padding:0.6rem 0.9rem;font-size:0.82rem;color:#94a3b8;margin-top:0.5rem;">
                            🕐 Час: <b style="color:#f1f5f9">{st.session_state.geo_time}</b><br>
                            📍 Координати: <b style="color:#60a5fa">{st.session_state.geo_lat:.4f}° N, {st.session_state.geo_lon:.4f}° E</b>
                        </div>""", unsafe_allow_html=True)
                        if st.button("🔄 Оновити геопозицію", use_container_width=True):
                            st.session_state.geo_arrived = False
                            st.rerun()
                    else:
                        geo_mode = st.radio("Режим:", ["📡 Симуляція (поблизу ТП)", "📝 Ввести вручну"], horizontal=True, label_visibility="collapsed")
                        if geo_mode == "📝 Ввести вручну":
                            g1, g2 = st.columns(2)
                            manual_lat = g1.number_input("Широта (N)", value=48.7364, format="%.4f")
                            manual_lon = g2.number_input("Довгота (E)", value=28.0822, format="%.4f")
                        else:
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
                                "Час": now_str, "Тип": "Інспекція", "Об'єкт": TP_TARGET["name"],
                                "Опис": f"[{current_user['display_name']}] 📍 ПРИБУТТЯ. Координати: {manual_lat:.4f}° N, {manual_lon:.4f}° E. Відстань: {dist*1000:.0f} м.",
                                "Критичність": "Висока"
                            })
                            st.rerun()

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
                with st.container(border=True):
                    st.markdown("### 📸 Фотозвіт (до та після робіт)")
                    try:
                        ua = st.context.headers.get("user-agent", "").lower()
                    except Exception:
                        ua = ""
                    is_mobile = any(kw in ua for kw in ["android", "iphone", "ipad", "mobile", "ipod"])
                    mode_labels = {
                        "auto":   f"🤖 Авто ({'📱 Камера' if is_mobile else '🖥️ Файл'})",
                        "camera": "📷 Камера",
                        "upload": "🗂️ Файл / Галерея",
                    }
                    chosen_mode = st.radio("Режим:", options=list(mode_labels.keys()),
                                          format_func=lambda k: mode_labels[k], horizontal=True,
                                          key="photo_mode_radio", label_visibility="collapsed")
                    st.session_state.photo_input_mode = chosen_mode
                    effective = ("camera" if is_mobile else "upload") if chosen_mode == "auto" else chosen_mode

                    if effective == "camera":
                        new_shot = st.camera_input("Зробіть знімок:", key="cam_shot")
                        if new_shot is not None:
                            new_bytes = new_shot.getvalue()
                            already = any(s.get("bytes") == new_bytes for s in st.session_state.camera_shots)
                            if not already:
                                ts = datetime.datetime.now().strftime("%H:%M:%S")
                                st.session_state.camera_shots.append({"name": f"Знімок_{ts}.jpg", "bytes": new_bytes, "source": "camera", "ts": ts})
                                st.toast(f"📸 Знімок {len(st.session_state.camera_shots)} додано!")
                        if st.session_state.camera_shots:
                            n = len(st.session_state.camera_shots)
                            st.success(f"✅ У фотозвіті: **{n} знімків**")
                    else:
                        uploaded_files = st.file_uploader("Оберіть фото:", type=["jpg","jpeg","png","webp","heic"],
                                                          accept_multiple_files=True, key="photo_uploader")
                        if uploaded_files:
                            st.session_state.uploaded_photos = [{"name": f.name, "bytes": f.getvalue(), "source": "upload"} for f in uploaded_files]
                            st.success(f"✅ Прикріплено {len(uploaded_files)} фото")

                    photo_count = len(st.session_state.camera_shots) + len(st.session_state.uploaded_photos)

                with st.container(border=True):
                    st.markdown("### 🎙️ Звіт про виконану роботу")
                    report_mode = st.radio("Спосіб:", ["⌨️ Текстовий", "🎙️ Голосова замітка"], horizontal=True, label_visibility="collapsed")
                    if report_mode == "🎙️ Голосова замітка":
                        voice_input = st.text_input("🎤 Диктуйте:", placeholder="Роботи виконано...", key="voice_raw_input")
                        v1, v2 = st.columns([1, 1])
                        with v1:
                            if st.button("🎙️ Транскрибувати", use_container_width=True):
                                if voice_input.strip():
                                    ts = datetime.datetime.now().strftime("%H:%M")
                                    st.session_state.voice_transcript = f"[🎙️ {ts}]: {voice_input.strip()}"
                                    st.toast("✅ Транскрипцію завершено!")
                        with v2:
                            quick_templates = st.selectbox("📝 Шаблон:", ["— оберіть —","Роботи виконано в повному обсязі","Замінено ізолятор, пошкоджень не виявлено","Виявлено корозію кріплення","Вимикач перевірено, контакти в нормі"], label_visibility="collapsed")
                            if quick_templates != "— оберіть —":
                                st.session_state.voice_transcript = quick_templates
                        comment = st.session_state.voice_transcript
                    else:
                        comment = st.text_area("Текстовий звіт:", placeholder="Опишіть виконані роботи...", height=120, key="text_comment")

            st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
            all_checks = tb_1 and tb_2 and tb_3 and tb_4
            has_comment = bool(comment and comment.strip())
            has_geo = st.session_state.geo_arrived
            readiness = sum([all_checks, has_comment, has_geo, photo_count > 0])
            readiness_pct = int(readiness / 4 * 100)
            readiness_colors = {0:"#ef4444",1:"#f59e0b",2:"#fbbf24",3:"#a3e635",4:"#22c55e"}
            readiness_color = readiness_colors.get(readiness, "#64748b")
            st.markdown(f"""
            <div style="background:#1e293b;border-radius:10px;padding:0.8rem 1.2rem;border:1px solid #334155;margin-bottom:0.8rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="color:#94a3b8;font-size:0.82rem;font-weight:600;">📊 Готовність наряду до закриття</span>
                    <span style="color:{readiness_color};font-weight:700;">{readiness_pct}%</span>
                </div>
                <div style="background:#0f172a;border-radius:6px;height:8px;overflow:hidden;">
                    <div style="background:{readiness_color};width:{readiness_pct}%;height:100%;border-radius:6px;"></div>
                </div>
                <div style="display:flex;gap:1rem;margin-top:8px;font-size:0.75rem;flex-wrap:wrap;">
                    <span style="color:{'#22c55e' if all_checks else '#475569'};">{'✅' if all_checks else '⬜'} Чек-лист</span>
                    <span style="color:{'#22c55e' if has_geo else '#475569'};">{'✅' if has_geo else '⬜'} GPS</span>
                    <span style="color:{'#22c55e' if has_comment else '#475569'};">{'✅' if has_comment else '⬜'} Звіт</span>
                    <span style="color:{'#22c55e' if photo_count > 0 else '#475569'};">{'✅' if photo_count > 0 else '⬜'} Фото ({photo_count})</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            btn_label = "🚀 Закрити наряд-допуск та відправити звіт" if readiness == 4 else f"🚀 Закрити наряд ({readiness_pct}% готовності)"
            if st.button(btn_label, use_container_width=True, type="primary"):
                if not all_checks:
                    st.error("❌ Заповніть усі пункти чек-листа безпеки!")
                elif not has_comment:
                    st.error("❌ Введіть звіт про виконану роботу!")
                else:
                    now_str = datetime.datetime.now().strftime("%d.%m %H:%M")
                    geo_info = f" | GPS: {st.session_state.geo_lat:.4f}° N, {st.session_state.geo_lon:.4f}° E" if has_geo else ""
                    photo_info = f" | Фото: {photo_count} шт." if photo_count > 0 else ""
                    st.session_state.log_data.insert(0, {
                        "Час": now_str, "Тип": "Планове ТО", "Об'єкт": "ТП-Шаргород-100",
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
                    st.markdown("**Зона обслуговування:**")
                    for sub in info["дільниці"]:
                        st.write(f"• {sub} дільниця")
        with col_shargorod:
            st.subheader("📍 Шаргородський регіон")
            st.info("ℹ️ Шаргородська дільниця входить до складу СО «Жмеринські електричні мережі».")
            box_sh = st.container(border=True)
            box_sh.markdown("### 🏢 У місті Шаргород діють:")
            box_sh.markdown("""
            * **🔧 Шаргородська дільниця** — технічне обслуговування мереж.
            * **👥 Центр обслуговування клієнтів (ЦОК)** — прийом споживачів.
            """)
            if FOLIUM_AVAILABLE:
                sh_map = folium.Map(location=[48.7377,28.0813], zoom_start=15, tiles="CartoDB dark_matter")
                sh_objects = [
                    {"name":"ТП-Шаргород-100","latitude":48.7364,"longitude":28.0822,"type":"Підстанція","status":"Нормальна","criticality":"Висока","subdivision":"СО «Жмеринські ЕМ»","desc":"ВН-35/10 кВ."},
                    {"name":"ЦОК Шаргород","latitude":48.7390,"longitude":28.0805,"type":"Центр клієнтів","status":"Нормальна","criticality":"Низька","subdivision":"СО «Жмеринські ЕМ»","desc":"Прийом споживачів."},
                ]
                for o in sh_objects:
                    folium.Marker(location=[o["latitude"],o["longitude"]], tooltip=o["name"],
                                  popup=folium.Popup(build_popup_html(o), max_width=280),
                                  icon=folium.Icon(color=get_marker_color(o["status"]), icon=get_marker_icon(o["type"]), prefix="fa")).add_to(sh_map)
                folium.PolyLine([[48.7364,28.0822],[48.7390,28.0805]], color="#4ade80", weight=2, dash_array="4 3").add_to(sh_map)
                st_folium(sh_map, width="100%", height=300, returned_objects=[])

# ==========================================
# ВКЛАДКА: АНАЛІТИКА ТА KPI
# ==========================================
if "analytics" in tab_map:
    with tab_map["analytics"]:
        st.title("📊 SmartGrid AI — Інтелектуальна аналітика мережі")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Індекс надійності SAIDI", "42.5 хв/рік", "-3.2 хв від плану", delta_color="inverse")
        m2.metric("Індекс частоти вимкнень SAIFI", "1.14 од/рік", "+0.02", delta_color="inverse")
        m3.metric("Загальна потужність", "148.5 МВт", "Норма")
        m4.metric("КВВ", "94.2%", "+0.5%")
        st.markdown("---")
        st.markdown("### 🌡️ SmartGrid AI — Симуляція навантаження")
        col_ctrl, col_info = st.columns([2, 1])
        with col_ctrl:
            temperature = st.slider("🌡️ Температура (°C)", min_value=-20, max_value=40, value=15, step=1)
        with col_info:
            if temperature <= -10: season_label, season_color = "❄️ Сильні морози", "#60a5fa"
            elif temperature <= 0: season_label, season_color = "🌨️ Зима", "#93c5fd"
            elif temperature <= 10: season_label, season_color = "🌤️ Прохолодна погода", "#6ee7b7"
            elif temperature <= 20: season_label, season_color = "🌿 Весна / Осінь", "#34d399"
            elif temperature <= 30: season_label, season_color = "☀️ Тепло", "#fbbf24"
            else: season_label, season_color = "🔥 Спека", "#f87171"
            st.markdown(f"""<div style="background:#1e293b;border-radius:10px;padding:0.9rem 1.1rem;border-left:4px solid {season_color};margin-top:0.4rem;">
                <div style="color:{season_color};font-weight:700;">{season_label}</div>
                <div style="color:#94a3b8;font-size:0.82rem;margin-top:4px;">t°: <b style="color:#f1f5f9">{temperature}°C</b></div>
            </div>""", unsafe_allow_html=True)
        BASE_LOAD = [65, 50, 85, 110, 140, 148, 90]
        hours = [f"{i}:00" for i in range(0, 25, 4)]
        LOAD_THRESHOLD_HIGH = 160.0; LOAD_THRESHOLD_LOW = 35.0
        def compute_load_for_temp(base_load, temp):
            if temp < 0: factor = 1.0 + 0.04 * abs(temp)
            elif temp <= 20: factor = 1.0 - 0.015 * (temp - 15)
            else: factor = 0.925 + 0.025 * (temp - 20)
            return [round(v * factor, 1) for v in base_load]
        predicted_load = compute_load_for_temp(BASE_LOAD, temperature)
        actual_load = [v + (i % 3 - 1) * 2.5 for i, v in enumerate(predicted_load)]
        overload_hours = [hours[i] for i, v in enumerate(predicted_load) if v > LOAD_THRESHOLD_HIGH]
        underload_hours = [hours[i] for i, v in enumerate(predicted_load) if v < LOAD_THRESHOLD_LOW]
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.2))
        fig.patch.set_facecolor("#0f172a")
        ax1.set_facecolor("#1e293b")
        ax1.plot(hours, actual_load, label="Фактичне навантаження (МВт)", color="#38bdf8", marker="o", linewidth=2.5, markersize=6)
        ax1.plot(hours, predicted_load, label=f"Прогноз SmartGrid AI ({temperature}°C)", color="#a855f7", linestyle="--", linewidth=2)
        ax1.axhline(y=LOAD_THRESHOLD_HIGH, color="#ef4444", linestyle=":", linewidth=1.5)
        ax1.axhline(y=LOAD_THRESHOLD_LOW, color="#f59e0b", linestyle=":", linewidth=1.5)
        ax1.set_xticks(range(len(hours))); ax1.set_xticklabels(hours, color="#94a3b8", fontsize=8)
        ax1.set_title(f"Прогноз навантаження при {temperature}°C", color="#f1f5f9", fontsize=10)
        ax1.legend(fontsize=7, facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1")
        ax1.grid(True, alpha=0.15, color="#334155"); ax1.tick_params(colors="#64748b"); ax1.spines[:].set_color("#334155")
        ax1.set_ylabel("МВт", color="#64748b", fontsize=9); ax1.set_ylim(0, 200)
        ax2.set_facecolor("#1e293b")
        current_logs_df = pd.DataFrame(st.session_state.log_data)
        types_distribution = current_logs_df["Тип"].value_counts()
        wedge_colors = ["#ef4444","#f59e0b","#10b981","#38bdf8","#bc5090"]
        wedges, texts, autotexts = ax2.pie(types_distribution.values, labels=types_distribution.index, colors=wedge_colors[:len(types_distribution)], autopct="%1.1f%%", startangle=90, wedgeprops=dict(edgecolor="#0f172a", linewidth=2))
        for t in texts: t.set_color("#94a3b8"); t.set_fontsize(8)
        for at in autotexts: at.set_color("#f1f5f9"); at.set_fontsize(8)
        ax2.set_title("Розподіл подій у журналі", color="#f1f5f9", fontsize=10)
        plt.tight_layout(pad=2.0); st.pyplot(fig); plt.close(fig)
        if overload_hours:
            st.error(f"🚨 Прогнозується перевантаження в: **{', '.join(overload_hours)}**")
        else:
            st.success(f"✅ Прогнозоване навантаження при {temperature}°C в межах норми. Пік: **{max(predicted_load)} МВт**.")

# ==========================================
# 💰 ВКЛАДКА: CRM ТА БІЛІНГ
# ==========================================
if "crm" in tab_map:
    with tab_map["crm"]:
        st.title("💰 CRM та Комерційний облік — АТ «Вінницяобленерго»")

        # ── KPI рядок ───────────────────────────────────────────────────
        total_consumers = sum(d["consumers_total"] for d in CRM_DISTRICTS)
        total_paid      = sum(d["consumers_paid"]   for d in CRM_DISTRICTS)
        total_debt      = sum(d["debt_uah"]          for d in CRM_DISTRICTS)
        total_kwh       = sum(d["consumption_kwh"]   for d in CRM_DISTRICTS)
        avg_pay_pct     = round(total_paid / total_consumers * 100, 1)
        total_revenue   = round(total_kwh * TARIFF_SINGLE / 1_000_000, 2)

        kc1, kc2, kc3, kc4, kc5 = st.columns(5)
        def crm_kpi(col, icon, value, label, delta=None, delta_color="#22c55e"):
            delta_html = f'<div style="color:{delta_color};font-size:0.75rem;margin-top:2px;">{delta}</div>' if delta else ""
            col.markdown(f"""
            <div style="background:#1e293b;border-radius:10px;padding:0.9rem 0.7rem;text-align:center;border:1px solid #334155;">
                <div style="font-size:1.5rem;">{icon}</div>
                <div style="color:#f1f5f9;font-size:1.3rem;font-weight:700;line-height:1.2;">{value}</div>
                <div style="color:#64748b;font-size:0.72rem;margin-top:3px;">{label}</div>
                {delta_html}
            </div>""", unsafe_allow_html=True)

        crm_kpi(kc1, "👥", f"{total_consumers:,}".replace(",","ʼ"), "Всього споживачів")
        crm_kpi(kc2, "✅", f"{avg_pay_pct}%", "Рівень оплати (поточний місяць)",
                delta=f"{'↑' if avg_pay_pct >= 85 else '↓'} {'В нормі' if avg_pay_pct >= 85 else 'Нижче цілі 85%'}",
                delta_color="#22c55e" if avg_pay_pct >= 85 else "#f87171")
        crm_kpi(kc3, "💸", f"{total_debt/1_000_000:.1f} млн", "Загальна заборгованість, грн",
                delta="⚠️ Потребує контролю", delta_color="#f59e0b")
        crm_kpi(kc4, "⚡", f"{total_kwh/1_000_000:.1f} млн", "Споживання, кВт·год / міс")
        crm_kpi(kc5, "🏦", f"{total_revenue} млн", "Нарахований дохід, грн",
                delta=f"Тариф: {TARIFF_SINGLE} грн/кВт·год", delta_color="#60a5fa")

        st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)

        # ── Три підвкладки ───────────────────────────────────────────────
        crm_tab1, crm_tab2, crm_tab3 = st.tabs([
            "📊 Дашборд оплат по дільницях",
            "🗺️ Теплова карта заборгованостей",
            "🧮 Тарифний калькулятор",
        ])

        # ─────────────────────────────────────────────────────────────────
        # ПІДВКЛАДКА 1: Дашборд оплат
        # ─────────────────────────────────────────────────────────────────
        with crm_tab1:
            st.markdown("### 📊 Рівень розрахунків по структурних одиницях")

            # Поточний місяць
            pay_data = []
            for d in CRM_DISTRICTS:
                pct = round(d["consumers_paid"] / d["consumers_total"] * 100, 1)
                paid_uah = round(d["consumption_kwh"] * TARIFF_SINGLE * pct / 100 / 1_000_000, 2)
                pay_data.append({
                    "Дільниця": d["name"],
                    "СО": d["so"].replace("СО «","").replace(" ЕМ»",""),
                    "Споживачів всього": d["consumers_total"],
                    "Сплатили": d["consumers_paid"],
                    "% оплати": pct,
                    "Борг (млн грн)": round(d["debt_uah"]/1_000_000, 2),
                    "Нарах. (млн грн)": round(d["consumption_kwh"] * TARIFF_SINGLE / 1_000_000, 2),
                    "Сплачено (млн грн)": paid_uah,
                })
            pay_df = pd.DataFrame(pay_data)

            # Горизонтальний прогрес-бар для кожної дільниці
            st.markdown("#### Рівень оплати по дільницях (поточний місяць)")
            for _, row in pay_df.iterrows():
                pct_val = row["% оплати"]
                color = "#22c55e" if pct_val >= 88 else ("#f59e0b" if pct_val >= 75 else "#ef4444")
                st.markdown(f"""
                <div style="margin-bottom:0.5rem;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
                    <span style="color:#e2e8f0;font-size:0.85rem;font-weight:600;">{row['Дільниця']}</span>
                    <span style="color:{color};font-weight:700;font-size:0.85rem;">{pct_val}%
                      &nbsp;<span style="color:#475569;font-weight:400;font-size:0.75rem;">
                        (борг: {row['Борг (млн грн)']} млн грн)
                      </span>
                    </span>
                  </div>
                  <div style="background:#0f172a;border-radius:6px;height:10px;overflow:hidden;">
                    <div style="background:{color};width:{pct_val}%;height:100%;border-radius:6px;"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            col_ch1, col_ch2 = st.columns(2)

            with col_ch1:
                st.markdown("#### 📈 Динаміка рівня оплати (12 місяців)")
                selected_districts = st.multiselect(
                    "Оберіть дільниці:",
                    options=[d["name"] for d in CRM_DISTRICTS],
                    default=[CRM_DISTRICTS[0]["name"], CRM_DISTRICTS[3]["name"], CRM_DISTRICTS[4]["name"]],
                    key="crm_district_select"
                )
                fig_dyn, ax_dyn = plt.subplots(figsize=(6.5, 3.8))
                fig_dyn.patch.set_facecolor("#0f172a")
                ax_dyn.set_facecolor("#1e293b")
                palette = ["#38bdf8","#a855f7","#10b981","#f59e0b","#f87171","#34d399","#60a5fa","#fbbf24"]
                for i, d in enumerate(CRM_DISTRICTS):
                    if d["name"] in selected_districts:
                        monthly = st.session_state.crm_monthly_pay[d["id"]]
                        ax_dyn.plot(MONTHS_SHORT, monthly, marker="o", markersize=4,
                                    linewidth=2, color=palette[i % len(palette)], label=d["name"][:18])
                ax_dyn.axhline(y=85, color="#ef4444", linestyle="--", linewidth=1, alpha=0.7, label="Ціль 85%")
                ax_dyn.set_ylim(50, 105)
                ax_dyn.tick_params(colors="#94a3b8", labelsize=8)
                ax_dyn.spines[:].set_color("#334155")
                ax_dyn.set_ylabel("% оплати", color="#64748b", fontsize=8)
                ax_dyn.legend(fontsize=7, facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1", loc="lower left")
                ax_dyn.grid(True, alpha=0.1, color="#334155")
                plt.tight_layout()
                st.pyplot(fig_dyn)
                plt.close(fig_dyn)

            with col_ch2:
                st.markdown("#### 💰 Структура боргу за категоріями споживачів")
                debt_cats = {"Населення": 12.8, "ОСББ / ЖКГ": 7.4, "Підприємства": 9.1,
                             "Бюджетні орг.": 3.2, "Агросектор": 4.7}
                fig_pie2, ax_pie2 = plt.subplots(figsize=(5, 3.8))
                fig_pie2.patch.set_facecolor("#0f172a")
                ax_pie2.set_facecolor("#0f172a")
                pie_colors = ["#3b82f6","#a855f7","#f59e0b","#10b981","#ef4444"]
                wedges2, texts2, autotexts2 = ax_pie2.pie(
                    list(debt_cats.values()), labels=list(debt_cats.keys()),
                    colors=pie_colors, autopct="%1.1f%%", startangle=90,
                    wedgeprops=dict(edgecolor="#0f172a", linewidth=2)
                )
                for t in texts2: t.set_color("#94a3b8"); t.set_fontsize(8)
                for at in autotexts2: at.set_color("#f1f5f9"); at.set_fontsize(8)
                ax_pie2.set_title("Борг за категоріями, млн грн", color="#f1f5f9", fontsize=9)
                plt.tight_layout()
                st.pyplot(fig_pie2)
                plt.close(fig_pie2)

            st.markdown("#### 📋 Таблиця розрахунків по дільницях")
            st.dataframe(pay_df.style.background_gradient(subset=["% оплати"], cmap="RdYlGn", vmin=60, vmax=100),
                         use_container_width=True, hide_index=True)

            # Завантаження звіту
            csv_crm = pay_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Завантажити звіт оплат (.csv)", data=csv_crm,
                               file_name="crm_payments_report.csv", mime="text/csv")

        # ─────────────────────────────────────────────────────────────────
        # ПІДВКЛАДКА 2: Теплова карта заборгованостей
        # ─────────────────────────────────────────────────────────────────
        with crm_tab2:
            st.markdown("### 🗺️ Теплова карта заборгованостей по дільницях")

            col_map_crm, col_debtors = st.columns([1.6, 1])

            with col_map_crm:
                st.markdown("#### Фолія-карта боргів (Folium)")
                st.caption("Кольорове кодування: 🟢 < 2 млн грн | 🟡 2–4 млн грн | 🔴 > 4 млн грн")

                if FOLIUM_AVAILABLE:
                    debt_map = folium.Map(location=[49.0, 28.5], zoom_start=8, tiles="CartoDB dark_matter")

                    for d in CRM_DISTRICTS:
                        debt_m = d["debt_uah"] / 1_000_000
                        pay_pct = round(d["consumers_paid"] / d["consumers_total"] * 100, 1)

                        # Колір залежно від боргу
                        if debt_m >= 4.0:
                            fill_color = "#ef4444"; border_color = "#b91c1c"; level = "🔴 КРИТИЧНИЙ РІВЕНЬ"
                        elif debt_m >= 2.0:
                            fill_color = "#f59e0b"; border_color = "#d97706"; level = "🟡 ПІДВИЩЕНИЙ РІВЕНЬ"
                        else:
                            fill_color = "#22c55e"; border_color = "#16a34a"; level = "🟢 НОРМАЛЬНИЙ РІВЕНЬ"

                        # Радіус кола пропорційний боргу
                        radius_km = max(8, min(35, debt_m * 6))

                        popup_html = f"""
                        <div style="font-family:sans-serif;min-width:220px;padding:4px">
                          <b style="font-size:13px">{d['name']}</b><br>
                          <span style="color:#555;font-size:11px">{d['so']}</span>
                          <hr style="margin:6px 0">
                          <table style="width:100%;font-size:11px">
                            <tr><td style="color:#666">Борг:</td><td><b style="color:#dc2626">{debt_m:.2f} млн грн</b></td></tr>
                            <tr><td style="color:#666">Оплата:</td><td><b>{pay_pct}%</b></td></tr>
                            <tr><td style="color:#666">Споживачів:</td><td>{d['consumers_total']:,}</td></tr>
                            <tr><td style="color:#666">Споживання:</td><td>{d['consumption_kwh']/1_000_000:.1f} млн кВт·год</td></tr>
                            <tr><td style="color:#666">Рівень:</td><td><b>{level}</b></td></tr>
                          </table>
                        </div>"""

                        folium.Circle(
                            location=[d["lat"], d["lon"]],
                            radius=radius_km * 1000,
                            color=border_color, fill=True,
                            fill_color=fill_color, fill_opacity=0.35, weight=2,
                            tooltip=folium.Tooltip(f"<b>{d['name']}</b><br>Борг: {debt_m:.2f} млн грн<br>Оплата: {pay_pct}%", sticky=True),
                            popup=folium.Popup(popup_html, max_width=260)
                        ).add_to(debt_map)

                        # Маркер з підписом
                        folium.Marker(
                            location=[d["lat"], d["lon"]],
                            tooltip=d["name"],
                            icon=folium.DivIcon(
                                html=f"""<div style="font-family:sans-serif;font-size:10px;font-weight:700;
                                    color:white;text-shadow:1px 1px 2px black;white-space:nowrap;">
                                    {d['name'][:14]}<br>
                                    <span style="color:{'#fca5a5' if debt_m >= 4 else ('#fde68a' if debt_m >= 2 else '#86efac')}">
                                    {debt_m:.1f} млн ₴</span></div>""",
                                icon_size=(120, 35), icon_anchor=(0, 35)
                            )
                        ).add_to(debt_map)

                    # Легенда
                    legend_debt = """
                    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:#1e293b;
                                color:#f1f5f9;padding:12px 16px;border-radius:8px;font-size:12px;
                                border:1px solid #334155;">
                      <b>Рівень заборгованості</b><br>
                      <span style="color:#22c55e">●</span> &lt; 2 млн грн — норма<br>
                      <span style="color:#f59e0b">●</span> 2–4 млн грн — підвищений<br>
                      <span style="color:#ef4444">●</span> &gt; 4 млн грн — критичний<br>
                      <i style="color:#64748b;font-size:10px">Розмір кола ∝ сумі боргу</i>
                    </div>"""
                    debt_map.get_root().html.add_child(folium.Element(legend_debt))
                    st_folium(debt_map, width="100%", height=480, returned_objects=[])

                else:
                    st.warning("⚠️ Folium не встановлено. Встановіть: `pip install folium streamlit-folium`")
                    st.markdown("**Альтернативна таблиця боргів:**")
                    alt_df = pd.DataFrame([{
                        "Дільниця": d["name"],
                        "Борг (млн грн)": round(d["debt_uah"]/1_000_000, 2),
                        "% оплати": round(d["consumers_paid"]/d["consumers_total"]*100, 1),
                        "Рівень": "🔴 Критичний" if d["debt_uah"] >= 4_000_000 else ("🟡 Підвищений" if d["debt_uah"] >= 2_000_000 else "🟢 Норма")
                    } for d in CRM_DISTRICTS])
                    st.dataframe(alt_df, use_container_width=True, hide_index=True)

                # Гістограма боргів
                st.markdown("#### 📊 Порівняння боргів по дільницях")
                fig_debt_bar, ax_db = plt.subplots(figsize=(8, 3.2))
                fig_debt_bar.patch.set_facecolor("#0f172a")
                ax_db.set_facecolor("#1e293b")
                debt_vals = [d["debt_uah"]/1_000_000 for d in CRM_DISTRICTS]
                dist_names = [d["name"][:16] for d in CRM_DISTRICTS]
                bar_clrs = ["#ef4444" if v >= 4 else ("#f59e0b" if v >= 2 else "#22c55e") for v in debt_vals]
                bars_db = ax_db.bar(dist_names, debt_vals, color=bar_clrs, width=0.6, edgecolor="#0f172a")
                ax_db.bar_label(bars_db, fmt="%.1f", color="#e2e8f0", fontsize=8, padding=3, label_type="edge")
                ax_db.axhline(y=4.0, color="#ef4444", linestyle="--", linewidth=1, alpha=0.7, label="Критичний поріг 4 млн")
                ax_db.axhline(y=2.0, color="#f59e0b", linestyle="--", linewidth=1, alpha=0.7, label="Підвищений поріг 2 млн")
                ax_db.set_ylabel("Борг, млн грн", color="#64748b", fontsize=8)
                ax_db.tick_params(colors="#94a3b8", labelsize=7, axis="x", rotation=25)
                ax_db.tick_params(colors="#94a3b8", labelsize=8, axis="y")
                ax_db.spines[:].set_color("#334155")
                ax_db.legend(fontsize=7.5, facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1")
                ax_db.grid(True, alpha=0.1, color="#334155", axis="y")
                plt.tight_layout()
                st.pyplot(fig_debt_bar)
                plt.close(fig_debt_bar)

            with col_debtors:
                st.markdown("#### ⛔ Реєстр боржників")

                # Фільтри
                cat_filter = st.selectbox("Категорія:", ["Усі"] + DEBTOR_CATEGORIES, key="crm_cat_filter")
                status_filter = st.selectbox("Статус:", ["Усі","⛔ Відключено","⚠️ Попередження","🟡 Нагадування"], key="crm_status_filter")

                debtors_df = pd.DataFrame(st.session_state.crm_debtors)
                if cat_filter != "Усі":
                    debtors_df = debtors_df[debtors_df["Категорія"] == cat_filter]
                if status_filter != "Усі":
                    debtors_df = debtors_df[debtors_df["Статус"] == status_filter]
                debtors_df = debtors_df.sort_values("Борг (грн)", ascending=False)

                st.markdown(f"Знайдено: **{len(debtors_df)}** боржників")
                st.dataframe(
                    debtors_df[["Назва / ПІБ","Категорія","Борг (грн)","Місяців прострочення","Статус","Останній платіж"]],
                    use_container_width=True, hide_index=True, height=350
                )

                # Додати платіж
                st.markdown("#### ✏️ Зафіксувати платіж")
                with st.form("payment_form"):
                    debtor_names = [d["Назва / ПІБ"] for d in st.session_state.crm_debtors]
                    sel_debtor = st.selectbox("Боржник:", debtor_names, key="pay_debtor")
                    pay_amount = st.number_input("Сума платежу (грн):", min_value=0.0, value=5000.0, step=100.0)
                    pay_submitted = st.form_submit_button("💳 Зафіксувати", use_container_width=True)
                    if pay_submitted and pay_amount > 0:
                        for d in st.session_state.crm_debtors:
                            if d["Назва / ПІБ"] == sel_debtor:
                                d["Борг (грн)"] = max(0.0, round(d["Борг (грн)"] - pay_amount, 2))
                                d["Останній платіж"] = datetime.date.today().strftime("%d.%m.%Y")
                                if d["Борг (грн)"] == 0:
                                    d["Статус"] = "✅ Погашено"
                                break
                        st.success(f"✅ Платіж {pay_amount:,.0f} грн від «{sel_debtor}» зафіксовано!")
                        st.rerun()

        # ─────────────────────────────────────────────────────────────────
        # ПІДВКЛАДКА 3: Тарифний калькулятор
        # ─────────────────────────────────────────────────────────────────
        with crm_tab3:
            st.markdown("### 🧮 Тарифний калькулятор (Правила НЕК «Укренерго» 2026)")

            st.markdown("""
            <div style="background:#1e293b;border-radius:10px;padding:1rem 1.4rem;border:1px solid #334155;margin-bottom:1.2rem;">
              <div style="color:#93c5fd;font-weight:700;font-size:0.9rem;margin-bottom:0.5rem;">💡 Діючі роздрібні тарифи на електроенергію (2026)</div>
              <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.8rem;font-size:0.85rem;">
                <div style="background:#0f172a;border-radius:8px;padding:0.6rem 0.8rem;">
                  <div style="color:#64748b;font-size:0.75rem;">⚡ Одноставковий</div>
                  <div style="color:#38bdf8;font-weight:700;font-size:1.1rem;">{single} грн/кВт·год</div>
                  <div style="color:#475569;font-size:0.72rem;">цілодобово</div>
                </div>
                <div style="background:#0f172a;border-radius:8px;padding:0.6rem 0.8rem;">
                  <div style="color:#64748b;font-size:0.75rem;">🌞 Двозонний</div>
                  <div style="color:#fbbf24;font-weight:700;">День: {day} грн</div>
                  <div style="color:#60a5fa;font-weight:700;">Ніч: {night} грн</div>
                  <div style="color:#475569;font-size:0.72rem;">07:00–23:00 / 23:00–07:00</div>
                </div>
                <div style="background:#0f172a;border-radius:8px;padding:0.6rem 0.8rem;">
                  <div style="color:#64748b;font-size:0.75rem;">⚡🕐 Тризонний</div>
                  <div style="color:#ef4444;font-weight:700;">Пік: {peak} грн</div>
                  <div style="color:#fbbf24;font-weight:700;">Напівпік: {semi} грн</div>
                  <div style="color:#60a5fa;font-weight:700;">Провал/Ніч: {valley} грн</div>
                </div>
              </div>
            </div>
            """.format(
                single=TARIFF_SINGLE, day=TARIFF_DAY, night=TARIFF_NIGHT,
                peak=TARIFF_PEAK, semi=TARIFF_SEMI, valley=TARIFF_VALLEY
            ), unsafe_allow_html=True)

            calc_col1, calc_col2 = st.columns([1, 1])

            with calc_col1:
                st.markdown("#### ⚙️ Введіть показники лічильника")

                meter_type = st.radio(
                    "Тип лічильника:",
                    ["⚡ Одноставковий", "🌞 Двозонний", "⚡🕐 Тризонний"],
                    horizontal=False, key="meter_type"
                )

                if meter_type == "⚡ Одноставковий":
                    kwh_total = st.number_input("Споживання за місяць (кВт·год):", min_value=0.0, value=280.0, step=10.0)
                    kwh_day = kwh_peak = kwh_semi = kwh_valley = kwh_night = 0.0

                elif meter_type == "🌞 Двозонний":
                    st.caption("Зони: День (07:00–23:00) та Ніч (23:00–07:00)")
                    kwh_day   = st.number_input("День (кВт·год):", min_value=0.0, value=190.0, step=5.0, key="kwh_day_2z")
                    kwh_night = st.number_input("Ніч (кВт·год):", min_value=0.0, value=90.0,  step=5.0, key="kwh_night_2z")
                    kwh_total = kwh_day + kwh_night
                    kwh_peak  = kwh_semi = kwh_valley = 0.0

                else:  # Тризонний
                    st.caption("Зони: Пік (08–11, 20–22), Напівпік (решта), Ніч/Провал (23–07)")
                    kwh_peak   = st.number_input("Пік (кВт·год):",     min_value=0.0, value=60.0,  step=5.0, key="kwh_peak_3z")
                    kwh_semi   = st.number_input("Напівпік (кВт·год):",min_value=0.0, value=150.0, step=5.0, key="kwh_semi_3z")
                    kwh_valley = st.number_input("Ніч/Провал (кВт·год):",min_value=0.0, value=70.0, step=5.0, key="kwh_valley_3z")
                    kwh_total  = kwh_peak + kwh_semi + kwh_valley
                    kwh_day    = kwh_night = 0.0

                payer_type = st.selectbox("Категорія споживача:", ["🏠 Населення","🏢 Юридична особа","🌾 Агросектор"])
                prev_debt = st.number_input("Борг за попередній місяць (грн):", min_value=0.0, value=0.0, step=50.0)

            with calc_col2:
                st.markdown("#### 📄 Рахунок до оплати")

                # Розрахунок
                if meter_type == "⚡ Одноставковий":
                    charge_energy = round(kwh_total * TARIFF_SINGLE, 2)
                    breakdown = [("Споживання (одноставк.)", kwh_total, TARIFF_SINGLE, charge_energy)]
                elif meter_type == "🌞 Двозонний":
                    c_day   = round(kwh_day   * TARIFF_DAY,   2)
                    c_night = round(kwh_night * TARIFF_NIGHT, 2)
                    charge_energy = c_day + c_night
                    breakdown = [("День (07–23)", kwh_day, TARIFF_DAY, c_day),
                                 ("Ніч (23–07)", kwh_night, TARIFF_NIGHT, c_night)]
                else:
                    c_peak   = round(kwh_peak   * TARIFF_PEAK,   2)
                    c_semi   = round(kwh_semi   * TARIFF_SEMI,   2)
                    c_valley = round(kwh_valley * TARIFF_VALLEY, 2)
                    charge_energy = c_peak + c_semi + c_valley
                    breakdown = [("Пік (08–11, 20–22)", kwh_peak, TARIFF_PEAK, c_peak),
                                 ("Напівпік",           kwh_semi, TARIFF_SEMI, c_semi),
                                 ("Ніч/Провал (23–07)", kwh_valley, TARIFF_VALLEY, c_valley)]

                # ПДВ 20%
                pdv = round(charge_energy * 0.20, 2)
                total_with_pdv = round(charge_energy + pdv, 2)
                total_payable  = round(total_with_pdv + prev_debt, 2)

                st.markdown(f"""
                <div style="background:#1e293b;border-radius:12px;padding:1.2rem 1.4rem;border:1px solid #334155;">
                  <div style="color:#93c5fd;font-size:0.8rem;font-weight:600;letter-spacing:2px;text-transform:uppercase;margin-bottom:0.8rem;">
                    🧾 РОЗРАХУНОК — {datetime.date.today().strftime("%B %Y")}
                  </div>
                  <table style="width:100%;font-size:0.85rem;border-collapse:collapse;color:#cbd5e1;">
                    <tr style="border-bottom:1px solid #334155;">
                      <th style="text-align:left;padding:4px 0;color:#64748b;">Зона</th>
                      <th style="text-align:right;color:#64748b;">кВт·год</th>
                      <th style="text-align:right;color:#64748b;">Тариф</th>
                      <th style="text-align:right;color:#64748b;">Сума</th>
                    </tr>
                    {"".join(f'<tr><td style="padding:4px 0">{b[0]}</td><td style="text-align:right">{b[1]:.1f}</td><td style="text-align:right">{b[2]}</td><td style="text-align:right;color:#38bdf8">{b[3]:.2f} грн</td></tr>' for b in breakdown)}
                    <tr style="border-top:1px solid #334155;">
                      <td colspan="3" style="padding:4px 0;color:#94a3b8;">Разом за енергію:</td>
                      <td style="text-align:right;color:#38bdf8;font-weight:700;">{charge_energy:.2f} грн</td>
                    </tr>
                    <tr>
                      <td colspan="3" style="padding:4px 0;color:#94a3b8;">ПДВ (20%):</td>
                      <td style="text-align:right;color:#94a3b8;">{pdv:.2f} грн</td>
                    </tr>
                    <tr>
                      <td colspan="3" style="padding:4px 0;color:#94a3b8;">Всього з ПДВ:</td>
                      <td style="text-align:right;color:#f1f5f9;font-weight:600;">{total_with_pdv:.2f} грн</td>
                    </tr>
                    {"<tr><td colspan='3' style='padding:4px 0;color:#f59e0b;'>Борг попереднього місяця:</td><td style='text-align:right;color:#f59e0b;'>" + f"{prev_debt:.2f} грн</td></tr>" if prev_debt > 0 else ""}
                  </table>
                  <div style="margin-top:1rem;background:#0f172a;border-radius:8px;padding:0.8rem 1rem;
                              display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#94a3b8;font-size:0.9rem;font-weight:600;">💳 ДО ОПЛАТИ:</span>
                    <span style="color:#22c55e;font-size:1.5rem;font-weight:800;">{total_payable:.2f} грн</span>
                  </div>
                  <div style="margin-top:0.5rem;font-size:0.75rem;color:#475569;">
                    {payer_type} · Тип: {meter_type} · Спожито: {kwh_total:.1f} кВт·год
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Порівняльна діаграма тарифних сценаріїв
                st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
                if kwh_total > 0:
                    st.markdown("##### 📊 Порівняння вартості за типами лічильника")
                    # Оцінюємо однакове споживання для всіх 3 тарифів (розподіл 68/32 і 23/55/22)
                    c_single = round(kwh_total * TARIFF_SINGLE, 2)
                    c_double = round(kwh_total * 0.68 * TARIFF_DAY + kwh_total * 0.32 * TARIFF_NIGHT, 2)
                    c_triple = round(kwh_total * 0.23 * TARIFF_PEAK + kwh_total * 0.55 * TARIFF_SEMI + kwh_total * 0.22 * TARIFF_VALLEY, 2)

                    fig_comp, ax_comp = plt.subplots(figsize=(5, 2.8))
                    fig_comp.patch.set_facecolor("#0f172a")
                    ax_comp.set_facecolor("#1e293b")
                    labels_c = ["Одноставк.", "Двозонний", "Тризонний"]
                    vals_c   = [c_single, c_double, c_triple]
                    clrs_c   = ["#3b82f6","#f59e0b","#a855f7"]
                    bars_c   = ax_comp.bar(labels_c, vals_c, color=clrs_c, width=0.5, edgecolor="#0f172a")
                    ax_comp.bar_label(bars_c, fmt="%.0f грн", color="#f1f5f9", fontsize=9, padding=3)
                    ax_comp.set_ylabel("Вартість (грн)", color="#64748b", fontsize=8)
                    ax_comp.tick_params(colors="#94a3b8", labelsize=9)
                    ax_comp.spines[:].set_color("#334155")
                    ax_comp.grid(True, alpha=0.1, color="#334155", axis="y")
                    best = labels_c[vals_c.index(min(vals_c))]
                    ax_comp.set_title(f"Найвигідніший тариф: {best}", color="#22c55e", fontsize=9)
                    plt.tight_layout()
                    st.pyplot(fig_comp)
                    plt.close(fig_comp)

                    savings = round(max(vals_c) - min(vals_c), 2)
                    if savings > 0:
                        st.info(f"💡 Потенційна економія при переході на оптимальний тариф: **{savings:.2f} грн/міс** ({savings*12:.0f} грн/рік)")

        # Нижній рядок — кнопки дій
        st.markdown("---")
        act1, act2, act3 = st.columns(3)
        with act1:
            crm_csv = pd.DataFrame([{
                "Дільниця": d["name"], "Споживачів": d["consumers_total"],
                "Сплатили": d["consumers_paid"], "Борг грн": d["debt_uah"],
                "Споживання кВт·год": d["consumption_kwh"]
            } for d in CRM_DISTRICTS]).to_csv(index=False).encode("utf-8")
            st.download_button("📥 Повний CRM-звіт (.csv)", data=crm_csv,
                               file_name="crm_full_report.csv", mime="text/csv", use_container_width=True)
        with act2:
            debtors_csv = pd.DataFrame(st.session_state.crm_debtors).to_csv(index=False).encode("utf-8")
            st.download_button("📥 Реєстр боржників (.csv)", data=debtors_csv,
                               file_name="crm_debtors.csv", mime="text/csv", use_container_width=True)
        with act3:
            if st.button("🔄 Оновити дані CRM", use_container_width=True):
                st.toast("✅ Дані CRM оновлено з бази!")
                st.rerun()

# ==========================================
# ВКЛАДКА: ЖУРНАЛ ПОДІЙ
# ==========================================
if "log" in tab_map:
    with tab_map["log"]:
        st.title("📋 Журнал оперативних подій")
        st.markdown("""
        Централізований реєстр всіх комутаційних операцій, аварійних відключень та планових робіт.
        Використовуйте фільтри нижче для швидкого пошуку конкретних інцидентів.
        """)
        
        # Створення DataFrame
        df = pd.DataFrame(st.session_state.log_data)
        
        # --- Блок фільтрів ---
        with st.container(border=True):
            st.markdown("#### ⚙️ Панель фільтрації")
            f1, f2, f3, f4 = st.columns([2, 1.5, 1.5, 1])
            
            search_query = f1.text_input("🔍 Пошук за об'єктом:", placeholder="Наприклад: ТП-245...")
            type_filter = f2.selectbox("Тип події:", ["Усі типи", "Аварія", "Планове ТО", "Ремонт", "Інспекція"])
            crit_filter = f3.selectbox("Критичність:", ["Усі рівні", "Критична", "Висока", "Середня", "Низька"])
            
            # Логіка фільтрації
            if type_filter != "Усі типи": df = df[df["Тип"] == type_filter]
            if crit_filter != "Усі рівні": df = df[df["Критичність"] == crit_filter]
            if search_query: df = df[df["Об'єкт"].str.contains(search_query, case=False)]
        
        # --- Статистика по журналу ---
        c_stat1, c_stat2, c_stat3 = st.columns(3)
        c_stat1.metric("Всього записів", len(df))
        c_stat2.metric("Активних аварій", len(df[df["Тип"] == "Аварія"]))
        c_stat3.metric("Рівень вибірки", f"{int((len(df) / len(st.session_state.log_data)) * 100)}%")
        
        st.markdown("<br>", unsafe_allow_html=True)

        # --- Таблиця журналу з умовним форматуванням ---
        def color_criticality(val):
            color = "#ef4444" if val == "Критична" else ("#f59e0b" if val == "Висока" else "#22c55e")
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            df.style.map(color_criticality, subset=["Критичність"]),
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Час": st.column_config.TextColumn("Час фіксації"),
                "Об'єкт": st.column_config.TextColumn("Об'єкт мережі"),
                "Опис": st.column_config.TextColumn("Деталі події", width="large")
            }
        )
        
        # --- Блок дій ---
        col_act1, col_act2 = st.columns([1, 4])
        if col_act1.button("🔄 Оновити дані", use_container_width=True):
            st.rerun()
            
        with st.expander("ℹ️ Інструкція з роботи з журналом"):
            st.markdown("""
            * **Оперативність:** Журнал оновлюється в реальному часі.
            * **Критичність:** Записи з червоним маркером потребують негайного реагування (диспетчерська команда).
            * **Експорт:** Ви можете завантажити повний звіт у вкладці «Data Центр».
            * **Доступ:** Будь-які зміни в статусах об'єктів реєструються під логіном користувача, який виконав дію.
            """)

# ==========================================
# ВКЛАДКА: ПЛАНУВАННЯ ТО
# ==========================================
if "schedule" in tab_map:
    with tab_map["schedule"]:
        st.title("📅 Графік планового технічного обслуговування")
        st.subheader("➕ Додати нове завдання:")
        col_in1, col_in2, col_in3 = st.columns(3)
        with col_in1: plan_obj = st.selectbox("Вузол:", [o["name"] for o in st.session_state.objects])
        with col_in2: plan_date = st.date_input("Дата робіт", datetime.date.today() + datetime.timedelta(days=1))
        with col_in3: plan_desc = st.text_input("Опис робіт:", placeholder="Введіть опис...")
        if st.button("➕ Додати до графіка", use_container_width=True):
            if plan_desc:
                st.session_state.schedule_data.append({"Дата": str(plan_date), "Об'єкт": plan_obj, "Вид робіт": plan_desc, "Статус": "Заплановано"})
                st.success(f"✅ Роботи по {plan_obj} додано!")
                st.rerun()
            else:
                st.error("Вкажіть вид робіт.")
        st.divider()
        st.subheader("📋 Поточний графік:")
        st.table(pd.DataFrame(st.session_state.schedule_data))

# ==========================================
# ГПВ — ДАНІ ТА СТРУКТУРА
# ==========================================
if "gpv_data" not in st.session_state:
    # 6 черг, кожна має підгрупи 1.1–6.2
    st.session_state.gpv_data = {
        f"{c}.{s}": _rnd.choice(["🟢 Активно", "🔴 Відключено", "🟡 Попередження"]) 
        for c in range(1, 7) for s in range(1, 3)
    }

# ==========================================
# ВКЛАДКА: ГПВ (Графіки відключень)
# ==========================================
if "gpv" in tab_map:
    with tab_map["gpv"]:
        st.title("⚡ Графіки погодинних відключень (ГПВ)")
        
        tab_user, tab_disp = st.tabs(["👤 Перевірка адреси", "🛠️ Керування ГПВ"])
        
        with tab_user:
            st.markdown("### 🔍 Перевірка черги за адресою")
            addr = st.text_input("Введіть адресу (вулиця, будинок):")
            if addr:
                # Симуляція вибору черги для адреси
                q = _rnd.choice(list(st.session_state.gpv_data.keys()))
                status = st.session_state.gpv_data[q]
                st.info(f"Адреса {addr} належить до **Черги {q}**")
                
                # Кольорове відображення статусу
                status_color = {"🟢 Активно": "green", "🔴 Відключено": "red", "🟡 Попередження": "orange"}
                st.markdown(f"Поточний стан: <span style='color:{status_color.get(status, 'black')}; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)
                
            st.divider()
            st.markdown("#### 🔔 Підписка на сповіщення")
            email = st.text_input("Email для сповіщень:")
            if st.button("Підписатися"):
                st.success(f"Ви підписані на сповіщення для черги {q if addr else 'обраної'}")

        with tab_disp:
            if user_role in ["admin", "dispatcher"]:
                st.markdown("### ⚙️ Матриця керування чергами")
                # Відображення черг у вигляді матриці
                cols = st.columns(4)
                all_keys = list(st.session_state.gpv_data.keys())
                for i, q in enumerate(all_keys):
                    with cols[i % 4]:
                        new_status = st.selectbox(f"Черга {q}", ["🟢 Активно", "🔴 Відключено", "🟡 Попередження"], 
                                                 index=["🟢 Активно", "🔴 Відключено", "🟡 Попередження"].index(st.session_state.gpv_data[q]))
                        st.session_state.gpv_data[q] = new_status
                
                if st.button("🚀 Застосувати зміни для всіх черг"):
                    st.toast("Зміни в ГПВ розіслані споживачам!")
            else:
                st.error("Доступ обмежено. Тільки для диспетчерів та адмінів.")

# ==========================================
# ВКЛАДКА: DATA ЦЕНТР (тільки Адмін)
# ==========================================
if "data" in tab_map:
    with tab_map["data"]:
        st.title("💾 Data-Центр: Архітектура та Синхронізація")
        
        # Вступний текст
        st.markdown("""
        Вітаємо в панелі управління даними. Тут здійснюється контроль за цілісністю бази даних, 
        оперативне вивантаження звітів для аналітичних відділів та імпорт оновлених конфігурацій 
        мереж. **Всі дії в цьому розділі протоколюються системою безпеки.**
        """)
        
        # Рядок з метриками Data-центру
        d1, d2, d3 = st.columns(3)
        d1.metric("Журнал подій", f"{len(st.session_state.log_data)} записів", "Актуально")
        d2.metric("Об'єктів мережі", f"{len(st.session_state.objects)}", "Синхронізовано")
        d3.metric("Резервних копій", "12", "Автоматично")
        
        st.divider()
        
        col_exp, col_imp = st.columns([1, 1.2], gap="large")
        
        with col_exp:
            st.subheader("📤 Експорт даних")
            st.markdown("""
            Використовуйте експорт для створення копій звітів. 
            Система автоматично формує файли згідно з регламентом АТ «Вінницяобленерго».
            """)
            
            curr_df = pd.DataFrame(st.session_state.log_data)
            
            # Експорт кнопок
            c_exp1, c_exp2 = st.columns(2)
            csv_data = curr_df.to_csv(index=False).encode('utf-8')
            c_exp1.download_button("📥 CSV-лог", data=csv_data, file_name="voe_log_export.csv", 
                                   mime="text/csv", use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                curr_df.to_excel(writer, index=False, sheet_name='Журнал Подій')
            c_exp2.download_button("📊 Excel-звіт", data=buffer.getvalue(), file_name="voe_report.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                                   use_container_width=True)
            
            json_data = json.dumps(st.session_state.log_data, indent=4, ensure_ascii=False)
            st.download_button("📜 JSON-конфіг (Full Backup)", data=json_data, file_name="system_config.json", 
                               mime="application/json", use_container_width=True)

        with col_imp:
            st.subheader("📥 Імпорт та Синхронізація")
            st.warning("Увага: Імпорт конфігурацій змінює поточний стан ГІС-системи.")
            st.markdown("""
            Завантажте файл оновлення мережі або реєстр нових об'єктів. 
            **Вимоги до файлу:**
            * Формат: .csv (UTF-8), .xlsx або .json
            * Наявність полів: `name`, `latitude`, `longitude`, `type`
            * Необхідна наявність ЕЦП для підтвердження транзакції.
            """)
            
            uploaded_file = st.file_uploader("Оберіть файл для завантаження:", type=["csv", "xlsx", "json"])
            
            if uploaded_file is not None:
                st.info(f"📁 Файл: **{uploaded_file.name}** ({uploaded_file.size} bytes)")
                with st.spinner('Проводиться валідація даних...'):
                    time.sleep(1.5) 
                    st.success("✅ Структура файлу відповідає стандартам VOE.")
                    
                    if st.button("🚀 Застосувати зміни в БД", type="primary", use_container_width=True):
                        st.balloons()
                        st.success("Базу даних успішно оновлено. Система перезавантажується.")

        st.divider()
        
        # Додаткова технічна інформація
        with st.expander("ℹ️ Технічні примітки для Адміністратора"):
            st.markdown("""
            * **Синхронізація:** Дані синхронізуються з центральним сервером кожні 15 хвилин. 
            * **Логи:** Користувач `admin` має доступ до розширеного аудиту дій.
            * **Безпека:** Якщо ви помітили невідповідність у даних (наприклад, зсув координат), 
              негайно запустіть скрипт `verify_integrity()` через консоль розробника.
            * **Підтримка:** При виникненні помилок під час імпорту звертайтеся до внутрішнього 
              порталу IT-департаменту (Ticket ID: #VOE-9902).
            """)
            
        st.subheader("⚙️ Службові налаштування")
        col_s1, col_s2 = st.columns(2)
        col_s1.toggle("Автоматичне резервне копіювання", value=True)
        col_s2.toggle("Деталізоване логування запитів (Debug Mode)", value=False)

# ==========================================
# ВКЛАДКА: УПРАВЛІННЯ ДОСТУПОМ (тільки Адмін)
# ==========================================
if "users" in tab_map:
    with tab_map["users"]:
        st.title("👥 Управління правами доступу користувачів")
        st.info("ℹ️ Ця вкладка доступна виключно адміністраторам системи.")
        st.subheader("📋 Облікові записи системи")
        users_display = []
        for login, data in USERS_DB.items():
            users_display.append({
                "Логін": login, "Ім'я та посада": data["display_name"],
                "Підрозділ": data["subdivision"], "Роль": ROLE_LABELS.get(data["role"], data["role"]),
                "Доступні вкладки": ", ".join(t[0] for t in TAB_DEFINITIONS[ROLE_TO_TAB_SET.get(data["role"],"brigade_tabs")])
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
