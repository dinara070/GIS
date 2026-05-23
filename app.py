import sys
import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QPushButton, QListWidget, QListWidgetItem, 
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QIcon

# Інтеграція Matplotlib з PyQt6
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- СТИЛІЗАЦІЯ ДОДАТКУ (QSS) ---
THEME_CSS = """
QMainWindow {
    background-color: #0f172a;
}
QTabWidget::pane {
    border: 1px solid #1e293b;
    background-color: #0f172a;
}
QTabBar::tab {
    background: #1e293b;
    color: #94a3b8;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 120px;
}
QTabBar::tab:selected {
    background: #185FA5;
    color: white;
}
QTabBar::tab:hover:!selected {
    background: #334155;
    color: #f8fafc;
}
QLabel {
    color: #f8fafc;
}
QPushButton {
    background-color: #185FA5;
    color: white;
    border: none;
    padding: 8px 15px;
    border-radius: 5px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #1e40af;
}
QPushButton:pressed {
    background-color: #1e3a8a;
}
"""

# --- КОМПОНЕНТ ІНТЕРАКТИВНОЇ МАПИ ---
class InteractiveMap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 500)
        self.parent_view = parent
        
        # Данні об'єктів (координати у % від розміру віджета)
        self.objects = [
            {"name": "ТП-12", "type": "substation", "x": 0.27, "y": 0.16, "status": "Нормальна", "desc": "ВН-110 кВ, Навантаження: 70%"},
            {"name": "ТП-28", "type": "substation", "x": 0.50, "y": 0.22, "status": "Нормальна", "desc": "ВН-35 кВ, Навантаження: 45%"},
            {"name": "ТП-245", "type": "substation", "x": 0.68, "y": 0.30, "status": "АВАРІЯ", "desc": "ВН-10 кВ, Навантаження: 95%! Потребує заміни"},
            {"name": "ТП-67", "type": "substation", "x": 0.82, "y": 0.18, "status": "Нормальна", "desc": "ВН-35 кВ, Навантаження: 30%"},
            {"name": "Оп. №8", "type": "pole", "x": 0.30, "y": 0.38, "status": "Норма", "desc": "ЖБ СВ-110, Задовільний стан"},
            {"name": "Оп. №9", "type": "pole", "x": 0.35, "y": 0.46, "status": "Попередження", "desc": "Пошкоджено ізолятор після грози"},
            {"name": "Оп. №10", "type": "pole", "x": 0.40, "y": 0.54, "status": "Норма", "desc": "ЖБ СВ-110, Огляд: 2024-05"},
            {"name": "Бригада 1", "type": "brigade", "x": 0.42, "y": 0.70, "status": "В роботі", "desc": "Екіпаж Іваненко М."},
            {"name": "Бригада 2", "type": "brigade", "x": 0.75, "y": 0.45, "status": "Вільна", "desc": "Екіпаж Коваль В."}
        ]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фон мапи
        painter.fillRect(self.rect(), QColor("#1a2332"))
        
        # Сітка мапи
        pen_grid = QPen(QColor(255, 255, 255, 10), 1)
        painter.setPen(pen_grid)
        w, h = self.width(), self.height()
        for i in range(1, 5):
            painter.drawLine(0, int(h * i / 5), w, int(h * i / 5))
            painter.drawLine(int(w * i / 5), 0, int(w * i / 5), h)

        # Малювання ЛЕП (ліній зв'язку)
        pen_line = QPen(QColor("#F2A623"), 2)
        painter.setPen(pen_line)
        # Головна шина підстанцій
        p1 = (int(w*0.27), int(h*0.16))
        p2 = (int(w*0.50), int(h*0.22))
        p3 = (int(w*0.68), int(h*0.30))
        painter.drawLine(p1[0], p1[1], p2[0], p2[1])
        painter.drawLine(p2[0], p2[1], p3[0], p3[1])

        # Відгалуження на опори
        pen_pole_line = QPen(QColor("#3B8BD4"), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen_pole_line)
        po1 = (int(w*0.30), int(h*0.38))
        po2 = (int(w*0.35), int(h*0.46))
        po3 = (int(w*0.40), int(h*0.54))
        painter.drawLine(p1[0], p1[1], po1[0], po1[1])
        painter.drawLine(po1[0], po1[1], po2[0], po2[1])
        painter.drawLine(po2[0], po2[1], po3[0], po3[1])

        # Малювання об'єктів мапи
        for obj in self.objects:
            ox = int(obj["x"] * w)
            oy = int(obj["y"] * h)
            
            if obj["type"] == "substation":
                if obj["status"] == "АВАРІЯ":
                    painter.setBrush(QBrush(QColor("#3a0800")))
                    painter.setPen(QPen(QColor("#E24B4A"), 2))
                    painter.drawRect(ox - 10, oy - 10, 20, 20)
                    painter.setPen(QPen(QColor("#E24B4A")))
                    painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                    painter.drawText(ox - 5, oy + 5, "⚠")
                else:
                    painter.setBrush(QBrush(QColor("#2a1800")))
                    painter.setPen(QPen(QColor("#F2A623"), 2))
                    painter.drawRect(ox - 10, oy - 10, 20, 20)
                    painter.setPen(QPen(QColor("#F2A623")))
                    painter.setFont(QFont("Arial", 8))
                    painter.drawText(ox - 5, oy + 5, "⚡")
                    
            elif obj["type"] == "pole":
                if obj["status"] == "Попередження":
                    painter.setBrush(QBrush(QColor("#E24B4A")))
                    painter.setPen(QPen(QColor("#F09595"), 1.5))
                else:
                    painter.setBrush(QBrush(QColor("#3B8BD4")))
                    painter.setPen(QPen(QColor("#85B7EB"), 1.5))
                painter.drawEllipse(ox - 5, oy - 5, 10, 10)
                
            elif obj["type"] == "brigade":
                painter.setBrush(QBrush(QColor("#1D9E75") if obj["status"] == "В роботі" else QColor("#185FA5")))
                painter.setPen(QPen(QColor("#ffffff"), 1.5))
                painter.drawEllipse(ox - 11, oy - 11, 22, 22)
                painter.setPen(QPen(QColor("#ffffff")))
                painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
                painter.drawText(ox - 7, oy + 4, "Б1" if "1" in obj["name"] else "Б2")

            # Підписи об'єктів
            painter.setPen(QPen(QColor(255, 255, 255, 180)))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(ox + 12, oy + 4, obj["name"])

    def mousePressEvent(self, event):
        w, h = self.width(), self.height()
        click_x = event.position().x()
        click_y = event.position().y()
        
        # Пошук об'єкта під кліком
        for obj in self.objects:
            ox = obj["x"] * w
            oy = obj["y"] * h
            distance = ((ox - click_x)**2 + (oy - click_y)**2)**0.5
            if distance < 15:
                if self.parent_view:
                    self.parent_view.update_sidebar(obj)
                break

