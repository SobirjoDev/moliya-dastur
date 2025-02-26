from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.utils import platform
from kivy.config import Config
from datetime import datetime
import sqlite3
import os

# Platformani aniqlash
IS_MOBILE = platform in ('android', 'ios')

# Mobil qurilma uchun config
if IS_MOBILE:
    Window.softinput_mode = 'below_target'  # Klaviatura ochilganda UI ko'tariladi
    FONT_SIZE = dp(14)
    BUTTON_HEIGHT = dp(50)
    INPUT_HEIGHT = dp(45)
else:
    FONT_SIZE = dp(12)
    BUTTON_HEIGHT = dp(40)
    INPUT_HEIGHT = dp(35)

# Ranglar
COLORS = {
    "background": [0.96, 0.96, 0.96, 1],  # #F5F5F5
    "primary": [0.13, 0.59, 0.95, 1],  # #2196F3
    "expense": [0.96, 0.26, 0.21, 1],  # #F44336
    "income": [0.30, 0.69, 0.31, 1],  # #4CAF50
    "text": [0.2, 0.2, 0.2, 1],  # #333333
}


class DatabaseManager:
    def __init__(self):
        # Ma'lumotlar bazasi faylini ilovaning ma'lumotlar direktoriyasida saqlash
        if IS_MOBILE:
            data_dir = os.path.join(App.get_running_app().user_data_dir, 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            db_path = os.path.join(data_dir, 'moliya.db')
        else:
            db_path = 'moliya.db'

        self.db = sqlite3.connect(db_path)
        self.create_tables()
        self._init_default_categories()

    def create_tables(self):
        """Jadvallarni yaratish"""
        cursor = self.db.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            date TEXT,
            type TEXT,
            category TEXT,
            amount REAL,
            description TEXT
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT
        )''')

        self.db.commit()

    def _init_default_categories(self):
        """Standart kategoriyalarni qo'shish"""
        default_categories = {
            'income': ['Ish haqi', 'Sovg\'a', 'Biznes', 'Boshqa kirimlar'],
            'expense': ['Oziq-ovqat', 'Transport', 'Kommunal', 'Kiyim-kechak', 'Boshqa xarajatlar']
        }

        cursor = self.db.cursor()
        for type_, categories in default_categories.items():
            for category in categories:
                cursor.execute("SELECT id FROM categories WHERE name = ? AND type = ?", (category, type_))
                if not cursor.fetchone():
                    self.add_category(category, type_)

    def get_categories(self, category_type):
        """Kategoriyalarni olish"""
        cursor = self.db.cursor()
        cursor.execute("SELECT name FROM categories WHERE type = ?", (category_type,))
        return [row[0] for row in cursor.fetchall()]

    def add_transaction(self, date, t_type, category, amount, description):
        """Yangi tranzaksiya qo'shish"""
        cursor = self.db.cursor()
        cursor.execute('''
        INSERT INTO transactions (date, type, category, amount, description)
        VALUES (?, ?, ?, ?, ?)
        ''', (date, t_type, category, amount, description))
        self.db.commit()

    def get_transactions(self):
        """Barcha tranzaksiyalarni olish"""
        cursor = self.db.cursor()
        cursor.execute("SELECT date, type, category, amount, description FROM transactions ORDER BY date DESC")
        return cursor.fetchall()

    def add_category(self, name, category_type):
        """Yangi kategoriya qo'shish"""
        cursor = self.db.cursor()
        cursor.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, category_type))
        self.db.commit()

    def get_balance(self):
        """Umumiy balansni hisoblash"""
        cursor = self.db.cursor()

        # Kirimlarni hisoblash
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'income'")
        income = cursor.fetchone()[0] or 0

        # Chiqimlarni hisoblash
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'expense'")
        expense = cursor.fetchone()[0] or 0

        return income - expense

    # ... (DatabaseManager klassi metodlari oldingi koddan o'zgarishsiz qoladi)


class MainScreen(Screen):
    def __init__(self, db_manager, **kwargs):
        super().__init__(**kwargs)
        self.db_manager = db_manager

        # Asosiy layout
        self.main_layout = BoxLayout(orientation='vertical', spacing=dp(10))

        # ScrollView ichida asosiy content
        self.scroll_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=dp(10),
            size_hint_y=None
        )
        self.scroll_layout.bind(minimum_height=self.scroll_layout.setter('height'))

        # ScrollView
        self.scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False
        )
        self.scroll.add_widget(self.scroll_layout)

        self.add_widgets()
        self.main_layout.add_widget(self.scroll)
        self.add_widget(self.main_layout)

    def add_widgets(self):
        # Balans ko'rsatkichi
        self.balance_label = Label(
            text='Balans: 0 so\'m',
            color=COLORS["text"],
            size_hint_y=None,
            height=dp(40),
            font_size=FONT_SIZE * 1.2
        )
        self.scroll_layout.add_widget(self.balance_label)

        # Kiritish qismi
        input_grid = GridLayout(
            cols=2,
            spacing=dp(10),
            padding=dp(10),
            size_hint_y=None,
            height=dp(200) if IS_MOBILE else dp(160)
        )

        # Summa kiritish
        input_grid.add_widget(Label(
            text='Summa:',
            size_hint_y=None,
            height=INPUT_HEIGHT,
            font_size=FONT_SIZE
        ))
        self.amount_input = TextInput(
            multiline=False,
            input_filter='float',
            size_hint_y=None,
            height=INPUT_HEIGHT,
            font_size=FONT_SIZE
        )
        input_grid.add_widget(self.amount_input)

        # Turi tanlash
        input_grid.add_widget(Label(
            text='Turi:',
            size_hint_y=None,
            height=INPUT_HEIGHT,
            font_size=FONT_SIZE
        ))
        self.type_spinner = Spinner(
            text='Kirim',
            values=['Kirim', 'Chiqim'],
            size_hint_y=None,
            height=INPUT_HEIGHT,
            font_size=FONT_SIZE
        )
        input_grid.add_widget(self.type_spinner)

        # Kategoriya tanlash
        input_grid.add_widget(Label(
            text='Kategoriya:',
            size_hint_y=None,
            height=INPUT_HEIGHT,
            font_size=FONT_SIZE
        ))
        self.category_spinner = Spinner(
            text='Kategoriyani tanlang',
            values=self.db_manager.get_categories('income'),
            size_hint_y=None,
            height=INPUT_HEIGHT,
            font_size=FONT_SIZE
        )
        input_grid.add_widget(self.category_spinner)

        # Izoh kiritish
        input_grid.add_widget(Label(
            text='Izoh:',
            size_hint_y=None,
            height=INPUT_HEIGHT,
            font_size=FONT_SIZE
        ))
        self.description_input = TextInput(
            multiline=False,
            size_hint_y=None,
            height=INPUT_HEIGHT,
            font_size=FONT_SIZE
        )
        input_grid.add_widget(self.description_input)

        self.scroll_layout.add_widget(input_grid)

        # Qo'shish tugmasi
        add_button = Button(
            text='Qo\'shish',
            size_hint_y=None,
            height=BUTTON_HEIGHT,
            background_color=COLORS["primary"],
            font_size=FONT_SIZE
        )
        add_button.bind(on_press=self.add_transaction)
        self.scroll_layout.add_widget(add_button)

        # Tranzaksiyalar ro'yxati
        self.transaction_list = GridLayout(
            cols=1,
            spacing=dp(5),
            size_hint_y=None,
            padding=dp(5)
        )
        self.transaction_list.bind(minimum_height=self.transaction_list.setter('height'))
        self.scroll_layout.add_widget(Label(
            text='Tranzaksiyalar:',
            size_hint_y=None,
            height=dp(30),
            font_size=FONT_SIZE
        ))
        self.scroll_layout.add_widget(self.transaction_list)

        # Kategoriyalar spinner'ini yangilash
        self.type_spinner.bind(text=self.update_categories)

        # Ma'lumotlarni yangilash
        self.update_balance()
        self.update_transactions()

    def update_categories(self, instance, value):
        """Kategoriyalar ro'yxatini yangilash"""
        category_type = 'income' if value == 'Kirim' else 'expense'
        self.category_spinner.values = self.db_manager.get_categories(category_type)
        self.category_spinner.text = 'Kategoriyani tanlang'

    def add_transaction(self, instance):
        """Yangi tranzaksiya qo'shish"""
        try:
            if not self.amount_input.text:
                self.show_popup("Xato", "Summani kiriting!")
                return

            if self.category_spinner.text == 'Kategoriyani tanlang':
                self.show_popup("Xato", "Kategoriyani tanlang!")
                return

            amount = float(self.amount_input.text)
            t_type = 'income' if self.type_spinner.text == 'Kirim' else 'expense'
            category = self.category_spinner.text
            description = self.description_input.text

            self.db_manager.add_transaction(
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                t_type,
                category,
                amount,
                description
            )

            self.amount_input.text = ''
            self.description_input.text = ''
            self.update_transactions()
            self.update_balance()

        except ValueError:
            self.show_popup("Xato", "Noto'g'ri summa kiritildi!")

    def update_balance(self):
        """Balansni yangilash"""
        balance = self.db_manager.get_balance()
        self.balance_label.text = f'Balans: {balance:,.0f} so\'m'

    def update_transactions(self):
        """Tranzaksiyalar ro'yxatini yangilash"""
        self.transaction_list.clear_widgets()
        transactions = self.db_manager.get_transactions()

        for date, t_type, category, amount, description in transactions:
            # Tranzaksiya ma'lumotlarini formatlash
            amount_str = f"{amount:,.0f} so'm"
            type_str = "Kirim" if t_type == "income" else "Chiqim"
            transaction_text = f"[{date}] {type_str} | {category}\n{amount_str}"
            if description:
                transaction_text += f"\nIzoh: {description}"

            # Tranzaksiya uchun label
            label = Label(
                text=transaction_text,
                size_hint_y=None,
                height=dp(60),
                halign='left',
                text_size=(None, None),
                color=COLORS["income"] if t_type == "income" else COLORS["expense"]
            )
            label.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            self.transaction_list.add_widget(label)

    def show_popup(self, title, message):
        """Popup xabarni ko'rsatish"""
        popup = Popup(
            title=title,
            content=Label(text=message),
            size_hint=(None, None),
            size=(dp(300), dp(200))
        )
        popup.open()


class Moliya_Dasturi(App):
    def build(self):
        # Ilova sozlamalari
        if IS_MOBILE:
            Window.clearcolor = COLORS["background"]
        else:
            Window.size = (400, 600)
            Window.minimum_width = 300
            Window.minimum_height = 400

        self.db_manager = DatabaseManager()
        sm = ScreenManager()
        sm.add_widget(MainScreen(self.db_manager, name='main'))
        return sm


if __name__ == '__main__':
    if not IS_MOBILE:
        # Desktop uchun sozlamalar
        Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
        Config.set('kivy', 'exit_on_escape', '1')

    Moliya_Dasturi().run()