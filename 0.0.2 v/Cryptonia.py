import os
import math
import random
import pygame
import pygame_gui
from config import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, BACKGROUND_COLOR, TEXT_COLOR, CRYPTO_GREEN
from trading import LineChart

class GameState:
    MAIN_MENU = "main_menu"
    EARN_SCREEN = "earn_screen"
    TRADING_SCREEN = "trading_screen"
    CASINO_SCREEN = "casino_screen"

class Upgrade:
    def __init__(self, cost, multiplier, image_name):
        self.cost = cost
        self.multiplier = multiplier
        self.image_name = image_name
        self.purchased = False

class CryptoClicker:
    def __init__(self):
        # Инициализация pygame
        pygame.init()
        
        # Создание главного окна
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Cryptonia")
        
        # Создание менеджера UI для pygame_gui
        self.ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # Установка часов для контроля FPS
        self.clock = pygame.time.Clock()
        
        self.running = True
        
        # Текущее состояние игры
        self.current_state = GameState.MAIN_MENU
        
        # Загрузка шрифта
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 36)
        
        # Параметры кнопки
        self.button_base_size = 200
        self.button_current_size = 200
        self.button_target_size = 200
        self.button_scale_duration = 0.08
        self.button_scale_time = 0
        
        # Позиция круглой кнопки
        self.mine_button_rect = pygame.Rect(0, 0, self.button_base_size, self.button_base_size)
        self.mine_button_rect.center = (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 50)
        
        # Баланс и улучшения
        self.balance = 100.0
        self.click_value = 1.0
        self.current_upgrade_index = 0
        
        # Автоклик
        self.auto_click_active = False
        self.auto_click_duration = 0
        self.auto_click_timer = 0
        self.auto_click_interval = 0.01  # клик каждые 0.5 секунд
        self.auto_click_elapsed = 0
        self.auto_click_cost = 300  # стоимость автоклика
        self.auto_click_cooldown = 300  # 5 минут в секундах
        self.auto_click_cooldown_timer = 0  # таймер кулдауна
        
        # Счетчик кликов пробелом для скрытия подсказки
        self.space_clicks_count = 0
        self.max_space_clicks_to_hide = 2
        
        # Список улучшений
        self.upgrades = [
            Upgrade(500, 1.5, "mine_button_upgrade1.png"),
            Upgrade(1000, 2.5, "mine_button_upgrade2.png"),
            Upgrade(2000, 5.0, "mine_button_upgrade3.png")
        ]
        
        # Загрузка изображений кнопок
        self.button_images = self.load_button_images()
        self.current_button_image = self.button_images[0]
        
        # Эффекты пульсации при клике
        self.click_effects = []
        
        # Эффекты покупки улучшения
        self.upgrade_effects = []
        
        # Эффекты автоклика
        self.auto_click_effects = []
        
        # Падающие монеты (для главного меню)
        self.coins = []
        self.coin_spawn_interval = 0.28  # реже спавним
        self.coin_spawn_timer = 0.0
        self.coin_max_count = 28  # меньше монет
        self.coin_base_image = self.load_coin_base_image()
        
        # Торговые позиции по символам
        self.positions = {}
        # История закрытых сделок
        self.order_history = []  # list of dicts: {symbol, entry, exit, margin, leverage, pnl, pct, reason}
        # Хранилище графиков по символам: отдельный LineChart для каждого символа
        self.charts = {}
        # Текст информации о позиции для отрисовки под графиком
        self.trade_info_text = "No position"
        
        # Создание UI элементов
        self.create_main_menu()
        self.create_earn_screen()
        self.create_casino_screen()
        self.create_trading_screen()

    def load_button_images(self):
        """Загрузка всех изображений кнопок"""
        images = []
        
        # Базовое изображение
        images.append(self.load_single_button_image("mine_button.png", "Базовое"))
        
        # Изображения улучшений
        for i, upgrade in enumerate(self.upgrades):
            images.append(self.load_single_button_image(upgrade.image_name, f"Улучшение {i+1}"))
        
        return images

    def load_single_button_image(self, image_name, description):
        """Загрузка одного изображения кнопки"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            assets_dir = os.path.join(script_dir, "assets")
            image_path = os.path.join(assets_dir, image_name)
            
            if not os.path.exists(image_path):
                print(f"Изображение {description} не найдено, создаю временное: {image_path}")
                return self.create_temp_button_image((self.button_base_size, self.button_base_size), description)
                
            image = pygame.image.load(image_path).convert_alpha()
            print(f"Изображение {description} успешно загружено!")
            return pygame.transform.scale(image, (self.button_base_size, self.button_base_size))
            
        except Exception as e:
            print(f"Ошибка загрузки изображения {description}: {e}")
            return self.create_temp_button_image((self.button_base_size, self.button_base_size), description)

    def create_temp_button_image(self, size, description):
        """Создание временного изображения кнопки"""
        surf = pygame.Surface(size, pygame.SRCALPHA)
        
        # Разные цвета для разных уровней улучшений
        colors = {
            "Базовое": (65, 105, 225),      # Royal Blue
            "Улучшение 1": (50, 205, 50),   # Lime Green
            "Улучшение 2": (255, 165, 0),   # Orange
            "Улучшение 3": (220, 20, 60)    # Crimson
        }
        
        color = colors.get(description, (65, 105, 225))
        
        # Градиентный фон
        for i in range(size[0]//2):
            alpha = 255 - (i * 255 // (size[0]//2))
            pygame.draw.circle(surf, (*color, alpha), (size[0]//2, size[1]//2), size[0]//2 - i)
        
        # Белая обводка
        pygame.draw.circle(surf, (255, 255, 255), (size[0]//2, size[1]//2), size[0]//2 - 5, 3)
        
        # Текст
        font = pygame.font.Font(None, 30)
        text = font.render(description, True, (255, 255, 255))
        text_rect = text.get_rect(center=(size[0]//2, size[1]//2))
        surf.blit(text, text_rect)
        
        return surf

    def load_coin_base_image(self):
        """Загружает базовое изображение монеты для анимации в меню"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            assets_dir = os.path.join(script_dir, "assets")
            image_path = os.path.join(assets_dir, "mine_button.png")
            if not os.path.exists(image_path):
                # Фолбэк: маленький временный кружок
                return self.create_temp_button_image((32, 32), "Базовое")
            image = pygame.image.load(image_path).convert_alpha()
            return image
        except Exception:
            return self.create_temp_button_image((32, 32), "Базовое")

    def spawn_coin(self):
        """Создать новую падающую монету (для главного меню)"""
        size = random.randint(22, 38)  # монеты чуть больше
        # Стартовая позиция по X — по всей ширине окна
        x = random.uniform(0, WINDOW_WIDTH)
        y = -size - random.uniform(0, WINDOW_HEIGHT * 0.2)
        # Вертикальная скорость
        vy = random.uniform(80, 120)  # плавнее падение
        # Небольшое горизонтальное покачивание будет за счет синусоиды
        sway_amplitude = random.uniform(12, 26)
        sway_speed = random.uniform(0.6, 1.2)
        sway_phase = random.uniform(0, math.tau)
        # Поворот
        angle = random.uniform(0, 360)
        rot_speed = random.uniform(-45, 45)  # мягче вращение
        # Пре-скейлим изображение под размер
        scaled = pygame.transform.smoothscale(self.coin_base_image, (size, size))
        coin = {
            'x': x,
            'y': y,
            'vy': vy,
            'sway_amp': sway_amplitude,
            'sway_speed': sway_speed,
            'sway_phase': sway_phase,
            'angle': angle,
            'rot_speed': rot_speed,
            'size': size,
            'image': scaled,
            'life': 1.0,  # для легкого затухания в конце
            'base_x': x
        }
        self.coins.append(coin)

    def update_coins(self, dt):
        """Обновление анимации монет для главного меню"""
        # Спавним новые монеты
        if len(self.coins) < self.coin_max_count:
            self.coin_spawn_timer -= dt
            if self.coin_spawn_timer <= 0:
                self.spawn_coin()
                # варьируем интервал появления
                self.coin_spawn_timer = random.uniform(self.coin_spawn_interval * 0.6, self.coin_spawn_interval * 1.4)

        # Обновляем существующие
        time_sec = pygame.time.get_ticks() / 1000.0
        for coin in self.coins[:]:
            coin['y'] += coin['vy'] * dt
            coin['angle'] = (coin['angle'] + coin['rot_speed'] * dt) % 360
            # Горизонтальное покачивание (не накапливаем x, а считаем относительно базовой позиции для плавности)
            sway = math.sin(time_sec * coin['sway_speed'] + coin['sway_phase']) * coin['sway_amp']
            coin['x'] = coin['base_x'] + sway
            # Удаляем, если улетела ниже экрана
            if coin['y'] > WINDOW_HEIGHT + coin['size']:
                self.coins.remove(coin)

    def render_coins(self):
        """Отрисовка монет на фоне главного меню"""
        for coin in self.coins:
            rotated = pygame.transform.rotozoom(coin['image'], -coin['angle'], 1.0)
            rect = rotated.get_rect(center=(int(coin['x']), int(coin['y'])))
            # Легкая прозрачность по размеру, чтобы мелкие были чуть прозрачнее
            alpha = max(80, min(230, int(200 * (coin['size'] / 28))))
            rotated.set_alpha(alpha)
            self.screen.blit(rotated, rect)

    def create_main_menu(self):
        """Создание элементов главного меню"""
        # Кнопка Earn
        self.earn_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 150, 250), (300, 60)),  
            text="Earn",
            manager=self.ui_manager
        )
        
        # Кнопка Trading
        self.trading_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 150, 330), (300, 60)),  
            text="Trading",
            manager=self.ui_manager
        )
        
        # Кнопка Casino
        self.casino_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 150, 410), (300, 60)),  
            text="Casino",
            manager=self.ui_manager
        )
        
        # Скрываем кнопки изначально
        self.hide_main_menu()

    def create_earn_screen(self):
        """Создание элементов экрана Earn"""
        # Кнопка возврата в главное меню
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((50, 50), (120, 50)),
            text="Back",
            manager=self.ui_manager
        )
        
        # Заголовок экрана Earn
        self.earn_title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 100, 100), (200, 50)),
            text="",
            manager=self.ui_manager
        )
        
        # Label для отображения баланса
        self.balance_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((WINDOW_WIDTH - 300, 50), (250, 50)),
            text=f"Balance: ${self.balance:.2f}",
            manager=self.ui_manager
        )
        
        # Label для отображения значения клика
        self.click_value_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((WINDOW_WIDTH - 300, 100), (250, 50)),
            text=f"Per click: ${self.click_value:.1f}",
            manager=self.ui_manager
        )
        
        # Кнопка улучшения (уменьшенный размер)
        self.upgrade_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 200, WINDOW_HEIGHT - 150), (190, 50)),
            text="",
            manager=self.ui_manager
        )
        
        # Кнопка автоклика (уменьшенный размер)
        self.auto_click_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 + 10, WINDOW_HEIGHT - 150), (190, 50)),
            text="",
            manager=self.ui_manager
        )
        
        # Подсказка для пробела
        self.space_hint = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 150, WINDOW_HEIGHT - 80), (300, 50)),
            text="Нажмите SPACE для клика",
            manager=self.ui_manager
        )
        
        # Таймер автоклика
        self.auto_click_timer_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((WINDOW_WIDTH - 300, 150), (250, 50)),
            text="",
            manager=self.ui_manager
        )
        
        # Обновляем текст кнопок
        self.update_upgrade_button_text()
        self.update_auto_click_button_text()
        
        # Скрываем элементы экрана Earn изначально
        self.hide_earn_screen()

    def create_casino_screen(self):
        """Создание элементов экрана Casino"""
        # Заголовок экрана Casino
        self.casino_title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 100, 100), (200, 50)),
            text="Casino Screen",
            manager=self.ui_manager
        )
        
        # Информация о казино
        self.casino_info = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 200, 180), (400, 80)),
            text="",
            manager=self.ui_manager
        )
        
        # Скрываем элементы экрана Casino изначально
        self.hide_casino_screen()

    def create_trading_screen(self):
        """Создание элементов экрана Trading"""
        # Заголовок Trading
        self.trading_title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((60, 60), (220, 40)),
            text="",
            manager=self.ui_manager
        )
        # Текущая цена
        self.trading_price = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((60, 100), (260, 30)),
            text="COOKIEUSDT: --",
            manager=self.ui_manager
        )
        # Область графика
        # Чарт слева, справа панель выбора и шкала цен
        right_panel_w = 200  # чуть уже, чтобы освободить место под график
        scale_margin = 60     # шкалу делаем шире
        # Фиксированные координаты и размеры чарта (статичное расположение)
        chart_rect = pygame.Rect(
            60, 150,
            WINDOW_WIDTH - (60 + right_panel_w + 40 + scale_margin),
            WINDOW_HEIGHT - 260
        )
        # Единая горизонтальная скорость прокрутки для всех символов
        self.chart_sample_interval = 0.10
        # Создаём отдельные графики для каждой пары
        cookie_chart = LineChart(chart_rect, max_points=240, y_min=20.0, y_max=60.0)
        cookie_chart.sample_interval = self.chart_sample_interval
        cookie_chart.step_min = -1.5
        cookie_chart.step_max = 1.5
        cookie_chart.inertia = 0.90
        cookie_chart.mid_pull = 0.03
        cookie_chart.line_color = pygame.Color(*CRYPTO_GREEN)
        cookie_chart.last_value = 40.0
        for _ in range(8):
            cookie_chart.push_value(cookie_chart.last_value)

        pump_chart = LineChart(chart_rect, max_points=240, y_min=80.0, y_max=500)
        pump_chart.sample_interval = self.chart_sample_interval  # одинаковая скорость вправо
        pump_chart.step_min = -10.0
        pump_chart.step_max = 10.0
        pump_chart.inertia = 0.42
        pump_chart.mid_pull = 0.002
        pump_chart.line_color = pygame.Color(*CRYPTO_GREEN)
        pump_chart.last_value = 100.0
        for _ in range(8):
            pump_chart.push_value(pump_chart.last_value)

        self.charts = {
            "COOKIEUSDT": cookie_chart,
            "PUMPUSDT": pump_chart,
        }

        # Выбор пары (справа)
        self.trading_symbol = "COOKIEUSDT"
        panel_left = WINDOW_WIDTH - right_panel_w - 40
        self.trading_pair_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((panel_left, 140), (right_panel_w, 30)),
            text="Select Pair",
            manager=self.ui_manager
        )
        self.trading_cookie_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((panel_left, 180), (right_panel_w, 40)),
            text="COOKIEUSDT",
            manager=self.ui_manager
        )
        self.trading_pump_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((panel_left, 230), (right_panel_w, 40)),
            text="PUMPUSDT",
            manager=self.ui_manager
        )

        # Сделаем кнопки более прозрачными (полупрозрачный фон)
        # Значения альфа: normal ~120, hovered ~160, active ~180
        semi_normal = pygame.Color(40, 120, 200, 120)
        semi_hover = pygame.Color(40, 120, 200, 160)
        semi_active = pygame.Color(40, 120, 200, 180)
        for btn in (self.trading_cookie_btn, self.trading_pump_btn):
            btn.colours['normal_bg'] = semi_normal
            btn.colours['hovered_bg'] = semi_hover
            btn.colours['active_bg'] = semi_active
            # Текст можно сделать чуть менее ярким
            btn.colours['normal_text'] = pygame.Color(230, 230, 240)
            btn.colours['hovered_text'] = pygame.Color(255, 255, 255)
            btn.colours['active_text'] = pygame.Color(255, 255, 255)
            btn.rebuild()

        # Блок торговли: сумма, плечо, кнопки Buy/Sell, информация о позиции
        controls_top = 290
        self.trade_amount_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((panel_left, controls_top), (right_panel_w, 24)),
            text="Amount ($)",
            manager=self.ui_manager
        )
        self.trade_amount_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((panel_left, controls_top + 26), (right_panel_w, 28)),
            manager=self.ui_manager
        )
        self.trade_amount_input.set_text("100")

        self.trade_leverage_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((panel_left, controls_top + 60), (right_panel_w, 24)),
            text="Leverage",
            manager=self.ui_manager
        )
        leverage_options = [f"{i}x" for i in range(1, 11)]
        self.trade_leverage_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=leverage_options,
            starting_option="1x",
            relative_rect=pygame.Rect((panel_left, controls_top + 84), (right_panel_w, 28)),
            manager=self.ui_manager
        )

        self.trade_buy_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((panel_left, controls_top + 120), (right_panel_w, 36)),
            text="Buy",
            manager=self.ui_manager
        )
        self.trade_sell_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((panel_left, controls_top + 162), (right_panel_w, 36)),
            text="Sell",
            manager=self.ui_manager
        )

        # Информация по позиции
        self.trade_info_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((panel_left, controls_top + 204), (right_panel_w, 120)),
            text="No position",
            manager=self.ui_manager
        )

        # Кнопка истории (правый нижний угол)
        self.history_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH - 140, WINDOW_HEIGHT - 60), (120, 40)),
            text="History",
            manager=self.ui_manager
        )
        # Окно истории создадим по требованию (для корректного восстановления после закрытия)
        self.history_window = None
        self.history_textbox = None

        # Текущий актив по умолчанию
        self.trading_symbol = "COOKIEUSDT"
        self.trading_chart = self.charts[self.trading_symbol]

        self.hide_trading_screen()

    def hide_main_menu(self):
        """Скрыть элементы главного меню"""
        self.earn_button.hide()
        self.trading_button.hide()
        self.casino_button.hide()

    def hide_earn_screen(self):
        """Скрыть элементы экрана Earn"""
        self.back_button.hide()
        self.earn_title.hide()
        self.balance_label.hide()
        self.click_value_label.hide()
        self.upgrade_button.hide()
        self.auto_click_button.hide()
        self.space_hint.hide()
        self.auto_click_timer_label.hide()

    def hide_casino_screen(self):
        """Скрыть элементы экрана Casino"""
        self.casino_title.hide()
        self.casino_info.hide()

    def hide_trading_screen(self):
        """Скрыть элементы экрана Trading"""
        # скрываем только UI-элементы, сам график рисуем вручную
        self.trading_title.hide()
        self.trading_price.hide()
        self.trading_pair_label.hide()
        self.trading_cookie_btn.hide()
        self.trading_pump_btn.hide()
        self.back_button.hide()
        # Скрываем общий лейбл баланса при уходе с Trading (в главном меню он не нужен)
        self.balance_label.hide()
        # Скрываем торговые контролы
        self.trade_amount_label.hide()
        self.trade_amount_input.hide()
        self.trade_leverage_label.hide()
        self.trade_leverage_dropdown.hide()
        self.trade_buy_button.hide()
        self.trade_sell_button.hide()
        self.trade_info_label.hide()
        self.history_button.hide()
        if self.history_window is not None and hasattr(self.history_window, 'visible'):
            try:
                self.history_window.hide()
            except Exception:
                pass

    def update_upgrade_button_text(self):
        """Обновление текста кнопки улучшения"""
        if self.current_upgrade_index < len(self.upgrades):
            upgrade = self.upgrades[self.current_upgrade_index]
            self.upgrade_button.set_text(f"Upgrade: ${upgrade.cost}")
            
            # Меняем цвет кнопки в зависимости от доступности
            if self.balance >= upgrade.cost:
                self.upgrade_button.colours['normal_bg'] = pygame.Color('#4CAF50')  # Зеленый
                self.upgrade_button.colours['hovered_bg'] = pygame.Color('#45a049')
                self.upgrade_button.colours['active_bg'] = pygame.Color('#3d8b40')
                self.upgrade_button.rebuild()
            else:
                self.upgrade_button.colours['normal_bg'] = pygame.Color('#f44336')  # Красный
                self.upgrade_button.colours['hovered_bg'] = pygame.Color('#da190b')
                self.upgrade_button.colours['active_bg'] = pygame.Color('#ba000d')
                self.upgrade_button.rebuild()
        else:
            self.upgrade_button.set_text("All upgrades!")
            self.upgrade_button.disable()

    def update_auto_click_button_text(self):
        """Обновление текста кнопки автоклика"""
        if self.auto_click_active:
            self.auto_click_button.set_text(f"Auto: {self.auto_click_timer:.1f}s")
            self.auto_click_button.disable()
        elif self.auto_click_cooldown_timer > 0:
            minutes = int(self.auto_click_cooldown_timer // 60)
            seconds = int(self.auto_click_cooldown_timer % 60)
            self.auto_click_button.set_text(f"Auto: {minutes:02d}:{seconds:02d}")
            self.auto_click_button.disable()
        else:
            self.auto_click_button.set_text(f"Auto: ${self.auto_click_cost}")
            self.auto_click_button.enable()
            
            # Меняем цвет кнопки в зависимости от доступности
            if self.balance >= self.auto_click_cost:
                self.auto_click_button.colours['normal_bg'] = pygame.Color('#2196F3')  # Синий
                self.auto_click_button.colours['hovered_bg'] = pygame.Color('#1976D2')
                self.auto_click_button.colours['active_bg'] = pygame.Color('#0D47A1')
                self.auto_click_button.rebuild()
            else:
                self.auto_click_button.colours['normal_bg'] = pygame.Color('#f44336')  # Красный
                self.auto_click_button.colours['hovered_bg'] = pygame.Color('#da190b')
                self.auto_click_button.colours['active_bg'] = pygame.Color('#ba000d')
                self.auto_click_button.rebuild()

    def show_main_menu(self):
        """Показать главное меню"""
        self.hide_earn_screen()
        self.hide_casino_screen()
        self.hide_trading_screen()
        
        self.earn_button.show()
        self.trading_button.show()
        self.casino_button.show()
        
        self.current_state = GameState.MAIN_MENU

    def show_earn_screen(self):
        """Показать экран Earn"""
        self.hide_main_menu()
        self.hide_casino_screen()
        self.hide_trading_screen()
        
        self.back_button.show()
        self.earn_title.show()
        self.balance_label.show()
        self.click_value_label.show()
        self.upgrade_button.show()
        self.auto_click_button.show()
        
        # Показываем подсказку только если еще не сделано достаточно кликов
        if self.space_clicks_count < self.max_space_clicks_to_hide:
            self.space_hint.show()
        else:
            self.space_hint.hide()
            
        self.auto_click_timer_label.show()
        
        self.current_state = GameState.EARN_SCREEN

    def show_casino_screen(self):
        """Показать экран Casino"""
        self.hide_main_menu()
        self.hide_earn_screen()
        self.hide_trading_screen()
        
        self.back_button.show()
        self.balance_label.show()
        self.casino_title.show()
        self.casino_info.show()
        
        self.current_state = GameState.CASINO_SCREEN

    def show_trading_screen(self):
        """Показать экран Trading"""
        self.hide_main_menu()
        self.hide_earn_screen()
        self.hide_casino_screen()

        self.trading_title.show()
        self.back_button.show()
        self.trading_pair_label.show()
        self.trading_cookie_btn.show()
        self.trading_pump_btn.show()
        # Показываем баланс на экране Trading
        self.balance_label.show()
        # Показываем торговые контролы
        self.trade_amount_label.show()
        self.trade_amount_input.show()
        self.trade_leverage_label.show()
        self.trade_leverage_dropdown.show()
        self.trade_buy_button.show()
        self.trade_sell_button.show()
        # Информацию о позиции рисуем кастомно под графиком
        self.history_button.show()

        self.current_state = GameState.TRADING_SCREEN

    def set_trading_symbol(self, symbol: str):
        """Смена активного символа без сброса данных графика"""
        if symbol not in ("COOKIEUSDT", "PUMPUSDT"):
            return
        self.trading_symbol = symbol
        self.trading_chart = self.charts[self.trading_symbol]
        # Обновить лейбл позиции для нового символа
        self.update_trade_info()

    def get_current_price(self) -> float:
        if self.trading_chart.data:
            return float(self.trading_chart.data[-1])
        return 0.0

    def parse_leverage(self) -> int:
        try:
            opt = self.trade_leverage_dropdown.selected_option
            return int(opt.replace('x', ''))
        except Exception:
            return 1

    def handle_trade_buy(self):
        amount_text = self.trade_amount_input.get_text().strip()
        try:
            amount = float(amount_text)
        except Exception:
            return
        if amount <= 0 or self.balance < amount:
            return
        price = self.get_current_price()
        if price <= 0:
            return
        leverage = self.parse_leverage()
        pos = self.positions.get(self.trading_symbol)
        if pos is None:
            pos = {
                'margin': 0.0,
                'entry_price': 0.0,
                'leverage': leverage,
                'liquidated': False
            }
        # Если уже есть позиция и другое плечо — используем текущее плечо позиции
        if pos['margin'] > 0 and pos['leverage'] != leverage:
            leverage = pos['leverage']
            # синхронизируем дропдаун
            self.trade_leverage_dropdown.selected_option = f"{leverage}x"
            self.trade_leverage_dropdown.rebuild()
        # Взвешенное усреднение цены входа по нотионалу
        new_notional = amount * leverage
        old_notional = pos['margin'] * pos['leverage']
        total_notional = old_notional + new_notional
        if total_notional > 0:
            pos['entry_price'] = (pos.get('entry_price', price) * old_notional + price * new_notional) / total_notional
        else:
            pos['entry_price'] = price
        pos['margin'] = pos['margin'] + amount
        pos['leverage'] = leverage
        # При открытии/доливке позиции статус ликвидации снимаем
        pos['liquidated'] = False
        self.positions[self.trading_symbol] = pos
        # списываем маржу
        self.balance -= amount
        self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
        self.update_trade_info()

    def handle_trade_sell(self):
        pos = self.positions.get(self.trading_symbol)
        if not pos or pos['margin'] <= 0:
            return
        price = self.get_current_price()
        if price <= 0:
            return
        margin = pos['margin']
        leverage = pos['leverage']
        entry = pos['entry_price']
        pnl = margin * leverage * ((price / entry) - 1.0)
        # Возвращаем маржу + PnL
        self.balance += (margin + pnl)
        self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
        # Сохраняем в историю
        pct = ((price / entry) - 1.0) * 100.0 * leverage if entry > 0 else 0.0
        self.order_history.append({
            'symbol': self.trading_symbol,
            'entry': entry,
            'exit': price,
            'margin': margin,
            'leverage': leverage,
            'pnl': pnl,
            'pct': pct,
            'reason': 'Closed'
        })
        self.update_history_text()
        # Закрываем позицию
        pos['margin'] = 0.0
        self.positions[self.trading_symbol] = pos
        self.update_trade_info()

    def update_trade_info(self):
        # Обновить блок информации по текущему символу
        pos = self.positions.get(self.trading_symbol)
        price = self.get_current_price()
        if not pos:
            self.trade_info_text = "No position"
            return
        if pos.get('liquidated'):
            self.trade_info_text = "Liquidation!"
            return
        if pos['margin'] <= 0:
            self.trade_info_text = "No position"
            return
        entry = pos['entry_price']
        leverage = pos['leverage']
        margin = pos['margin']
        if price > 0 and entry > 0:
            pct = ((price / entry) - 1.0) * 100.0 * leverage
            pnl = margin * leverage * ((price / entry) - 1.0)
            text = f"Entry: {entry:.2f}\nLev: {leverage}x  Margin: ${margin:.2f}\nPnL: ${pnl:.2f} ({pct:+.2f}%)"
        else:
            text = f"Entry: {entry:.2f}\nLev: {leverage}x  Margin: ${margin:.2f}\nPnL: --"
        self.trade_info_text = text

    def check_liquidations(self):
        """Проверить все открытые позиции на ликвидацию (-100%)."""
        for symbol, pos in list(self.positions.items()):
            if not pos or pos.get('liquidated') or pos.get('margin', 0.0) <= 0:
                continue
            chart = self.charts.get(symbol)
            if not chart or not chart.data:
                continue
            price = float(chart.data[-1])
            entry = pos.get('entry_price', 0.0)
            if price <= 0 or entry <= 0:
                continue
            margin = pos['margin']
            leverage = pos.get('leverage', 1)
            pnl = margin * leverage * ((price / entry) - 1.0)
            equity = margin + pnl
            if equity <= 0:
                # Ликвидация: полностью теряем маржу, позиция закрывается
                pos['margin'] = 0.0
                pos['liquidated'] = True
                self.positions[symbol] = pos
                # Запишем в историю
                pct = -100.0
                self.order_history.append({
                    'symbol': symbol,
                    'entry': entry,
                    'exit': price,
                    'margin': margin,
                    'leverage': leverage,
                    'pnl': -margin,  # потеря всей маржи
                    'pct': pct,
                    'reason': 'Liquidation'
                })
                self.update_history_text()

    def update_history_text(self):
        """Обновить HTML-текст истории сделок в окне."""
        if not hasattr(self, 'history_textbox'):
            return
        if self.history_textbox is None:
            return
        if not self.order_history:
            try:
                self.history_textbox.set_text("No closed orders yet")
            except Exception:
                pass
            return
        rows = []
        rows.append('<b>Closed Orders</b><br><br>')
        for i, o in enumerate(self.order_history, 1):
            color = '#78c27d' if o['pnl'] >= 0 else '#e05757'
            rows.append(
                f"{i}. <b>{o['symbol']}</b> — <i>{o['reason']}</i><br>"
                f"&nbsp;&nbsp;Entry: {o['entry']:.2f}  Exit: {o['exit']:.2f}<br>"
                f"&nbsp;&nbsp;Lev: {int(o['leverage'])}x  Margin: ${o['margin']:.2f}<br>"
                f"&nbsp;&nbsp;<font color='{color}'>PnL: ${o['pnl']:.2f} ({o['pct']:+.2f}%)</font><br><br>"
            )
        try:
            self.history_textbox.set_text("")
            self.history_textbox.set_text("".join(rows))
        except Exception:
            pass

    def create_or_recreate_history_window(self):
        """Создать окно истории (если его нет или было закрыто)."""
        # Если окно существует и живо — ничего не делаем
        if getattr(self, 'history_window', None) is not None:
            try:
                if hasattr(self.history_window, 'alive') and self.history_window.alive():
                    return
            except Exception:
                pass
        # Создаём заново окно и текстбокс
        self.history_window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((WINDOW_WIDTH//2 - 280, WINDOW_HEIGHT//2 - 200), (560, 400)),
            manager=self.ui_manager,
            window_display_title='Order History',
            object_id="#history_window"
        )
        self.history_textbox = pygame_gui.elements.UITextBox(
            html_text="No closed orders yet",
            relative_rect=pygame.Rect((10, 30), (540, 360)),
            manager=self.ui_manager,
            container=self.history_window
        )
        self.update_history_text()

    def handle_events(self):
        for event in pygame.event.get():
            self.ui_manager.process_events(event)
            
            if event.type == pygame.QUIT:
                self.running = False
                
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.earn_button:
                    self.show_earn_screen()
                
                elif event.ui_element == self.trading_button:
                    self.show_trading_screen()
                
                elif event.ui_element == self.casino_button:
                    self.show_casino_screen()
                
                elif event.ui_element == self.back_button:
                    self.show_main_menu()
                
                elif event.ui_element == self.upgrade_button:
                    self.handle_upgrade_purchase()
                
                elif event.ui_element == self.auto_click_button:
                    self.handle_auto_click_purchase()
                
                # Выбор пары
                elif event.ui_element == self.trading_cookie_btn:
                    self.set_trading_symbol("COOKIEUSDT")
                elif event.ui_element == self.trading_pump_btn:
                    self.set_trading_symbol("PUMPUSDT")
                
                elif event.ui_element == self.trade_buy_button:
                    self.handle_trade_buy()
                elif event.ui_element == self.trade_sell_button:
                    self.handle_trade_sell()
                elif event.ui_element == self.history_button:
                    # Переключаем окно истории. Если окно было закрыто (kill), пересоздаём.
                    needs_create = (
                        self.history_window is None or
                        (hasattr(self.history_window, 'alive') and not self.history_window.alive())
                    )
                    if needs_create:
                        self.create_or_recreate_history_window()
                        self.history_window.show()
                    else:
                        if getattr(self.history_window, 'visible', False):
                            self.history_window.hide()
                        else:
                            self.update_history_text()
                            self.history_window.show()
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.current_state == GameState.EARN_SCREEN and self.mine_button_rect.collidepoint(event.pos):
                    self.handle_mine_click()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and self.current_state == GameState.EARN_SCREEN:
                    self.handle_mine_click()
                    self.handle_space_click()

    def handle_mine_click(self):
        """Обработка клика по круглой кнопке"""
        self.button_target_size = 180
        self.button_scale_time = self.button_scale_duration
        
        # Создаем эффект пульсации
        click_effect = {
            'position': self.mine_button_rect.center,
            'start_radius': self.button_current_size // 2,
            'current_radius': self.button_current_size // 2,
            'max_radius': self.button_current_size // 2 + 40,
            'duration': 0.6,
            'time_remaining': 0.6,
            'alpha': 200
        }
        self.click_effects.append(click_effect)
        
        # Начисляем деньги
        self.balance += self.click_value
        self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
        self.update_upgrade_button_text()
        self.update_auto_click_button_text()

    def handle_space_click(self):
        """Обработка клика пробелом (для скрытия подсказки)"""
        self.space_clicks_count += 1
        
        # Скрываем подсказку после достижения лимита кликов
        if self.space_clicks_count >= self.max_space_clicks_to_hide:
            self.space_hint.hide()

    def handle_upgrade_purchase(self):
        """Обработка покупки улучшения"""
        if self.current_upgrade_index >= len(self.upgrades):
            return
            
        upgrade = self.upgrades[self.current_upgrade_index]
        
        if self.balance >= upgrade.cost:
            # Покупка улучшения
            self.balance -= upgrade.cost
            self.click_value *= upgrade.multiplier
            upgrade.purchased = True
            
            # Обновляем UI
            self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
            self.click_value_label.set_text(f"Per click: ${self.click_value:.1f}")
            
            # Меняем изображение кнопки
            self.current_button_image = self.button_images[self.current_upgrade_index + 1]
            
            # Создаем эффект покупки улучшения
            upgrade_effect = {
                'position': self.mine_button_rect.center,
                'duration': 2.0,
                'time_remaining': 2.0,
                'text': f"UPGRADE! +{upgrade.multiplier}x"
            }
            self.upgrade_effects.append(upgrade_effect)
            
            # Переходим к следующему улучшению
            self.current_upgrade_index += 1
            self.update_upgrade_button_text()
            self.update_auto_click_button_text()
            
            print(f"Куплено улучшение! Новый доход: ${self.click_value:.1f} за клик")

    def handle_auto_click_purchase(self):
        """Обработка покупки автоклика"""
        if (self.balance >= self.auto_click_cost and 
            not self.auto_click_active and 
            self.auto_click_cooldown_timer <= 0):
            
            # Покупка автоклика
            self.balance -= self.auto_click_cost
            self.auto_click_active = True
            self.auto_click_duration = 10.0  # 10 секунд
            self.auto_click_timer = self.auto_click_duration
            self.auto_click_elapsed = 0
            self.auto_click_cooldown_timer = self.auto_click_cooldown  # Устанавливаем кулдаун
            
            # Обновляем UI
            self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
            self.update_auto_click_button_text()
            
            # Создаем эффект автоклика
            auto_click_effect = {
                'position': self.mine_button_rect.center,
                'duration': self.auto_click_duration,
                'time_remaining': self.auto_click_duration,
                'radius': 50
            }
            self.auto_click_effects.append(auto_click_effect)
            
            print(f"Активирован автоклик на {self.auto_click_duration} секунд!")

    def update(self, time_delta):
        self.ui_manager.update(time_delta)
        
        # Обновление анимации масштабирования кнопки
        if self.button_scale_time > 0:
            self.button_scale_time -= time_delta
            
            if self.button_scale_time <= 0:
                self.button_target_size = self.button_base_size
                self.button_scale_time = self.button_scale_duration
            else:
                progress = 1 - (self.button_scale_time / self.button_scale_duration)
                if self.button_target_size < self.button_base_size:
                    self.button_current_size = self.button_base_size - (self.button_base_size - self.button_target_size) * progress
                else:
                    self.button_current_size = self.button_target_size - (self.button_target_size - self.button_base_size) * (1 - progress)
        
        # Анимация монет — только в главном меню
        if self.current_state == GameState.MAIN_MENU:
            self.update_coins(time_delta)
        # Обновление графиков — в Trading обновляем сразу оба символа,
        # чтобы неактивный тоже продолжал рисовать курс
        if self.current_state == GameState.TRADING_SCREEN:
            for chart in self.charts.values():
                chart.update(time_delta)
            # проверяем ликвидации по всем позициям
            self.check_liquidations()
            # обновляем цену/информацию для активного символа
            self.update_trade_info()
            # Обновление кулдауна автоклика
        if self.auto_click_cooldown_timer > 0:
            self.auto_click_cooldown_timer -= time_delta
            if self.auto_click_cooldown_timer <= 0:
                self.auto_click_cooldown_timer = 0
                self.update_auto_click_button_text()
        
        # Обновление автоклика
        if self.auto_click_active:
            self.auto_click_timer -= time_delta
            self.auto_click_elapsed += time_delta
            
            # Обновляем таймер
            if self.auto_click_timer > 0:
                self.auto_click_timer_label.set_text(f"Auto Click: {self.auto_click_timer:.1f}s")
                
                # Автоклик каждые interval секунд
                if self.auto_click_elapsed >= self.auto_click_interval:
                    self.auto_click_elapsed = 0
                    self.handle_mine_click()  # Автоматический клик
            else:
                # Завершаем автоклик
                self.auto_click_active = False
                self.auto_click_timer_label.set_text("")
                self.update_auto_click_button_text()
        
        # Обновление эффектов пульсации
        for effect in self.click_effects[:]:
            effect['time_remaining'] -= time_delta
            if effect['time_remaining'] <= 0:
                self.click_effects.remove(effect)
            else:
                progress = 1 - (effect['time_remaining'] / effect['duration'])
                effect['current_radius'] = effect['start_radius'] + (
                    effect['max_radius'] - effect['start_radius']) * progress
                effect['alpha'] = int(200 * (1 - progress))
        
        # Обновление эффектов улучшения
        for effect in self.upgrade_effects[:]:
            effect['time_remaining'] -= time_delta
            if effect['time_remaining'] <= 0:
                self.upgrade_effects.remove(effect)
        
        # Обновление эффектов автоклика
        for effect in self.auto_click_effects[:]:
            effect['time_remaining'] -= time_delta
            if effect['time_remaining'] <= 0:
                self.auto_click_effects.remove(effect)

    def render_main_menu(self):
        """Отрисовка главного меню"""
        # Сначала фоновые монеты
        self.render_coins()

        # Затем заголовки
        title = self.font.render("Cryptonia", True, TEXT_COLOR)
        self.screen.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 150))
        
        subtitle = self.small_font.render("Выберите режим игры", True, TEXT_COLOR)
        self.screen.blit(subtitle, (WINDOW_WIDTH//2 - subtitle.get_width()//2, 200))

    def render_earn_screen(self):
        """Отрисовка экрана Earn"""
        info = self.small_font.render("Eaarnn!!!", True, TEXT_COLOR)
        self.screen.blit(info, (WINDOW_WIDTH//2 - info.get_width()//2, 180))
        
        # Масштабируем кнопку
        scaled_button = pygame.transform.scale(
            self.current_button_image, 
            (int(self.button_current_size), int(self.button_current_size))
        )
        button_rect = scaled_button.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 50))
        
        # Отрисовываем эффекты пульсации
        for effect in self.click_effects:
            effect_surface = pygame.Surface((effect['current_radius'] * 2, effect['current_radius'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                effect_surface, 
                (255, 255, 255, effect['alpha']),
                (effect['current_radius'], effect['current_radius']), 
                effect['current_radius'], 
                3
            )
            effect_rect = effect_surface.get_rect(center=effect['position'])
            self.screen.blit(effect_surface, effect_rect)
        
        # Отрисовываем эффекты автоклика
        for effect in self.auto_click_effects:
            if effect['time_remaining'] > 0:
                progress = 1 - (effect['time_remaining'] / effect['duration'])
                alpha = int(100 * (1 - progress))
                radius = int(effect['radius'] * (1 + progress * 0.5))
                
                effect_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    effect_surface, 
                    (0, 255, 255, alpha),  # Голубой цвет для автоклика
                    (radius, radius), 
                    radius, 
                    3
                )
                effect_rect = effect_surface.get_rect(center=effect['position'])
                self.screen.blit(effect_surface, effect_rect)
        
        # Отрисовываем кнопку
        self.screen.blit(scaled_button, button_rect)
        self.mine_button_rect = button_rect
        
        # Отрисовываем эффекты улучшения
        for effect in self.upgrade_effects:
            progress = 1 - (effect['time_remaining'] / effect['duration'])
            alpha = int(255 * min(1.0, progress * 2))
            size = int(30 + progress * 20)
            
            font = pygame.font.Font(None, size)
            text = font.render(effect['text'], True, (255, 215, 0, alpha))
            text.set_alpha(alpha)
            
            text_rect = text.get_rect(center=(effect['position'][0], effect['position'][1] - 100 - progress * 50))
            self.screen.blit(text, text_rect)
        
        # Подсветка при наведении
        mouse_pos = pygame.mouse.get_pos()
        if self.mine_button_rect.collidepoint(mouse_pos):
            pygame.draw.circle(
                self.screen, 
                (255, 255, 255, 100), 
                self.mine_button_rect.center, 
                self.button_current_size // 2.145 + 2, 
                3
            )

    def render_casino_screen(self):
        """Отрисовка экрана Casino"""
        coming_soon = self.font.render("Coming Soon!", True, (255, 215, 0))
        self.screen.blit(coming_soon, (WINDOW_WIDTH//2 - coming_soon.get_width()//2, 280))

    def render_trading_screen(self):
        """Отрисовка экрана Trading"""
        # подпись осей/подсказка
        hint = self.small_font.render("Chart", True, TEXT_COLOR)
        self.screen.blit(hint, (60, 120))
        # график
        self.trading_chart.draw(self.screen)

        # Правый ценовой скейл: показываем только текущую, минимум и максимум цены (по данным)
        if self.trading_chart.data:
            current = self.trading_chart.data[-1]
            data_min = min(self.trading_chart.data)
            data_max = max(self.trading_chart.data)
            cr = self.trading_chart.rect
            y_min = self.trading_chart.y_min
            y_max = self.trading_chart.y_max
            rng = max(1e-6, y_max - y_min)

            # Область для шкалы справа от графика
            scale_left = cr.right + 8
            scale_right = scale_left + 38
            # Рисуем рамку шкалы
            pygame.draw.rect(self.screen, (70, 70, 90), pygame.Rect(scale_left - 4, cr.top, (scale_right - scale_left) + 8, cr.height), 1)

            def price_to_y(p):
                p_clamped = max(y_min, min(y_max, p))
                norm = (p_clamped - y_min) / rng
                return int(cr.bottom - norm * cr.height)

            levels = [
                (price_to_y(data_max), 'max', data_max, (120, 200, 120)),
                (price_to_y(current), 'cur', current, (255, 215, 0)),
                (price_to_y(data_min), 'min', data_min, (200, 120, 120)),
            ]

            font = pygame.font.Font(None, 22)
            for y, tag, price, color in levels:
                if y < cr.top or y > cr.bottom:
                    continue
                # короткая линия-тик
                pygame.draw.line(self.screen, color, (cr.right - 6, y), (scale_left, y), 1)
                # подпись
                label = f"{price:.2f}"
                text = font.render(label, True, color)
                self.screen.blit(text, (scale_left + 2, y - text.get_height() // 2))

        # Панель информации о позиции под графиком (кастомный стиль)
        cr = self.trading_chart.rect
        panel_margin_top = 6
        panel_h = 90
        panel_rect = pygame.Rect(cr.left, min(cr.bottom + panel_margin_top, WINDOW_HEIGHT - panel_h - 10), cr.width, panel_h)
        # фон панели с альфой
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((25, 25, 35, 200))
        # рамка
        pygame.draw.rect(panel_surf, (80, 80, 120), pygame.Rect(0, 0, panel_rect.width, panel_rect.height), 1)
        # заголовок
        title_font = pygame.font.Font(None, 24)
        title = title_font.render(f"Position — {self.trading_symbol}", True, (180, 200, 255))
        panel_surf.blit(title, (12, 8))
        # содержимое
        content_font = pygame.font.Font(None, 22)
        lines = self.trade_info_text.split('\n') if self.trade_info_text else ["No position"]
        # вычислить цвет PnL/статуса
        pnl_color = (200, 200, 200)
        is_liq = any("Liquidation!" in l for l in lines)
        if is_liq:
            pnl_color = (220, 80, 80)
            lines = ["Liquidation!"]
        elif any(l.startswith("PnL:") for l in lines):
            for l in lines:
                if l.startswith("PnL:"):
                    pnl_color = (120, 200, 120) if ("+" in l and "-" not in l) else ((200, 120, 120) if "-" in l else (200, 200, 200))
                    break
        yoff = 30
        for l in lines:
            color = pnl_color if l.startswith("PnL:") else (220, 220, 230)
            if is_liq:
                color = pnl_color
            txt = content_font.render(l, True, color)
            panel_surf.blit(txt, (12, yoff))
            yoff += 22
        # рисуем панель на экран
        self.screen.blit(panel_surf, panel_rect)

    def render(self):
        self.screen.fill(BACKGROUND_COLOR)
        
        if self.current_state == GameState.MAIN_MENU:
            self.render_main_menu()
        elif self.current_state == GameState.EARN_SCREEN:
            self.render_earn_screen()
        elif self.current_state == GameState.CASINO_SCREEN:
            self.render_casino_screen()
        elif self.current_state == GameState.TRADING_SCREEN:
            self.render_trading_screen()
        
        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def run(self):
        self.show_main_menu()
        
        while self.running:
            time_delta = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(time_delta)
            self.render()
        
        pygame.quit()

if __name__ == "__main__":
    game = CryptoClicker()
    game.run()