# --- ВКАДКА 1: ДИСПЕТЧЕР (МАПА ТА БІЧНА ПАНЕЛЬ) ---
class DispatchView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Ліва частина: Мапа
        self.map_widget = InteractiveMap(self)
        layout.addWidget(self.map_widget, stretch=4)
        
        # Права частина: Бічна панель
        self.sidebar = QFrame()
        self.sidebar.setStyleSheet("background-color: #111827; border-left: 1px solid #1e293b;")
        self.sidebar.setFixedWidth(280)
        sb_layout = QVBoxLayout(self.sidebar)
        
        self.title_lbl = QLabel("Оберіть об'єкт")
        self.title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8; padding-bottom: 10px;")
        sb_layout.addWidget(self.title_lbl)
        
        self.info_lbl = QLabel("Клікніть на підстанцію або опору на карті для отримання повної інформації.")
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        sb_layout.addWidget(self.info_lbl)
        
        sb_layout.addStretch()
        
        # Секція швидких дій бригад
        sb_layout.addWidget(QLabel("<b>Оперативні Бригади:</b>"))
        self.b1_btn = QPushButton("Бригада 1: В роботі (Зайнята)")
        self.b1_btn.setStyleSheet("background-color: #065f46; font-size: 11px;")
        self.b2_btn = QPushButton("Бригада 2: Вільна (Призначити)")
        self.b2_btn.setStyleSheet("background-color: #1e3a8a; font-size: 11px;")
        sb_layout.addWidget(self.b1_btn)
        sb_layout.addWidget(self.b2_btn)
        
        layout.addWidget(self.sidebar, stretch=1)

    def update_sidebar(self, obj):
        self.title_lbl.setText(f"{obj['name']} [{obj['status']}]")
        status_color = "#ef4444" if obj['status'] == "АВАРІЯ" else "#f59e0b" if obj['status'] == "Попередження" else "#10b981"
        self.title_lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {status_color};")
        
        text = f"<b>Тип:</b> {obj['type'].upper()}<br><br>" \
               f"<b>Статус системи:</b> {obj['status']}<br><br>" \
               f"<b>Опис/Специфікація:</b><br>{obj['desc']}<br><br>" \
               f"<i>Історія ремонтів синхронізована з ГІС базою даних.</i>"
        self.info_lbl.setText(text)

# --- ВКЛАДКА 2: МОБІЛЬНИЙ ІНТЕРФЕЙС СТРАЖА ---
class MobileView(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QHBoxLayout(self)
        
        # Імітація мобільного телефона у центрі екрану
        phone_frame = QFrame()
        phone_frame.setFixedSize(320, 580)
        phone_frame.setStyleSheet("background-color: #0f172a; border: 8px solid #334155; border-radius: 24px;")
        phone_layout = QVBoxLayout(phone_frame)
        phone_layout.setContentsMargins(5,5,5,5)
        
        # Верхня плашка мобільного додатка
        top_bar = QLabel("📱 Польовий ГІС-Клієнт (Бригада 1)")
        top_bar.setStyleSheet("background-color: #185FA5; color: white; padding: 8px; font-weight: bold; border-radius: 10px; font-size: 11px;")
        top_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        phone_layout.addWidget(top_bar)
        
        # Секція поточної задачі
        task_box = QFrame()
        task_box.setStyleSheet("background-color: #1e293b; border-radius: 10px; padding: 5px;")
        tb_layout = QVBoxLayout(task_box)
        tb_layout.addWidget(QLabel("<b>Поточне завдання:</b> <font color='#ef4444'>Аварія на ТП-245</font>"))
        tb_layout.addWidget(QLabel("<font color='#94a3b8'>Локація: вул. Польова, 2.4км</font>"))
        phone_layout.addWidget(task_box)
        
        # Внутрішній перемикач вкладок мобільного додатка
        self.mob_stack = QStackedWidget()
        
        # Мобільна вкладка 1: Навігація
        nav_widget = QWidget()
        nav_l = QVBoxLayout(nav_widget)
        nav_l.addWidget(QLabel("<b>Маршрут до об'єкта:</b>"))
        nav_l.addWidget(QLabel("• Розрахунковий час: 13 хв\n• GPS Статус: Активний\n• Координати: 49.5521 N, 27.9612 E"))
        self.mob_stack.addWidget(nav_widget)
        
        # Мобільна вкладка 2: Паспорт
        pass_widget = QWidget()
        pass_l = QVBoxLayout(pass_widget)
        pass_l.addWidget(QLabel("<b>Технічний паспорт об'єкта:</b>"))
        pass_l.addWidget(QLabel("• Об'єкт: ТП-245 (ВН-10 кВ)\n• Трансформатор: ТМ-400/10\n• Рік випуску: 2001\n• Запобіжники: ПК-10 3х25А"))
        self.mob_stack.addWidget(pass_widget)
        
        # Мобільна вкладка 3: Звіт
        rep_widget = QWidget()
        rep_l = QVBoxLayout(rep_widget)
        rep_l.addWidget(QLabel("<b>Подати звіт про виконання:</b>"))
        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Введіть коментар щодо усунення аварії...")
        self.comment_input.setStyleSheet("background-color: #1e293b; color: white; border: 1px solid #475569;")
        rep_l.addWidget(self.comment_input)
        
        send_rep_btn = QPushButton("✅ Позначити як виконано")
        send_rep_btn.setStyleSheet("background-color: #10b981;")
        send_rep_btn.clicked.connect(self.close_task)
        rep_l.addWidget(send_rep_btn)
        self.mob_stack.addWidget(rep_widget)
        
        phone_layout.addWidget(self.mob_stack)
        
        # Кнопки керування мобільними підвкладками
        btn_layout = QHBoxLayout()
        b_nav = QPushButton("Маршрут")
        b_pass = QPushButton("Паспорт")
        b_rep = QPushButton("Звіт")
        for b in [b_nav, b_pass, b_rep]:
            b.setStyleSheet("background-color: #334155; font-size: 10px; padding: 4px;")
            btn_layout.addWidget(b)
        b_nav.clicked.connect(lambda: self.mob_stack.setCurrentIndex(0))
        b_pass.clicked.connect(lambda: self.mob_stack.setCurrentIndex(1))
        b_rep.clicked.connect(lambda: self.mob_stack.setCurrentIndex(2))
        
        phone_layout.addLayout(btn_layout)
        main_layout.addWidget(phone_frame)

    def close_task(self):
        self.comment_input.setText("Завдання успішно виконано та надіслано в систему!")

# --- ВКЛАДКА 3: АНАЛІТИКА ТА KPI (МАТПЛОТЛІБ) ---
class AnalyticsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # KPI плашки верхнього рівня
        kpi_layout = QHBoxLayout()
        kpis = [
            ("Аварій цього місяця", "12", "#ef4444"),
            ("Закрито нарядів", "47", "#10b981"),
            ("Сер. час реагування", "38 хв", "#38bdf8"),
            ("Об'єктів на ТО", "7", "#f59e0b")
        ]
        for title, value, color in kpis:
            box = QFrame()
            box.setStyleSheet(f"background-color: #1e293b; border-radius: 8px; border: 1px solid #334155;")
            bl = QVBoxLayout(box)
            l1 = QLabel(title)
            l1.setStyleSheet("font-size: 11px; color: #94a3b8;")
            l2 = QLabel(value)
            l2.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
            bl.addWidget(l1)
            bl.addWidget(l2)
            kpi_layout.addWidget(box)
            
        layout.addLayout(kpi_layout)
        
        # Графіки Matplotlib
        fig = Figure(figsize=(5, 3), facecolor='#0f172a')
        self.canvas = FigureCanvas(fig)
        
        # Графік 1: Аварії за типами
        ax1 = fig.add_subplot(121)
        ax1.set_facecolor('#0f172a')
        categories = ['Підстанції', 'Кабелі', 'Опори', 'Трансф.']
        values = [12, 8, 5, 4]
        ax1.bar(categories, values, color=['#ef4444', '#f59e0b', '#38bdf8', '#10b981'])
        ax1.set_title("Аварії по типах (2026)", color='white', fontsize=10)
        ax1.tick_params(colors='white', labelsize=8)
        
        # Графік 2: Розподіл статусів нарядів
        ax2 = fig.add_subplot(122)
        ax2.set_facecolor('#0f172a')
        labels = ['Відкриті', 'В роботі', 'Закриті']
        sizes = [5, 8, 34]
        ax2.pie(sizes, labels=labels, colors=['#ef4444', '#f59e0b', '#10b981'], autopct='%1.1f%%', textprops={'color':"w", 'fontsize':8})
        ax2.set_title("Статус нарядів", color='white', fontsize=10)
        
        layout.addWidget(self.canvas)

# --- ВКЛАДКА 4: ЖУРНАЛ ПОДІЙ ---
class LogView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Фільтри
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Пошук за назвою об'єкта...")
        self.search_input.setStyleSheet("background-color: #1e293b; color: white; padding: 6px;")
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Усі типи", "Аварія", "Планове ТО", "Ремонт"])
        self.type_combo.setStyleSheet("background-color: #1e293b; color: white; padding: 6px;")
        
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.type_combo)
        layout.addLayout(filter_layout)
        
        # Таблиця
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Час", "Тип", "Об'єкт", "Опис"])
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e293b; color: white; gridline-color: #334155; }
            QHeaderView::section { background-color: #0f172a; color: #94a3b8; font-weight: bold; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.SectionResizeMode.Stretch)
        
        # Статичні дані для таблиці журналу
        self.log_data = [
            ("23.05 09:14", "Аварія", "ТП-245", "Відключення трансформатора, немає напруги"),
            ("23.05 08:52", "Аварія", "Оп. №9", "Пошкоджено ізолятор після грози"),
            ("23.05 07:30", "Планове ТО", "ТП-12", "Регламентне обслуговування"),
            ("22.05 18:45", "Ремонт", "КЛ-3", "Замінено кабельну муфту 10 кВ")
        ]
        
        self.populate_table(self.log_data)
        layout.addWidget(self.table)
        
        self.search_input.textChanged.connect(self.filter_data)
        self.type_combo.currentIndexChanged.connect(self.filter_data)

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(value)
                if col_idx == 1 and value == "Аварія":
                    item.setForeground(QColor("#ef4444"))
                self.table.setItem(row_idx, col_idx, item)

    def filter_data(self):
        search_text = self.search_input.text().lower()
        selected_type = self.type_combo.currentText()
        
        filtered = []
        for row in self.log_data:
            match_search = search_text in row[2].lower() or search_text in row[3].lower()
            match_type = selected_type == "Усі типи" or selected_type == row[1]
            if match_search and match_type:
                filtered.append(row)
        self.populate_table(filtered)

# --- ВКЛАДКА 5: ПЛАНУВАННЯ ТО (КАЛЕНДАР) ---
class CalendarView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("<h3>Календар регламентного технічного обслуговування (ТО)</h3>"))
        
        # Спрощена реалізація списку найближчих ТО робіт
        self.todo_list = QListWidget()
        self.todo_list.setStyleSheet("background-color: #1e293b; color: white; font-size: 13px; padding: 10px;")
        
        tasks = [
            "📅 [06.05.2026] ТП-12 — Регламентне ТО трансформатора (Планове)",
            "📅 [19.05.2026] КЛ-3 — Діагностика силового кабелю 10 кВ (Виконується)",
            "📅 [23.05.2026] ТП-245 — Капітальний ремонт за результатами аварії (Терміново)",
            "📅 [28.05.2026] Оп. №11 — Заміна застарілої дерев'яної опори (Заплановано)"
        ]
        
        for t in tasks:
            item = QListWidgetItem(t)
            if "Терміново" in t:
                item.setForeground(QColor("#ef4444"))
            elif "Планове" in t:
                item.setForeground(QColor("#38bdf8"))
            self.todo_list.addItem(item)
            
        layout.addWidget(self.todo_list)
        
        add_btn = QPushButton("➕ Додати нове планове ТО")
        layout.addWidget(add_btn)

# --- ГОЛОВНЕ ВІКНО ПРОГРАМИ ---
class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ГІС Диспетчерська Система Регіональних Електромереж v2.0")
        self.setMinimumSize(1024, 700)
        
        # Ініціалізація віджета вкладок (Main Topbar)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Додавання панелей (модулів системи)
        self.tabs.addTab(DispatchView(), "Диспетчер мапи")
        self.tabs.addTab(MobileView(), "Мобільний клієнт")
        self.tabs.addTab(AnalyticsView(), "Аналітика та KPI")
        self.tabs.addTab(LogView(), "Журнал подій")
        self.tabs.addTab(CalendarView(), "Планування ТО")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(THEME_CSS)
    
    # Встановлення глобального шрифту додатка
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainApplication()
    window.show()
    sys.exit(app.exec())
