import os
import sys
import json
import math
import random
import csv
import pygame
import pygame_gui
from pygame_gui.windows import UIFileDialog
from config import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, BACKGROUND_COLOR, TEXT_COLOR, CRYPTO_GREEN
from trading import LineChart

class GameState:
    MAIN_MENU = "main_menu" 
    EARN_SCREEN = "earn_screen"
    TRADING_SCREEN = "trading_screen"
    CASINO_SCREEN = "casino_screen"
    CRASH_SCREEN = "crash_screen"

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


        # Инициализация музыки
        self.setup_music()

        # Создание главного окна
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Cryptonia")
        # Инициализация буфера обмена для корректной работы вставки в полях ввода
        try:
            pygame.scrap.init()
            try:
                pygame.scrap.set_mode(pygame.SCRAP_CLIPBOARD)
            except Exception:
                pass
            # pygame_gui ожидает наличие методов get_text/put_text у pygame.scrap
            if not hasattr(pygame.scrap, 'get_text'):
                def _scrap_get_text():
                    try:
                        data = None
                        try:
                            data = pygame.scrap.get(pygame.SCRAP_TEXT)
                        except Exception:
                            pass
                        if data is None:
                            try:
                                data = pygame.scrap.get('text/plain')
                            except Exception:
                                pass
                        if data is None:
                            # Попробуем через pyperclip, если установлен
                            try:
                                import pyperclip  # type: ignore
                                return pyperclip.paste() or ''
                            except Exception:
                                return ''
                        if isinstance(data, (bytes, bytearray)):
                            try:
                                return data.decode('utf-8')
                            except Exception:
                                try:
                                    return data.decode('cp1251')
                                except Exception:
                                    return data.decode(errors='ignore')
                        return str(data)
                    except Exception:
                        try:
                            import pyperclip  # type: ignore
                            return pyperclip.paste() or ''
                        except Exception:
                            return ''
                pygame.scrap.get_text = _scrap_get_text  # type: ignore[attr-defined]
            if not hasattr(pygame.scrap, 'put_text'):
                def _scrap_put_text(text):
                    try:
                        if not isinstance(text, (str, bytes, bytearray)):
                            text = str(text)
                        data_bytes = text.encode('utf-8') if isinstance(text, str) else bytes(text)
                    except Exception:
                        return
                    try:
                        if hasattr(pygame.scrap, 'put'):
                            pygame.scrap.put(pygame.SCRAP_TEXT, data_bytes)
                            return
                    except Exception:
                        pass
                    # Фолбэк через pyperclip, если доступен
                    try:
                        import pyperclip  # type: ignore
                        if isinstance(text, (bytes, bytearray)):
                            try:
                                text = text.decode('utf-8')
                            except Exception:
                                text = text.decode(errors='ignore')
                        pyperclip.copy(text)
                    except Exception:
                        pass
                pygame.scrap.put_text = _scrap_put_text  # type: ignore[attr-defined]
        except Exception:
            pass
        
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
        self.auto_click_interval = 0.02  # автоклик немного медленнее
        self.auto_click_elapsed = 0
        self.auto_click_cost = 150  # стоимость автоклика (в 2 раза дешевле)
        self.auto_click_cooldown = 120  # 2 минуты в секундах
        self.auto_click_cooldown_timer = 0  # таймер кулдауна
        
        # Счетчик кликов пробелом для скрытия подсказки
        self.space_clicks_count = 0
        self.max_space_clicks_to_hide = 2
        
        # Список улучшений
        self.upgrades = [
            Upgrade(250, 1.5, "mine_button_upgrade1.png"),
            Upgrade(500, 2.5, "mine_button_upgrade2.png"),
            Upgrade(1000, 5.0, "mine_button_upgrade3.png")
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
        
        self.toast_messages = []
        
        # Crash screen multiplier animation
        self.crash_multiplier = 1.01
        self.crash_multiplier_speed = 0.001
        self.crash_multiplier_acceleration = 1.02
        self.crash_multiplier_active = False
        self.crash_max_stop_time = random.uniform(3.0, 8.0)
        self.crash_current_time = 0.0
        
        # Creating UI elements
        self.create_main_menu()
        self.create_earn_screen()
        self.create_casino_screen()
        self.create_trading_screen()
        # Загрузка сохранения перед показом меню
        try:
            self.load_game()
        except Exception:
            pass
        # Показать главное меню при старте
        self.show_main_menu()


    
    def load_button_images(self):
        """Загрузка всех изображений кнопок"""
        images = []
        
        # Базовое изображение
        images.append(self.load_single_button_image("mine_button.png", "Базовое"))
        
        # Изображения улучшений
        for i, upgrade in enumerate(self.upgrades):
            images.append(self.load_single_button_image(upgrade.image_name, f"Улучшение {i+1}"))
        
        return images

    def setup_music(self):
        """Инициализация и запуск фоновой музыки из папки music"""
        try:
            pygame.mixer.init()
            # Загружаем музыку из папки music
            script_dir = os.path.dirname(os.path.abspath(__file__))
            music_dir = os.path.join(script_dir, "music")
            
            if os.path.exists(music_dir):
                # Получаем все mp3 файлы из папки music
                music_files = [f for f in os.listdir(music_dir) if f.lower().endswith('.mp3')]
                
                if music_files:
                    # Создаем плейлист из всех найденных треков
                    playlist = []
                    for music_file in music_files:
                        music_path = os.path.join(music_dir, music_file)
                        playlist.append(music_path)
                    
                    # Загружаем и запускаем первый трек
                    pygame.mixer.music.load(playlist[0])
                    pygame.mixer.music.set_volume(0.1)
                    pygame.mixer.music.play()
                    
                    # Сохраняем плейлист для переключения треков
                    self.music_playlist = playlist
                    self.current_track_index = 0
                    
                    print(f"Загружено треков: {len(playlist)}")
                    print(f"Сейчас играет: {music_files[0]}")
                    
                    # Устанавливаем обработчик окончания трека
                    pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
                else:
                    print("В папке music не найдено mp3 файлов")
            else:
                print(f"Папка music не найдена: {music_dir}")
                
        except Exception as e:
            print(f"Ошибка загрузки музыки: {e}")

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
        
        # Кнопка Crash
        self.crash_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 150, 490), (300, 60)),  
            text="Crash",
            manager=self.ui_manager
        )
        
        # Скрываем кнопки изначально
        # Кнопка Withdraw (слева снизу)
        self.withdraw_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((40, WINDOW_HEIGHT - 80), (160, 50)),
            text="Withdraw",
            manager=self.ui_manager
        )
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
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 100, 120), (200, 50)),
            text="",
            manager=self.ui_manager
        )
        
        # Информация о казино
        self.casino_info = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 200, 180), (400, 80)),
            text="",
            manager=self.ui_manager
        )
        # Roulette UI
        # Правая панель (sidebar) для крупных контролов
        sidebar_w = 280
        sidebar_x = WINDOW_WIDTH - sidebar_w - 40
        # Заголовок рулетки
        self.roulette_title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((sidebar_x, 140), (sidebar_w, 40)),
            text="Roulette (18 Red, 18 Black, 1 Zero)",
            manager=self.ui_manager
        )
        # Ввод суммы ставки (крупнее)
        self.roulette_bet_amount_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((sidebar_x, 188), (sidebar_w, 30)),
            text="Bet Amount ($)",
            manager=self.ui_manager
        )
        self.roulette_bet_amount_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((sidebar_x, 222), (sidebar_w, 40)),
            manager=self.ui_manager
        )
        self.roulette_bet_amount_input.set_text("10")
        # Кнопки выбора ставки (большие вертикальные)
        btn_h = 52
        gap = 12
        self.roulette_bet_red_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((sidebar_x, 274), (sidebar_w, btn_h)),
            text="Bet Red",
            manager=self.ui_manager
        )
        self.roulette_bet_black_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((sidebar_x, 274 + (btn_h + gap)), (sidebar_w, btn_h)),
            text="Bet Black",
            manager=self.ui_manager
        )
        self.roulette_bet_zero_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((sidebar_x, 274 + 2 * (btn_h + gap)), (sidebar_w, btn_h)),
            text="Bet Zero",
            manager=self.ui_manager
        )
        # Кнопка спина (ещё крупнее)
        self.roulette_spin_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((sidebar_x, 274 + 3 * (btn_h + gap) + 10), (sidebar_w, btn_h + 6)),
            text="Spin",
            manager=self.ui_manager
        )
        # Результат
        self.roulette_result_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((sidebar_x, 274 + 4 * (btn_h + gap) + 22), (sidebar_w, 80)),
            text="",
            manager=self.ui_manager
        )
        # Стили кнопок под казино (яркие цвета)
        try:
            # Bet Red
            self.roulette_bet_red_btn.colours['normal_bg'] = pygame.Color(220, 35, 35)
            self.roulette_bet_red_btn.colours['hovered_bg'] = pygame.Color(240, 60, 60)
            self.roulette_bet_red_btn.colours['active_bg'] = pygame.Color(180, 30, 30)
            self.roulette_bet_red_btn.colours['normal_text'] = pygame.Color(255, 255, 255)
            self.roulette_bet_red_btn.colours['hovered_text'] = pygame.Color(255, 255, 255)
            self.roulette_bet_red_btn.colours['active_text'] = pygame.Color(255, 255, 255)
            self.roulette_bet_red_btn.rebuild()

            # Bet Black
            self.roulette_bet_black_btn.colours['normal_bg'] = pygame.Color(24, 24, 28)
            self.roulette_bet_black_btn.colours['hovered_bg'] = pygame.Color(48, 48, 54)
            self.roulette_bet_black_btn.colours['active_bg'] = pygame.Color(16, 16, 20)
            self.roulette_bet_black_btn.colours['normal_text'] = pygame.Color(255, 255, 255)
            self.roulette_bet_black_btn.colours['hovered_text'] = pygame.Color(255, 255, 255)
            self.roulette_bet_black_btn.colours['active_text'] = pygame.Color(255, 255, 255)
            self.roulette_bet_black_btn.rebuild()

            # Bet Zero (зелёная)
            self.roulette_bet_zero_btn.colours['normal_bg'] = pygame.Color(0, 160, 60)
            self.roulette_bet_zero_btn.colours['hovered_bg'] = pygame.Color(0, 190, 70)
            self.roulette_bet_zero_btn.colours['active_bg'] = pygame.Color(0, 130, 50)
            self.roulette_bet_zero_btn.colours['normal_text'] = pygame.Color(255, 255, 255)
            self.roulette_bet_zero_btn.colours['hovered_text'] = pygame.Color(255, 255, 255)
            self.roulette_bet_zero_btn.colours['active_text'] = pygame.Color(255, 255, 255)
            self.roulette_bet_zero_btn.rebuild()

            # Spin (золотая)
            self.roulette_spin_btn.colours['normal_bg'] = pygame.Color(255, 215, 0)
            self.roulette_spin_btn.colours['hovered_bg'] = pygame.Color(255, 232, 80)
            self.roulette_spin_btn.colours['active_bg'] = pygame.Color(220, 180, 0)
            self.roulette_spin_btn.colours['normal_text'] = pygame.Color(25, 25, 25)
            self.roulette_spin_btn.colours['hovered_text'] = pygame.Color(25, 25, 25)
            self.roulette_spin_btn.colours['active_text'] = pygame.Color(0, 0, 0)
            self.roulette_spin_btn.rebuild()
        except Exception:
            pass
        # Текущее выбранное пари: 'red' | 'black' | 'zero' | None
        self.roulette_current_bet = None
        # Параметры колеса рулетки
        # Рассчитываем радиус и центр: чуть меньше и ближе к центру, но не задевая сайдбар
        left_margin = 60
        padding = 20
        # максимальный радиус по ширине (до левого края сайдбара)
        max_r_w = max(80, (sidebar_x - left_margin - padding) // 2)
        # максимальный радиус по высоте (в пределах окна)
        max_r_h = max(80, WINDOW_HEIGHT // 2 - 80)
        # Чуть уменьшим для визуального баланса
        base_r = min(220, max_r_w, max_r_h)
        big_r = max(90, int(base_r) - 15)
        self.roulette_radius = int(big_r)
        # Центр: сдвигаем вправо к центру, но держим зазор до сайдбара
        gap_sidebar = 24
        center_x_min = left_margin + self.roulette_radius + padding
        center_x_max = sidebar_x - gap_sidebar - self.roulette_radius
        target_center_x = WINDOW_WIDTH // 2 - 80
        center_x = max(center_x_min, min(center_x_max, target_center_x))
        self.roulette_center = (center_x, 360)
        # Список 37 секторов: 1 зелёный ZERO + 18 красных + 18 чёрных
        self.roulette_sectors = ['zero'] + [c for pair in [('red','black')] * 18 for c in pair][:36]
        # Физика вращения
        self.roulette_angle = 0.0  # текущий угол (рад), 0 — на "12 часов"
        # Новая анимация: интерполяция угла от start к end по easing без рывков
        self.roulette_spin_anim = False
        self.roulette_spin_t = 0.0
        self.roulette_spin_T = 0.0
        self.roulette_start_angle = 0.0
        self.roulette_end_angle = 0.0
        self.roulette_target_outcome = None
        self.roulette_target_index = 0
        # Множественные ставки: red/black/zero
        self.roulette_bets = {'red': 0.0, 'black': 0.0, 'zero': 0.0}
        self.roulette_pending_bets = None
        # Анимация выигрыша
        self.roulette_win_anim_active = False
        self.roulette_win_anim_t = 0.0
        self.roulette_win_anim_T = 1.2
        self.roulette_win_particles = []  # список частиц {x,y,vx,vy,life,size,color}
        self.roulette_win_amount = 0.0
        
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
        self.chart_sample_interval = 0.28
        # Создаём отдельные графики для каждой пары (больше истории для перемотки)
        cookie_chart = LineChart(chart_rect, max_points=2000, y_min=28.0, y_max=52.0)
        cookie_chart.sample_interval = self.chart_sample_interval
        # Усиливаем волатильность и делаем линию толще
        cookie_chart.step_min = -9.0
        cookie_chart.step_max = 9.0
        cookie_chart.inertia = 0.68
        cookie_chart.mid_pull = 0.015
        cookie_chart.line_color = pygame.Color(*CRYPTO_GREEN)
        cookie_chart.line_width = 3
        # Показываем на экране не всю историю, а окно, чтобы была возможность листать
        try:
            cookie_chart.set_display_points(280)
        except Exception:
            pass
        cookie_chart.last_value = 40.0
        for _ in range(8):
            cookie_chart.push_value(cookie_chart.last_value)
        # Предзаполняем историю, чтобы можно было сразу листать назад
        try:
            for _ in range(800):
                step = random.uniform(cookie_chart.step_min, cookie_chart.step_max)
                inertia = cookie_chart.inertia
                new_val = cookie_chart.last_value * inertia + (cookie_chart.last_value + step) * (1 - inertia)
                mid = (cookie_chart.y_min + cookie_chart.y_max) / 2
                new_val = new_val * (1 - cookie_chart.mid_pull) + mid * cookie_chart.mid_pull
                cookie_chart.push_value(new_val)
        except Exception:
            pass

        pump_chart = LineChart(chart_rect, max_points=2000, y_min=100.0, y_max=320.0)
        pump_chart.sample_interval = self.chart_sample_interval  # одинаковая скорость вправо
        # Усиливаем волатильность и делаем линию толще
        pump_chart.step_min = -60.0
        pump_chart.step_max = 60.0
        pump_chart.inertia = 0.28
        pump_chart.mid_pull = 0.0015
        pump_chart.line_color = pygame.Color(*CRYPTO_GREEN)
        pump_chart.line_width = 3
        # Не допускаем отрицательные значения цены на PUMP
        try:
            pump_chart.min_floor = 0.01
        except Exception:
            pass
        try:
            pump_chart.set_display_points(280)
        except Exception:
            pass
        pump_chart.last_value = 100.0
        for _ in range(8):
            pump_chart.push_value(pump_chart.last_value)
        try:
            for _ in range(800):
                step = random.uniform(pump_chart.step_min, pump_chart.step_max)
                inertia = pump_chart.inertia
                new_val = pump_chart.last_value * inertia + (pump_chart.last_value + step) * (1 - inertia)
                mid = (pump_chart.y_min + pump_chart.y_max) / 2
                new_val = new_val * (1 - pump_chart.mid_pull) + mid * pump_chart.mid_pull
                pump_chart.push_value(new_val)
        except Exception:
            pass

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

        # Направление сделки (Long/Short)
        self.trade_direction_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((panel_left, controls_top + 116), (right_panel_w, 24)),
            text="Direction",
            manager=self.ui_manager
        )
        self.trade_direction_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=["Long", "Short"],
            starting_option="Long",
            relative_rect=pygame.Rect((panel_left, controls_top + 140), (right_panel_w, 28)),
            manager=self.ui_manager
        )

        self.trade_buy_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((panel_left, controls_top + 176), (right_panel_w, 36)),
            text="Buy",
            manager=self.ui_manager
        )
        self.trade_sell_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((panel_left, controls_top + 218), (right_panel_w, 36)),
            text="Sell",
            manager=self.ui_manager
        )

        # Информация по позиции
        self.trade_info_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((panel_left, controls_top + 260), (right_panel_w, 120)),
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
        self.history_save_btn = None
        self.history_save_dialog = None

        # Текущий актив по умолчанию
        self.trading_symbol = "COOKIEUSDT"
        self.trading_chart = self.charts[self.trading_symbol]

        # Маркеры сделок для отрисовки на графике
        self.trade_markers = {"COOKIEUSDT": [], "PUMPUSDT": []}

        # Состояние для перетаскивания (панорамирования) графика
        self.is_panning_chart = False
        self.pan_last_x = 0
        self.pan_accum_points = 0.0

        self.hide_trading_screen()

    def hide_main_menu(self):
        """Скрыть элементы главного меню"""
        self.earn_button.hide()
        self.trading_button.hide()
        self.casino_button.hide()
        self.crash_button.hide()
        if hasattr(self, 'withdraw_button'): self.withdraw_button.hide()

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
        # Roulette UI hide
        if hasattr(self, 'roulette_title'):
            self.roulette_title.hide()
        if hasattr(self, 'roulette_bet_amount_label'):
            self.roulette_bet_amount_label.hide()
        if hasattr(self, 'roulette_bet_amount_input'):
            self.roulette_bet_amount_input.hide()
        if hasattr(self, 'roulette_bet_red_btn'):
            self.roulette_bet_red_btn.hide()
        if hasattr(self, 'roulette_bet_black_btn'):
            self.roulette_bet_black_btn.hide()
        if hasattr(self, 'roulette_bet_zero_btn'):
            self.roulette_bet_zero_btn.hide()
        if hasattr(self, 'roulette_spin_btn'):
            self.roulette_spin_btn.hide()
        if hasattr(self, 'roulette_result_label'):
            self.roulette_result_label.hide()

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
        if hasattr(self, 'trade_direction_label'):
            self.trade_direction_label.hide()
        if hasattr(self, 'trade_direction_dropdown'):
            self.trade_direction_dropdown.hide()
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
        self.crash_button.show()
        if hasattr(self, 'withdraw_button'): self.withdraw_button.show()
        
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

        # Обновим тексты кнопок сразу при входе, чтобы отразить текущий кулдаун/стоимость
        self.update_upgrade_button_text()
        self.update_auto_click_button_text()

    def show_casino_screen(self):
        """Показать экран Casino"""
        self.hide_main_menu()
        self.hide_earn_screen()
        self.hide_trading_screen()
        
        self.back_button.show()
        self.balance_label.show()
        self.casino_title.show()
        self.casino_info.show()
        # Roulette UI show
        self.roulette_title.show()
        self.roulette_bet_amount_label.show()
        self.roulette_bet_amount_input.show()
        self.roulette_bet_red_btn.show()
        self.roulette_bet_black_btn.show()
        self.roulette_bet_zero_btn.show()
        self.roulette_spin_btn.show()
        self.roulette_result_label.show()
        
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
        self.trade_direction_label.show()
        self.trade_direction_dropdown.show()
        self.trade_buy_button.show()
        self.trade_sell_button.show()
        # Информацию о позиции рисуем кастомно под графиком
        self.history_button.show()

        self.current_state = GameState.TRADING_SCREEN

    def show_crash_screen(self):
        """Показать экран Crash с квадратом слева"""
        self.hide_main_menu()
        self.hide_earn_screen()
        self.hide_casino_screen()
        self.hide_trading_screen()
        
        # Reset and start multiplier
        self.crash_multiplier = 1.01
        self.crash_multiplier_speed = 0.001
        self.crash_multiplier_active = True
        self.crash_max_stop_time = random.uniform(3.0, 8.0)
        self.crash_current_time = 0.0
        
        self.current_state = GameState.CRASH_SCREEN

    def render_crash_screen(self):
        """Отрисовка экрана Crash с квадратом слева"""
        # Заполняем фон красным цветом (эффект краша)
        self.screen.fill((220, 20, 60))
        
        # Рисуем квадрат слева
        square_size = 200
        square_x = 50
        square_y = (WINDOW_HEIGHT - square_size) // 2
        pygame.draw.rect(self.screen, (255, 255, 255), (square_x, square_y, square_size, square_size))
        
        # Draw multiplier in center of square (black color)
        if self.crash_multiplier_active:
            multiplier_text = f"{self.crash_multiplier:.2f}x"
        else:
            multiplier_text = "1.00x"
        
        multiplier_font = pygame.font.Font(None, 48)
        multiplier_surface = multiplier_font.render(multiplier_text, True, (0, 0, 0))
        multiplier_rect = multiplier_surface.get_rect(center=(square_x + square_size//2, square_y + square_size//2))
        self.screen.blit(multiplier_surface, multiplier_rect)
        
        # Добавляем текст "CRASH" в центре
        crash_font = pygame.font.Font(None, 54)
        crash_text = crash_font.render("CRASH", True, (255, 255, 255))
        crash_rect = crash_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//10s))
        self.screen.blit(crash_text, crash_rect)
        
        # Добавляем подсказку для возврата
        hint_font = pygame.font.Font(None, 36)
        hint_text = hint_font.render("", True, (255, 255, 255))
        hint_rect = hint_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 60))
        self.screen.blit(hint_text, hint_rect)

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

    def parse_direction(self) -> str:
        try:
            opt = self.trade_direction_dropdown.selected_option
            return 'short' if opt.lower() == 'short' else 'long'
        except Exception:
            return 'long'

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
        side = self.parse_direction()
        pos = self.positions.get(self.trading_symbol)
        if pos is None:
            pos = {
                'margin': 0.0,
                'entry_price': 0.0,
                'leverage': leverage,
                'liqяuidated': False,
                'side': side
            }
        # Если уже есть позиция и другое плечо — используем текущее плечо позиции
        if pos['margin'] > 0 and pos['leverage'] != leverage:
            leverage = pos['leverage']
            # синхронизируем дропдаун
            self.trade_leverage_dropdown.selected_option = f"{leverage}x"
            self.trade_leverage_dropdown.rebuild()
        # Если уже есть позиция другого направления — закроем её по рынку и откроем новую
        if pos.get('margin', 0.0) > 0 and pos.get('side', 'long') != side:
            old_side = pos.get('side', 'long')
            entry = pos['entry_price']
            margin = pos['margin']
            lev = pos['leverage']
            if old_side == 'long':
                pnl_old = margin * lev * ((price / entry) - 1.0)
            else:
                pnl_old = margin * lev * ((entry / price) - 1.0)
            # Cap realized PnL to ± notional to avoid unrealistic spikes
            cap = margin * lev
            pnl_old = max(-cap, min(cap, pnl_old))
            self.balance += (margin + pnl_old)
            pct_old = (((price / entry) - 1.0) if old_side == 'long' else ((entry / price) - 1.0)) * 100.0 * lev if entry > 0 else 0.0
            self.order_history.append({
                'symbol': self.trading_symbol,
                'entry': entry,
                'exit': price,
                'margin': margin,
                'leverage': lev,
                'side': old_side,
                'pnl': pnl_old,
                'pct': pct_old,
                'reason': 'Closed'
            })
            self.update_history_text()
            # Маркер закрытия: для закрытия шорта — 'B' (зелёная), для лонга — 'S' (красная)
            try:
                chart = self.charts[self.trading_symbol]
                close_type = 'B' if old_side == 'short' else 'S'
                self.trade_markers[self.trading_symbol].append({'abs': chart.abs_index, 'price': price, 'type': close_type})
            except Exception:
                pass
            pos['margin'] = 0.0
            pos['entry_price'] = 0.0
            pos['liquidated'] = False
            pos['side'] = side
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
        pos['side'] = side
        # При открытии/доливке позиции статус ликвидации снимаем
        pos['liquidated'] = False
        self.positions[self.trading_symbol] = pos
        # списываем маржу
        self.balance -= amount
        self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
        self.update_trade_info()
        # Маркер покупки: для открытия шорта — 'S' (красная), для лонга — 'B' (зелёная)
        try:
            chart = self.charts[self.trading_symbol]
            open_type = 'S' if side == 'short' else 'B'
            self.trade_markers[self.trading_symbol].append({'abs': chart.abs_index, 'price': price, 'type': open_type})
        except Exception:
            pass

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
        side = self.positions[self.trading_symbol].get('side', 'long')
        if side == 'long':
            pnl = margin * leverage * ((price / entry) - 1.0)
            pct = ((price / entry) - 1.0) * 100.0 * leverage if entry > 0 else 0.0
        else:
            pnl = margin * leverage * ((entry / price) - 1.0)
            pct = ((entry / price) - 1.0) * 100.0 * leverage if entry > 0 else 0.0
        # Cap realized PnL to ± notional
        cap = margin * leverage
        pnl = max(-cap, min(cap, pnl))
        # Возвращаем маржу + PnL
        self.balance += (margin + pnl)
        self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
        # Сохраняем в историю
        self.order_history.append({
            'symbol': self.trading_symbol,
            'entry': entry,
            'exit': price,
            'margin': margin,
            'leverage': leverage,
            'side': side,
            'pnl': pnl,
            'pct': pct,
            'reason': 'Closed'
        })
        self.update_history_text()
        # Маркер продажи: для закрытия шорта — 'B' (зелёная), для лонга — 'S' (красная)
        try:
            chart = self.charts[self.trading_symbol]
            close_type = 'B' if side == 'short' else 'S'
            self.trade_markers[self.trading_symbol].append({'abs': chart.abs_index, 'price': price, 'type': close_type})
        except Exception:
            pass
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
            side = pos.get('side', 'long')
            if side == 'long':
                pct = ((price / entry) - 1.0) * 100.0 * leverage
                pnl = margin * leverage * ((price / entry) - 1.0)
            else:
                pct = ((entry / price) - 1.0) * 100.0 * leverage
                pnl = margin * leverage * ((entry / price) - 1.0)
            # Cap unrealized PnL in display to ± notional for sanity
            cap = margin * leverage
            pnl = max(-cap, min(cap, pnl))
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
            side = pos.get('side', 'long')
            if side == 'long':
                pnl = margin * leverage * ((price / entry) - 1.0)
                pct = ((price / entry) - 1.0) * 100.0 * leverage if entry > 0 else 0.0
            else:
                pnl = margin * leverage * ((entry / price) - 1.0)
                pct = ((entry / price) - 1.0) * 100.0 * leverage if entry > 0 else 0.0
            equity = margin + pnl
            if equity <= 0:
                # Ликвидация: полностью теряем маржу, позиция закрывается
                pos['margin'] = 0.0
                pos['liquidated'] = True
                self.positions[symbol] = pos
                # Запишем в историю
                self.order_history.append({
                    'symbol': symbol,
                    'entry': entry,
                    'exit': price,
                    'margin': margin,
                    'leverage': leverage,
                    'side': side,
                    'pnl': -margin,  # потеря всей маржи
                    'pct': pct,
                    'reason': 'Liquidation'
                })
                self.update_history_text()
                # Маркер ликвидации как продажа: для шорта — 'B', для лонга — 'S'
                try:
                    chart = self.charts[symbol]
                    close_type = 'B' if side == 'short' else 'S'
                    self.trade_markers[symbol].append({'abs': chart.abs_index, 'price': price, 'type': close_type})
                except Exception:
                    pass

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
            side_txt = (o.get('side', 'long')).upper()
            rows.append(
                f"{i}. <b>{o['symbol']}</b> — <i>{o['reason']}</i> — <b>{side_txt}</b><br>"
                f"&nbsp;&nbsp;Entry: {o['entry']:.2f}  Exit: {o['exit']:.2f}<br>"
                f"&nbsp;&nbsp;Lev: {int(o['leverage'])}x  Margin: ${o['margin']:.2f}<br>"
                f"&nbsp;&nbsp;<font color='{color}'>PnL: ${o['pnl']:.2f} ({o['pct']:+.2f}%)</font><br><br>"
            )
        try:
            self.history_textbox.set_text("")
            self.history_textbox.set_text("".join(rows))
        except Exception:
            pass

    def export_history_to_csv(self, file_path: str):
        """Экспорт истории закрытых сделок в CSV."""
        try:
            # Гарантируем существование директории
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        except Exception:
            # Если директорию создать нельзя (например, сохранение в корень), игнорируем
            pass
        try:
            # Используем UTF-8 BOM и точку с запятой как разделитель — так файлы корректно открываются в Excel (RU)
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([
                    'symbol', 'side', 'entry', 'exit', 'margin', 'leverage', 'pnl', 'pct', 'reason'
                ])
                for o in self.order_history:
                    writer.writerow([
                        o.get('symbol', ''),
                        (o.get('side', 'long')).upper(),
                        f"{o.get('entry', 0.0):.6f}",
                        f"{o.get('exit', 0.0):.6f}",
                        f"{o.get('margin', 0.0):.6f}",
                        int(o.get('leverage', 1)),
                        f"{o.get('pnl', 0.0):.6f}",
                        f"{o.get('pct', 0.0):.6f}",
                        o.get('reason', '')
                    ])
            # Небольшая обратная связь через текстбокс, если открыт
            try:
                if self.history_textbox is not None:
                    self.history_textbox.append_html_text(f"<br><i>Saved to: {file_path}</i>")
            except Exception:
                pass
        except Exception as e:
            # Сообщение об ошибке
            try:
                if self.history_textbox is not None:
                    self.history_textbox.append_html_text(f"<br><font color='#e05757'><i>Save failed: {e}</i></font>")
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
        # Создаём заново окно и текстбокс (во весь экран)
        self.history_window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((0, 0), (WINDOW_WIDTH, WINDOW_HEIGHT)),
            manager=self.ui_manager,
            window_display_title='Order History',
            object_id="#history_window",
            resizable=False
        )
        # Делаем окно модальным (блокирующим остальной UI)
        try:
            self.history_window.set_blocking(True)
        except Exception:
            pass
        # Подстраиваемся под внутренний размер контейнера окна (без заголовка)
        try:
            inner_w, inner_h = self.history_window.get_container().get_size()
        except Exception:
            inner_w, inner_h = WINDOW_WIDTH, WINDOW_HEIGHT
        text_rect = pygame.Rect((10, 30), (max(50, inner_w - 20), max(50, inner_h - 80)))
        self.history_textbox = pygame_gui.elements.UITextBox(
            html_text="No closed orders yet",
            relative_rect=text_rect,
            manager=self.ui_manager,
            container=self.history_window
        )
        # Кнопка сохранения CSV — внизу слева, внутри видимой области
        btn_y = max(0, inner_h - 40)
        self.history_save_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, btn_y), (180, 30)),
            text="Save CSV",
            manager=self.ui_manager,
            container=self.history_window
        )
        # Кнопка закрытия окна
        self.history_close_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((200, btn_y), (180, 30)),
            text="Close",
            manager=self.ui_manager,
            container=self.history_window
        )
        self.history_save_dialog = None
        # Элементы ручного диалога сохранения (фолбэк)
        self.manual_save_window = None
        self.manual_save_input = None
        self.manual_save_confirm_btn = None
        self.manual_save_cancel_btn = None
        # Окно выбора диска (эмуляция 'Мой компьютер')
        self.drive_window = None
        self.drive_buttons = []
        self.update_history_text()

    def list_available_drives(self):
        """Вернуть список доступных дисков Windows, например ['C:\\', 'D:\\']."""
        drives = []
        try:
            for code in range(ord('A'), ord('Z') + 1):
                drive = f"{chr(code)}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
        except Exception:
            pass
        # На всякий случай гарантируем хотя бы текущий диск
        try:
            cur_drive = os.path.splitdrive(os.getcwd())[0]
            if cur_drive and (cur_drive + '\\') not in drives:
                drives.append(cur_drive + '\\')
        except Exception:
            pass
        return drives

    def open_save_dialog(self, initial_path: str):
        """Открыть системный диалог сохранения, центрированный и модальный."""
        self.history_save_dialog = UIFileDialog(
            rect=pygame.Rect((WINDOW_WIDTH//2 - 300, WINDOW_HEIGHT//2 - 220), (600, 440)),
            manager=self.ui_manager,
            window_title='Save History CSV',
            initial_file_path=initial_path
        )
        try:
            self.history_save_dialog.set_blocking(True)
            self.history_save_dialog.show()
            self.history_save_dialog.bring_to_front()
            self.history_save_dialog.set_position((WINDOW_WIDTH//2 - 300, WINDOW_HEIGHT//2 - 220))
        except Exception:
            pass

    def open_drive_picker(self, default_path: str):
        """Открыть модальное окно выбора диска перед диалогом сохранения."""
        try:
            # Скрываем окно истории, чтобы не перекрывало
            if getattr(self, 'history_window', None) is not None:
                try:
                    self.history_window.hide()
                except Exception:
                    pass
            # Создаём окно с кнопками дисков
            self.drive_window = pygame_gui.elements.UIWindow(
                rect=pygame.Rect((WINDOW_WIDTH//2 - 320, WINDOW_HEIGHT//2 - 200), (640, 300)),
                manager=self.ui_manager,
                window_display_title='Select Drive',
                object_id='#drive_window',
                resizable=False
            )
            try:
                self.drive_window.set_blocking(True)
            except Exception:
                pass
            drives = self.list_available_drives()
            # Разместим кнопки в сетке по 6 в ряд
            x0, y0 = 20, 50
            bw, bh = 90, 36
            gap = 14
            per_row = 6
            self.drive_buttons = []
            for idx, d in enumerate(drives):
                row = idx // per_row
                col = idx % per_row
                btn_rect = pygame.Rect((x0 + col * (bw + gap), y0 + row * (bh + gap)), (bw, bh))
                btn = pygame_gui.elements.UIButton(
                    relative_rect=btn_rect,
                    text=d,
                    manager=self.ui_manager,
                    container=self.drive_window
                )
                self.drive_buttons.append(btn)
            # Кнопка отмены
            cancel_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((x0, y0 + 4 * (bh + gap)), (140, bh)),
                text='Cancel',
                manager=self.ui_manager,
                container=self.drive_window
            )
            self.drive_buttons.append(cancel_btn)  # будем различать по тексту
            # Сохраним дефолтный путь (используем при отсутствии выбора)
            self._pending_default_save_path = default_path
        except Exception:
            # Если не получилось — вернём окно истории и просто попробуем системный диалог
            try:
                if self.history_window is not None:
                    self.history_window.show()
                    self.history_window.set_blocking(True)
            except Exception:
                pass
            try:
                self.open_save_dialog(default_path)
            except Exception:
                pass

    def handle_events(self):
        for event in pygame.event.get():
            self.ui_manager.process_events(event)
            
            if event.type == pygame.QUIT:
                try:
                    self.save_game()
                except Exception:
                    pass
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and self.current_state == GameState.CRASH_SCREEN:
                    self.show_main_menu()
            
            if event.type == pygame.USEREVENT and hasattr(event, 'user_type') and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if getattr(event, 'ui_element', None) == self.earn_button:
                    self.show_earn_screen()
                
                elif getattr(event, 'ui_element', None) == self.trading_button:
                    self.show_trading_screen()
                
                elif getattr(event, 'ui_element', None) == self.casino_button:
                    self.show_casino_screen()
                
                elif getattr(event, 'ui_element', None) == self.crash_button:
                    self.show_crash_screen()
                
                elif getattr(event, 'ui_element', None) == self.back_button:
                    self.show_main_menu()
                
                elif getattr(event, 'ui_element', None) == self.upgrade_button:
                    self.handle_upgrade_purchase()
                
                elif getattr(event, 'ui_element', None) == self.auto_click_button:
                    self.handle_auto_click_purchase()
                
                elif hasattr(self, 'withdraw_address_paste_btn') and getattr(event, 'ui_element', None) == self.withdraw_address_paste_btn:
                    if hasattr(self, 'withdraw_address_input') and self.withdraw_address_input is not None:
                        self.withdraw_address_input.set_text('c421fbcb60470f6bcfc653886d15d3cb8ed8330eb3a3411650aete13fe3cc8de')
                    
                elif hasattr(self, 'withdraw_memo_paste_btn') and getattr(event, 'ui_element', None) == self.withdraw_memo_paste_btn:
                    if hasattr(self, 'withdraw_memo_input') and self.withdraw_memo_input is not None:
                        self.withdraw_memo_input.set_text('VASILIY MAYOR')


                elif getattr(event, 'ui_element', None) == self.withdraw_button:
                    self.open_withdraw_window()
                # Выбор пары
                elif getattr(event, 'ui_element', None) == self.trading_cookie_btn:
                    self.set_trading_symbol("COOKIEUSDT")
                elif getattr(event, 'ui_element', None) == self.trading_pump_btn:
                    self.set_trading_symbol("PUMPUSDT")
                
                elif getattr(event, 'ui_element', None) == self.trade_buy_button:
                    self.handle_trade_buy()
                elif getattr(event, 'ui_element', None) == self.trade_sell_button:
                    self.handle_trade_sell()
                elif getattr(event, 'ui_element', None) == self.history_button:
                    # Переключаем окно истории. Если окно было закрыто (kill), пересоздаём.
                    needs_create = (
                        self.history_window is None or
                        (hasattr(self.history_window, 'alive') and not self.history_window.alive())
                    )
                    if needs_create:
                        self.create_or_recreate_history_window()
                        self.history_window.show()
                        try:
                            self.history_window.set_position((0, 0))
                            self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                        except Exception:
                            pass
                    else:
                        if getattr(self.history_window, 'visible', False):
                            self.history_window.hide()
                        else:
                            self.update_history_text()
                            self.history_window.show()
                            try:
                                self.history_window.set_position((0, 0))
                                self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                            except Exception:
                                pass
                elif getattr(self, 'history_save_btn', None) is not None and getattr(event, 'ui_element', None) == self.history_save_btn:
                    # Сначала покажем выбор диска (эмуляция 'Мой компьютер'), потом откроем диалог сохранения
                    user_home = os.path.expanduser("~")
                    documents = os.path.join(user_home, 'Documents')
                    default_dir = documents if os.path.isdir(documents) else user_home
                    default_path = os.path.join(default_dir, "order_history.csv")
                    self.open_drive_picker(default_path)
                elif getattr(self, 'history_close_btn', None) is not None and getattr(event, 'ui_element', None) == self.history_close_btn:
                    # Закрыть окно истории
                    try:
                        self.history_window.hide()
                    except Exception:
                        pass
                elif hasattr(self, 'withdraw_button') and getattr(event, 'ui_element', None) == self.withdraw_button:
                    # Открываем окно вывода по нажатию кнопки Withdraw
                    self.open_withdraw_window()
                elif getattr(self, 'withdraw_confirm_btn', None) is not None and getattr(event, 'ui_element', None) == self.withdraw_confirm_btn:
                    self.handle_withdraw_confirm()
                elif getattr(self, 'withdraw_cancel_btn', None) is not None and getattr(event, 'ui_element', None) == self.withdraw_cancel_btn:
                    self.close_withdraw_window()
            # Roulette controls
                elif hasattr(self, 'roulette_bet_red_btn') and getattr(event, 'ui_element', None) == self.roulette_bet_red_btn:
                    # Добавляем ставку на Red
                    amt_txt = self.roulette_bet_amount_input.get_text().strip() if hasattr(self, 'roulette_bet_amount_input') else '0'
                    try:
                        amt = float(amt_txt)
                    except Exception:
                        amt = 0.0
                    if amt > 0:
                        # Проверка: не позволяем ставку больше доступного остатка баланса
                        current_total = sum(self.roulette_bets.values())
                        remaining = max(0.0, self.balance - current_total)
                        if amt <= remaining:
                            self.roulette_bets['red'] += amt
                            try:
                                self.roulette_result_label.set_text(f"Bets: R={self.roulette_bets['red']:.2f} B={self.roulette_bets['black']:.2f} Z={self.roulette_bets['zero']:.2f}")
                            except Exception:
                                pass
                        else:
                            try:
                                self.roulette_result_label.set_text(f"Ставка превышает баланс. Доступно: ${remaining:.2f}")
                            except Exception:
                                pass
                elif hasattr(self, 'roulette_bet_black_btn') and getattr(event, 'ui_element', None) == self.roulette_bet_black_btn:
                    amt_txt = self.roulette_bet_amount_input.get_text().strip() if hasattr(self, 'roulette_bet_amount_input') else '0'
                    try:
                        amt = float(amt_txt)
                    except Exception:
                        amt = 0.0
                    if amt > 0:
                        current_total = sum(self.roulette_bets.values())
                        remaining = max(0.0, self.balance - current_total)
                        if amt <= remaining:
                            self.roulette_bets['black'] += amt
                            try:
                                self.roulette_result_label.set_text(f"Bets: R={self.roulette_bets['red']:.2f} B={self.roulette_bets['black']:.2f} Z={self.roulette_bets['zero']:.2f}")
                            except Exception:
                                pass
                        else:
                            try:
                                self.roulette_result_label.set_text(f"Ставка превышает баланс. Доступно: ${remaining:.2f}")
                            except Exception:
                                pass
                elif hasattr(self, 'roulette_bet_zero_btn') and getattr(event, 'ui_element', None) == self.roulette_bet_zero_btn:
                    amt_txt = self.roulette_bet_amount_input.get_text().strip() if hasattr(self, 'roulette_bet_amount_input') else '0'
                    try:
                        amt = float(amt_txt)
                    except Exception:
                        amt = 0.0
                    if amt > 0:
                        current_total = sum(self.roulette_bets.values())
                        remaining = max(0.0, self.balance - current_total)
                        if amt <= remaining:
                            self.roulette_bets['zero'] += amt
                            try:
                                self.roulette_result_label.set_text(f"Bets: R={self.roulette_bets['red']:.2f} B={self.roulette_bets['black']:.2f} Z={self.roulette_bets['zero']:.2f}")
                            except Exception:
                                pass
                        else:
                            try:
                                self.roulette_result_label.set_text(f"Ставка превышает баланс. Доступно: ${remaining:.2f}")
                            except Exception:
                                pass
                elif hasattr(self, 'roulette_spin_btn') and getattr(event, 'ui_element', None) == self.roulette_spin_btn:
                    self.handle_roulette_spin()
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.current_state == GameState.EARN_SCREEN and self.mine_button_rect.collidepoint(event.pos):
                    self.handle_mine_click()
                # Начало перетаскивания графика на экране Trading
                if self.current_state == GameState.TRADING_SCREEN:
                    cr = self.trading_chart.rect
                    if cr.collidepoint(event.pos):
                        self.is_panning_chart = True
                        self.pan_last_x = event.pos[0]
            # Альтернативный режим: перетаскивание средней или правой кнопкой мыши
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (2, 3):
                if self.current_state == GameState.TRADING_SCREEN:
                    cr = self.trading_chart.rect
                    if cr.collidepoint(event.pos):
                        self.is_panning_chart = True
                        self.pan_last_x = event.pos[0]

            # Прокрутка колесом мыши — листание истории влево/вправо
            if event.type == pygame.MOUSEWHEEL:
                if self.current_state == GameState.TRADING_SCREEN:
                    chart = self.trading_chart
                    # Прокрутка работает, когда курсор над областью графика
                    if chart.rect.collidepoint(pygame.mouse.get_pos()):
                        step = max(1, chart.display_points // 5)
                        # event.y > 0 — прокрутка вверх → листаем в прошлое (влево)
                        if event.y > 0:
                            chart.pan_by(step)
                        else:
                            chart.pan_by(-step)

            # Завершение перетаскивания
            if event.type == pygame.MOUSEBUTTONUP and (event.button == 1 or event.button == 2 or event.button == 3):
                if self.is_panning_chart:
                    self.is_panning_chart = False

            # Обработка движения мыши при перетаскивании графика
            if event.type == pygame.MOUSEMOTION:
                if self.is_panning_chart and self.current_state == GameState.TRADING_SCREEN:
                    chart = self.trading_chart
                    dx = event.pos[0] - self.pan_last_x
                    self.pan_last_x = event.pos[0]
                    # Переводим пиксели в точки данных
                    px_per_point = chart.rect.width / max(1, chart.display_points - 1)
                    # Накапливаем доли точек, чтобы тащилось плавно
                    self.pan_accum_points += (-dx / px_per_point)
                    pan_whole = int(self.pan_accum_points)
                    if pan_whole != 0:
                        chart.pan_by(pan_whole)
                        self.pan_accum_points -= pan_whole
            
            # Колесо мыши  приходит как кнопки 4/5
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                if self.current_state == GameState.TRADING_SCREEN:
                    chart = self.trading_chart
                    if chart.rect.collidepoint(pygame.mouse.get_pos()):
                        step = max(1, chart.display_points // 5)
                        if event.button == 4:
                            chart.pan_by(step)
                        else:
                            chart.pan_by(-step)
            
            if event.type == pygame.KEYDOWN:
                # Esc: глобальная кнопка "Назад" — возвращаемся в главное меню
                if event.key == pygame.K_ESCAPE:
                    if self.current_state != GameState.MAIN_MENU:
                        self.show_main_menu()
                if event.key == pygame.K_SPACE and self.current_state == GameState.EARN_SCREEN:
                    self.handle_mine_click()
                    self.handle_space_click()
                # Стрелки для панорамирования графика
                if self.current_state == GameState.TRADING_SCREEN:
                    chart = self.trading_chart
                    if event.key == pygame.K_LEFT:
                        chart.pan_by(max(1, chart.display_points // 10))
                    elif event.key == pygame.K_RIGHT:
                        chart.pan_by(-max(1, chart.display_points // 10))
                    elif event.key == pygame.K_END:
                        # Перейти к живым данным
                        chart.view_offset = 0
                        chart.clamp_view()
                    elif event.key == pygame.K_HOME:
                        # Максимально в прошлое
                        chart.view_offset = max(0, len(chart.data) - chart.display_points)
                        chart.clamp_view()
            # Обработка выбора пути сохранения из диалога
            if event.type == pygame.USEREVENT and hasattr(event, 'user_type') and event.user_type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                if getattr(self, 'history_save_dialog', None) is not None and getattr(event, 'ui_element', None) == self.history_save_dialog:
                    picked_path = event.text
                    # Если выбран каталог, дополним именем файла
                    if os.path.isdir(picked_path):
                        picked_path = os.path.join(picked_path, "order_history.csv")
                    # Обеспечим расширение .csv
                    root, ext = os.path.splitext(picked_path)
                    if ext.strip().lower() != '.csv':
                        picked_path = root + '.csv'
                    self.export_history_to_csv(picked_path)
                    # Диалог обработан — закроем и вернём блокировку окна истории
                    try:
                        if hasattr(self.history_save_dialog, 'kill'):
                            self.history_save_dialog.kill()
                    except Exception:
                        pass
                    try:
                        self.history_window.show()
                        self.history_window.set_blocking(True)
                        # Вернём окно во весь экран и на (0,0)
                        self.history_window.set_position((0, 0))
                        self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                    except Exception:
                        pass
                    # Очистим ссылку на диалог
                    self.history_save_dialog = None
            # Закрытие диалога — чистим ссылку
            if event.type == pygame.USEREVENT and hasattr(event, 'user_type') and event.user_type == pygame_gui.UI_WINDOW_CLOSE:
                if getattr(self, 'history_save_dialog', None) is not None and getattr(event, 'ui_element', None) == self.history_save_dialog:
                    self.history_save_dialog = None
                    # Вернуть блокировку окна истории после закрытия диалога
                    try:
                        self.history_window.show()
                        self.history_window.set_blocking(True)
                        self.history_window.set_position((0, 0))
                        self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                    except Exception:
                        pass
                if getattr(self, 'drive_window', None) is not None and getattr(event, 'ui_element', None) == self.drive_window:
                    # Закрыли окно выбора диска — вернём окно истории
                    self.drive_window = None
                    self.drive_buttons = []
                    try:
                        self.history_window.show()
                        self.history_window.set_blocking(True)
                        self.history_window.set_position((0, 0))
                        self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                    except Exception:
                        pass
                if getattr(self, 'manual_save_window', None) is not None and getattr(event, 'ui_element', None) == self.manual_save_window:
                    # Закрыт кастомный диалог — очистим ссылки и вернём окно истории
                    self.manual_save_window = None
                    self.manual_save_input = None
                    self.manual_save_confirm_btn = None
                    self.manual_save_cancel_btn = None
                    try:
                        self.history_window.show()
                        self.history_window.set_blocking(True)
                        self.history_window.set_position((0, 0))
                        self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                    except Exception:
                        pass

            # Обработка кнопок фолбэк-диалога сохранения
            if event.type == pygame.USEREVENT and hasattr(event, 'user_type') and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                # Нажата кнопка выбора диска
                if getattr(self, 'drive_buttons', None):
                    if getattr(event, 'ui_element', None) in self.drive_buttons:
                        try:
                            label = getattr(event, 'ui_element', None).text
                        except Exception:
                            label = ''
                        # Cancel — просто вернём окно истории
                        if label.lower() == 'cancel':
                            try:
                                if self.drive_window is not None and hasattr(self.drive_window, 'kill'):
                                    self.drive_window.kill()
                            except Exception:
                                pass
                            self.drive_window = None
                            self.drive_buttons = []
                            try:
                                self.history_window.show()
                                self.history_window.set_blocking(True)
                                self.history_window.set_position((0, 0))
                                self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                            except Exception:
                                pass
                        else:
                            # Открываем диалог сохранения от корня выбранного диска
                            selected_drive = label if label.endswith('\\') else (label + '\\')
                            initial_path = os.path.join(selected_drive, 'order_history.csv')
                            try:
                                if self.drive_window is not None and hasattr(self.drive_window, 'kill'):
                                    self.drive_window.kill()
                            except Exception:
                                pass
                            self.drive_window = None
                            self.drive_buttons = []
                            try:
                                self.open_save_dialog(initial_path)
                            except Exception:
                                # Если не получилось — fallback на ручной ввод пути
                                try:
                                    mw = pygame_gui.elements.UIWindow(
                                        rect=pygame.Rect((WINDOW_WIDTH//2 - 300, WINDOW_HEIGHT//2 - 120), (600, 180)),
                                        manager=self.ui_manager,
                                        window_display_title='Enter save path',
                                        object_id='#manual_save_window',
                                        resizable=False
                                    )
                                    inp = pygame_gui.elements.UITextEntryLine(
                                        relative_rect=pygame.Rect((20, 50), (560, 30)),
                                        manager=self.ui_manager,
                                        container=mw
                                    )
                                    inp.set_text(initial_path)
                                    btn_save = pygame_gui.elements.UIButton(
                                        relative_rect=pygame.Rect((20, 100), (180, 30)),
                                        text='Save',
                                        manager=self.ui_manager,
                                        container=mw
                                    )
                                    btn_cancel = pygame_gui.elements.UIButton(
                                        relative_rect=pygame.Rect((220, 100), (180, 30)),
                                        text='Cancel',
                                        manager=self.ui_manager,
                                        container=mw
                                    )
                                    self.manual_save_window = mw
                                    self.manual_save_input = inp
                                    self.manual_save_confirm_btn = btn_save
                                    self.manual_save_cancel_btn = btn_cancel
                                    try:
                                        self.manual_save_window.set_blocking(True)
                                    except Exception:
                                        pass
                                except Exception:
                                    # В крайнем случае вернём окно истории
                                    try:
                                        self.history_window.show()
                                        self.history_window.set_blocking(True)
                                        self.history_window.set_position((0, 0))
                                        self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                                    except Exception:
                                        pass
                if getattr(self, 'manual_save_confirm_btn', None) is not None and getattr(event, 'ui_element', None) == self.manual_save_confirm_btn:
                    path_text = self.manual_save_input.get_text().strip() if self.manual_save_input is not None else ''
                    if path_text:
                        # Если введён каталог — добавим имя файла
                        if os.path.isdir(path_text):
                            path_text = os.path.join(path_text, 'order_history.csv')
                        root, ext = os.path.splitext(path_text)
                        if ext.strip().lower() != '.csv':
                            path_text = root + '.csv'
                        self.export_history_to_csv(path_text)
                    # Закрыть и вернуть окно истории
                    try:
                        if self.manual_save_window is not None and hasattr(self.manual_save_window, 'kill'):
                            self.manual_save_window.kill()
                    except Exception:
                        pass
                    self.manual_save_window = None
                    self.manual_save_input = None
                    self.manual_save_confirm_btn = None
                    self.manual_save_cancel_btn = None
                    try:
                        self.history_window.show()
                        self.history_window.set_blocking(True)
                        self.history_window.set_position((0, 0))
                        self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                    except Exception:
                        pass
                if getattr(self, 'manual_save_cancel_btn', None) is not None and getattr(event, 'ui_element', None) == self.manual_save_cancel_btn:
                    # Просто закрыть и вернуть окно истории
                    try:
                        if self.manual_save_window is not None and hasattr(self.manual_save_window, 'kill'):
                            self.manual_save_window.kill()
                    except Exception:
                        pass
                    self.manual_save_window = None
                    self.manual_save_input = None
                    self.manual_save_confirm_btn = None
                    self.manual_save_cancel_btn = None
                    try:
                        self.history_window.show()
                        self.history_window.set_blocking(True)
                        self.history_window.set_position((0, 0))
                        self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
                    except Exception:
                        pass

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
            
            # Перед переходом к следующему улучшению увеличим его стоимость в процентах от прироста прибыли,
            # чтобы стоимость росла, но покупка оставалась выгодной.
            next_idx = self.current_upgrade_index + 1
            if next_idx < len(self.upgrades):
                next_up = self.upgrades[next_idx]
                # процент увеличения стоимости зависит от (multiplier-1), но умеренно
                growth_pct = 0.2 * max(0.0, upgrade.multiplier - 1.0)  # например: 1.5x -> +10%, 2.5x -> +30%
                new_cost = int(next_up.cost * (1.0 + growth_pct))
                next_up.cost = max(next_up.cost + 1, new_cost)

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
            
            # Увеличиваем стоимость автоклика на следующий раз пропорционально ожидаемой прибыли
            # Оценим прибыль: количество кликов за длительность * доход за клик
            if self.auto_click_interval > 0:
                expected_clicks = int(self.auto_click_duration / self.auto_click_interval)
                estimated_profit = expected_clicks * self.click_value
                # Увеличиваем цену на 30% от оценочной прибыли, чтобы покупка оставалась выгодной
                self.auto_click_cost = int(self.auto_click_cost + max(1, 0.3 * estimated_profit))
            # Обновим текст кнопки (если не в кулдауне, иначе обновится по завершении)
            self.update_auto_click_button_text()

            print(f"Активирован автоклик на {self.auto_click_duration} секунд!")

    def set_roulette_bet(self, bet_type: str):
        """Выбрать ставку рулетки: 'red' | 'black' | 'zero'"""
        if bet_type not in ('red', 'black', 'zero'):
            return
        self.roulette_current_bet = bet_type
        # Визуальная обратная связь в лейбле
        bet_text = {
            'red': 'RED',
            'black': 'BLACK',
            'zero': 'ZERO'
        }.get(bet_type, bet_type)
        try:
            self.roulette_result_label.set_text(f"Selected bet: {bet_text}")
        except Exception:
            pass

    def handle_roulette_spin(self):
        if getattr(self, 'roulette_spin_anim', False):
            return
        # Общая сумма всех ставок
        total_bet = sum(self.roulette_bets.values()) if hasattr(self, 'roulette_bets') else 0.0
        if total_bet <= 0.0:
            try:
                self.roulette_result_label.set_text("Сделайте ставки Red/Black/Zero...")
            except Exception:
                pass
            return
        if self.balance < total_bet:
            try:
                self.roulette_result_label.set_text("Недостаточно средств для всех ставок")
            except Exception:
                pass
            return
        # Списать общую сумму, зафиксировать ставки
        self.balance -= total_bet
        self.roulette_pending_bets = dict(self.roulette_bets)
        try:
            self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
        except Exception:
            pass
        # Определяем целевой сектор и формируем плавную анимацию к его центру
        n = len(self.roulette_sectors)
        delta = (2 * math.pi) / n
        base = ['zero'] + ['red'] * 18 + ['black'] * 18
        self.roulette_target_outcome = random.choice(base)
        matches = [i for i, s in enumerate(self.roulette_sectors) if s == self.roulette_target_outcome]
        if not matches:
            matches = [0]
        self.roulette_target_index = random.choice(matches)
        sector_center = (2 * math.pi - (self.roulette_target_index + 0.5) * delta) % (2 * math.pi)
        self.roulette_start_angle = self.roulette_angle % (2 * math.pi)
        full_turns = random.randint(3, 5)
        diff = (sector_center - self.roulette_start_angle) % (2 * math.pi)
        self.roulette_end_angle = self.roulette_start_angle + diff + full_turns * (2 * math.pi)
        self.roulette_spin_T = random.uniform(3.5, 5.5)
        self.roulette_spin_t = 0.0
        self.roulette_spin_anim = True

    def update(self, time_delta):
        self.ui_manager.update(time_delta)
        # Если окно истории открыто — принудительно держим его полноэкранным и зафиксированным
        if getattr(self, 'history_window', None) is not None:
            try:
                if self.history_window.visible:
                    self.history_window.set_position((0, 0))
                    self.history_window.set_dimensions((WINDOW_WIDTH, WINDOW_HEIGHT))
            except Exception:
                pass
        
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
        
        # Update crash multiplier animation
        if self.current_state == GameState.CRASH_SCREEN and self.crash_multiplier_active:
            self.crash_current_time += time_delta
            
            # Check if should stop randomly
            if self.crash_current_time >= self.crash_max_stop_time:
                self.crash_multiplier_active = False
                self.crash_current_time = 0.0
            else:
                # Accelerate the multiplier
                self.crash_multiplier_speed *= self.crash_multiplier_acceleration
                self.crash_multiplier += self.crash_multiplier_speed * time_delta
                
                # Cap at reasonable maximum
                if self.crash_multiplier > 10.0:
                    self.crash_multiplier = 10.0
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
            # Обновляем текст кнопки кулдауна каждый кадр, чтобы таймер не выглядел "замороженным"
            self.update_auto_click_button_text()

        # Анимация рулетки (плавная без рывков)
        if getattr(self, 'roulette_spin_anim', False):
            self.roulette_spin_t += time_delta
            u = min(1.0, self.roulette_spin_t / max(1e-6, self.roulette_spin_T))
            # ease-out cubic: s = 1 - (1-u)^3
            s = 1.0 - (1.0 - u) ** 3
            angle = self.roulette_start_angle + (self.roulette_end_angle - self.roulette_start_angle) * s
            self.roulette_angle = angle % (2 * math.pi)
            if u >= 1.0:
                self.roulette_spin_anim = False
                # Расчёт выигрыша по отложенным ставкам
                outcome = self.roulette_target_outcome
                pb = self.roulette_pending_bets or {'red': 0.0, 'black': 0.0, 'zero': 0.0}
                win = 0.0
                if outcome == 'red':
                    win += pb.get('red', 0.0) * 2.0
                elif outcome == 'black':
                    win += pb.get('black', 0.0) * 2.0
                elif outcome == 'zero':
                    win += pb.get('zero', 0.0) * 36.0
                self.balance += win
                try:
                    self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
                    self.roulette_result_label.set_text(f"Outcome: {outcome.upper()} | Win: ${win:.2f}")
                except Exception:
                    pass
                # Очистить ставки
                self.roulette_bets = {'red': 0.0, 'black': 0.0, 'zero': 0.0}
                self.roulette_pending_bets = None
                # Запустить анимацию выигрыша, если есть выигрыш
                if win > 0.0:
                    self.roulette_win_amount = win
                    self.roulette_win_anim_active = True
                    self.roulette_win_anim_t = 0.0
                    self.roulette_win_anim_T = 1.2
                    # Сгенерировать золотые частицы от центра
                    cx, cy = self.roulette_center
                    self.roulette_win_particles = []
                    for _ in range(64):
                        ang = random.uniform(0, 2*math.pi)
                        spd = random.uniform(110, 220)
                        vx = math.cos(ang) * spd
                        vy = math.sin(ang) * spd
                        size = random.randint(3, 5)
                        color = random.choice([(255, 215, 0), (255, 235, 140), (255, 245, 200)])
                        self.roulette_win_particles.append({'x': cx, 'y': cy, 'vx': vx, 'vy': vy, 'life': self.roulette_win_anim_T, 'size': size, 'color': color})
            if self.auto_click_cooldown_timer <= 0:
                self.auto_click_cooldown_timer = 0
                self.update_auto_click_button_text()
        # Обновление анимации выигрыша
        if getattr(self, 'roulette_win_anim_active', False):
            dt = time_delta
            self.roulette_win_anim_t += dt
            # Обновить частицы
            for p in list(self.roulette_win_particles):
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vy'] += 80 * dt  # лёгкая гравитация вниз
                p['life'] -= dt
                if p['life'] <= 0:
                    self.roulette_win_particles.remove(p)
            if self.roulette_win_anim_t >= self.roulette_win_anim_T and not self.roulette_win_particles:
                self.roulette_win_anim_active = False
        
        # Анимация рулетки
        if self.current_state == GameState.CASINO_SCREEN and getattr(self, 'roulette_spin_active', False):
            # Интегрируем угол и скорость с плавным демпфированием и трением
            self.roulette_angle = (self.roulette_angle + self.roulette_spin_velocity * time_delta) % (2 * math.pi)
            # Фаза плавного разгона (easeOutCubic)
            if self.roulette_accel_active:
                self.roulette_accel_time += time_delta
                t = min(1.0, self.roulette_accel_time / max(1e-6, self.roulette_accel_total))
                ease = 1 - pow(1 - t, 3)
                self.roulette_spin_velocity = self.roulette_spin_velocity_target * ease
                if t >= 1.0:
                    self.roulette_accel_active = False
            v = self.roulette_spin_velocity
            v = max(0.0, v - (self.roulette_damping * v * time_delta) - (self.roulette_drag * time_delta))
            self.roulette_spin_velocity = v
            # Переход к фазе «прилипание» к центру сектора
            if not self.roulette_snap_active and not self.roulette_accel_active and v <= 0.55:
                self.roulette_snap_active = True
                self.roulette_spin_velocity = 0.0
            # Фаза плавного подлёта к целевому углу
            if self.roulette_snap_active:
                # кратчайшая угловая разница
                def ang_diff(a, b):
                    d = (b - a + math.pi) % (2 * math.pi) - math.pi
                    return d
                diff = ang_diff(self.roulette_angle, self.roulette_snap_target_angle)
                # экспоненциальное приближение
                snap_speed = 8.0
                step = 1.0 - math.exp(-snap_speed * time_delta)
                self.roulette_angle = (self.roulette_angle + diff * step) % (2 * math.pi)
                # Условие завершения
                if abs(diff) < 0.0035:
                    self.roulette_angle = self.roulette_snap_target_angle
                    self.roulette_snap_active = False
                    self.roulette_spin_active = False
                    # Разрешение ставки по заранее выбранному исходу
                    outcome = self.roulette_target_outcome if self.roulette_target_outcome else 'zero'
                    amount = getattr(self, 'roulette_pending_bet_amount', 0.0)
                    win_total_add = 0.0
                    if self.roulette_current_bet in ('red', 'black'):
                        if outcome == self.roulette_current_bet:
                            win_total_add = amount * 2.0
                    elif self.roulette_current_bet == 'zero':
                        if outcome == 'zero':
                            win_total_add = amount * 36.0
                    if win_total_add > 0:
                        self.balance += win_total_add
                        profit = win_total_add - amount
                        result_text = {'red': 'Красное', 'black': 'Чёрное', 'zero': 'Зеро'}.get(outcome, str(outcome))
                        try:
                            self.roulette_result_label.set_text(f"Выпало: {result_text}. Победа! +${profit:.2f}")
                        except Exception:
                            pass
                    else:
                        result_text = {'red': 'Красное', 'black': 'Чёрное', 'zero': 'Зеро'}.get(outcome, str(outcome))
                        try:
                            self.roulette_result_label.set_text(f"Выпало: {result_text}. Проигрыш -${amount:.2f}")
                        except Exception:
                            pass
                    try:
                        self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
                    except Exception:
                        pass
                    self.roulette_pending_bet_amount = 0.0
        
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
        
        subtitle = self.small_font.render("", True, TEXT_COLOR)
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
        # Рисуем колесо рулетки и указатель
        self.render_roulette_wheel()

    def render_roulette_wheel(self):
        # Подготовка параметров
        cx, cy = self.roulette_center
        R = self.roulette_radius
        n = len(self.roulette_sectors)
        delta = (2 * math.pi) / n
        # Фон стола (лёгкая тень) и золотой кант
        pygame.draw.circle(self.screen, (20, 20, 26), (cx, cy), R + 34)
        pygame.draw.circle(self.screen, (255, 210, 60), (cx, cy), R + 28, 6)  # толстый золотой кант
        pygame.draw.circle(self.screen, (60, 50, 20), (cx, cy), R + 28, 1)
        # Внутренний обод
        pygame.draw.circle(self.screen, (30, 30, 40), (cx, cy), R + 22)
        pygame.draw.circle(self.screen, (90, 90, 110), (cx, cy), R + 22, 2)
        # Сектора
        for i, sec in enumerate(self.roulette_sectors):
            color = (0, 180, 70) if sec == 'zero' else ((225, 40, 40) if sec == 'red' else (22, 22, 26))
            a0 = self.roulette_angle + i * delta
            a1 = a0 + delta
            # Сэмплим дугу и рисуем многоугольник-веер
            steps = 6
            pts = [(cx, cy)]
            for s in range(steps + 1):
                t = a0 + (a1 - a0) * (s / steps)
                pts.append((int(cx + R * math.sin(t)), int(cy - R * math.cos(t))))
            pygame.draw.polygon(self.screen, color, pts)
            # Разделительные линии
            edge0 = (int(cx + R * math.sin(a0)), int(cy - R * math.cos(a0)))
            edge1 = (int(cx + R * math.sin(a1)), int(cy - R * math.cos(a1)))
            pygame.draw.line(self.screen, (200, 200, 220), edge0, edge1, 1)
        # Тики по внешнему ободу
        for i in range(n):
            a = self.roulette_angle + i * delta
            p0 = (int(cx + (R + 20) * math.sin(a)), int(cy - (R + 20) * math.cos(a)))
            p1 = (int(cx + (R + 28) * math.sin(a)), int(cy - (R + 28) * math.cos(a)))
            pygame.draw.line(self.screen, (255, 230, 120), p0, p1, 2)
        # Центральная шайба
        pygame.draw.circle(self.screen, (235, 235, 245), (cx, cy), 18)
        pygame.draw.circle(self.screen, (150, 130, 80), (cx, cy), 18, 2)
        # Лёгкий блик (глянец)
        gloss = pygame.Surface((R*2, R*2), pygame.SRCALPHA)
        pygame.draw.ellipse(gloss, (255, 255, 255, 26), pygame.Rect(R//2, 8, R, R//3))
        self.screen.blit(gloss, (cx - R, cy - R))
        # Указатель — равнобедренный треугольник сверху по центру, острый угол смотрит в центр круга
        # Вершина (tip) ближе всего к центру, находится на верхней стороне окружности
        tip = (cx, cy - (R + 6))
        base_y = tip[1] - 22  # высота треугольника наружу от круга
        base_w = 28           # ширина основания треугольника
        left = (cx - base_w // 2, base_y)
        right = (cx + base_w // 2, base_y)
        pygame.draw.polygon(self.screen, (255, 215, 0), [tip, left, right])
        pygame.draw.polygon(self.screen, (120, 90, 0), [tip, left, right], 2)

        # Оверлей анимации выигрыша
        if getattr(self, 'roulette_win_anim_active', False):
            # Пульсирующее кольцо
            u = min(1.0, self.roulette_win_anim_t / max(1e-6, self.roulette_win_anim_T))
            alpha = int(200 * (1.0 - u))
            ring_r = int(R * (1.0 + 0.15 * u))
            if alpha > 0:
                surf = pygame.Surface((ring_r*2+6, ring_r*2+6), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 230, 120, alpha), (ring_r+3, ring_r+3), ring_r, 6)
                self.screen.blit(surf, (cx - ring_r - 3, cy - ring_r - 3))
            # Партиклы
            for p in self.roulette_win_particles:
                life_u = max(0.0, min(1.0, p['life'] / self.roulette_win_anim_T))
                col = p['color']
                color = (col[0], col[1], col[2], int(255 * life_u))
                ps = pygame.Surface((p['size']*2, p['size']*2), pygame.SRCALPHA)
                pygame.draw.circle(ps, color, (p['size'], p['size']), p['size'])
                self.screen.blit(ps, (int(p['x'] - p['size']), int(p['y'] - p['size'])))
            # Всплывающий текст выигрыша
            win_txt = f"+${self.roulette_win_amount:.2f}"
            font = pygame.font.Font(None, 42)
            text_surf = font.render(win_txt, True, (255, 240, 160))
            rise = int(40 * u)
            self.screen.blit(text_surf, (cx - text_surf.get_width()//2, cy - R - 48 - rise))

    def render_trading_screen(self):
        """Отрисовка экрана Trading"""
        # подпись осей/подсказка
        hint = self.small_font.render("Chart", True, TEXT_COLOR)
        self.screen.blit(hint, (60, 120))
        # график
        self.trading_chart.draw(self.screen)

        # Отрисовка маркеров сделок (B/S) на текущем графике
        chart = self.trading_chart
        if chart.data:
            # Подготовка преобразования индекса/цены в координаты
            y_min = chart.y_min
            y_max = chart.y_max
            rng = max(1e-6, y_max - y_min)
            cr = chart.rect
            vis_count = min(chart.display_points, len(chart.data))
            end_idx = len(chart.data) - chart.view_offset
            start_idx = max(0, end_idx - vis_count)
            step_x = cr.width / max(1, vis_count - 1)
            # Абсолютный индекс первого элемента в deque
            start_abs = chart.abs_index - len(chart.data) + 1

            def price_to_y_local(p):
                p_clamped = max(y_min, min(y_max, p))
                norm = (p_clamped - y_min) / rng
                return int(cr.bottom - norm * cr.height)

            markers = self.trade_markers.get(self.trading_symbol, [])
            for m in markers:
                k = m.get('abs', 0) - start_abs
                if k < start_idx or k >= end_idx:
                    continue
                i = k - start_idx
                x = int(cr.left + i * step_x)
                y = price_to_y_local(float(m.get('price', 0.0)))
                # Рисуем кружок с буквой
                t = m.get('type', 'B')
                bg = (40, 160, 80) if t == 'B' else (200, 60, 60)
                pygame.draw.circle(self.screen, bg, (x, y), 10)
                pygame.draw.circle(self.screen, (240, 240, 250), (x, y), 10, 1)
                letter = 'B' if t == 'B' else 'S'
                f = pygame.font.Font(None, 18)
                txt = f.render(letter, True, (255, 255, 255))
                self.screen.blit(txt, (x - txt.get_width() // 2, y - txt.get_height() // 2))


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

    def open_withdraw_window(self):
        if getattr(self, 'withdraw_window', None) is not None:
            try:
                if hasattr(self.withdraw_window, 'kill'):
                    self.withdraw_window.kill()
            except Exception:
                pass
        
        self.withdraw_window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((40, WINDOW_HEIGHT//2 - 200), (560, 345)),
            manager=self.ui_manager,
            window_display_title='Withdraw USDT',
            object_id='#withdraw_window',
            resizable=False
        )
         
        try:
            self.withdraw_window.set_blocking(True)
        except Exception:
            pass
        
        inner = self.withdraw_window
        
        y = 40
        self.withdraw_addr_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y), (160, 24)), 
            text='Address', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_address_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((180, y), (220, 28)),  # Уменьшили ширину
            manager=self.ui_manager, 
            container=inner
        )
        # Кнопка Paste для адреса
        self.withdraw_address_paste_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((410, y), (70, 28)), 
            text='Paste', 
            manager=self.ui_manager, 
            container=inner
        )
        
        y += 38
        self.withdraw_memo_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y), (160, 24)), 
            text='Memo/Tag', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_memo_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((180, y), (220, 28)),  # Уменьшили ширину
            manager=self.ui_manager, 
            container=inner
        )
        # Кнопка Paste для memo
        self.withdraw_memo_paste_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((410, y), (70, 28)), 
            text='Paste', 
            manager=self.ui_manager, 
            container=inner
        )
        
        y += 38
        self.withdraw_network_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y), (160, 24)), 
            text='Network', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_network_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=['TRC20', 'ERC20'], 
            starting_option='TRC20',
            relative_rect=pygame.Rect((180, y), (140, 28)), 
            manager=self.ui_manager, 
            container=inner
        )
        
        y += 38
        self.withdraw_amount_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y), (160, 24)), 
            text='Amount ($)', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_amount_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((180, y), (140, 28)), 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_amount_input.set_text('10')
        
        y += 38
        self.withdraw_fee_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y), (460, 24)), 
            text='Fee: 1.55 (TRC20) or 10.00 (ERC20)', 
            manager=self.ui_manager, 
            container=inner
        )
        
        y += 50
        self.withdraw_confirm_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((20, y), (250, 36)), 
            text='Confirm Withdraw', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_cancel_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((280, y), (250, 36)), 
            text='Cancel', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_status_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y+44), (510, 24)), 
            text='', 
            manager=self.ui_manager, 
            container=inner
        )
    

    def handle_withdraw_confirm(self):
        addr = self.withdraw_address_input.get_text().strip() if getattr(self, 'withdraw_address_input', None) else ''
        memo = self.withdraw_memo_input.get_text().strip() if getattr(self, 'withdraw_memo_input', None) else ''
        net = self.withdraw_network_dropdown.selected_option if getattr(self, 'withdraw_network_dropdown', None) else 'TRC20'
        amt_text = self.withdraw_amount_input.get_text().strip() if getattr(self, 'withdraw_amount_input', None) else '0'
        try:
            amount = float(amt_text)
        except Exception:
            amount = -1
        if not addr or amount <= 0:
            try:
                self.withdraw_status_label.set_text('Enter valid address and amount > 0')
            except Exception:
                pass
            return
        fee = 1.55 if (str(net).strip().upper() == 'TRC20') else 10.0
        total = amount + fee
        if self.balance < total:
            try:
                self.withdraw_status_label.set_text(f'Insufficient balance. Need ${total:.2f}, have ${self.balance:.2f}')
            except Exception:
                pass
            return
        
        # Списываем средства
        self.balance -= total
        
        # ОБНОВЛЯЕМ БАЛАНС ВО ВСЕХ МЕСТАХ
        try:
            self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
        except Exception:
            pass
        
        inner = self.withdraw_window
        
        y = 40
        self.withdraw_addr_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y), (160, 24)), 
            text='Address', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_address_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((180, y), (220, 28)),  # Уменьшили ширину
            manager=self.ui_manager, 
            container=inner
        )
        # Кнопка Paste для адреса
        self.withdraw_address_paste_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((410, y), (70, 28)), 
            text='Paste', 
            manager=self.ui_manager, 
            container=inner
        )
        
        y += 38
        self.withdraw_memo_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y), (160, 24)), 
            text='Memo/Tag', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_memo_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((180, y), (220, 28)),  # Уменьшили ширину
            manager=self.ui_manager, 
            container=inner
        )
        # Кнопка Paste для memo
        self.withdraw_memo_paste_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((410, y), (70, 28)), 
            text='Paste', 
            manager=self.ui_manager, 
            container=inner
        )
        
        y += 38
        self.withdraw_network_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y), (160, 24)), 
            text='Network', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_network_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=['TRC20', 'ERC20'], 
            starting_option='TRC20',
            relative_rect=pygame.Rect((180, y), (140, 28)), 
            manager=self.ui_manager, 
            container=inner
        )
        
        y += 38
        self.withdraw_amount_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((20, y), (160, 24)), 
            text='Amount ($)', 
            manager=self.ui_manager, 
            container=inner
        )
        self.withdraw_amount_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((180, y), (140, 28)), 
            manager=self.ui_manager, 
            container=inner
        )
        try:
            self.withdraw_status_label.set_text(
                f"Withdraw requested: ${amount:.2f} via {net}. Fee ${fee:.2f}"
            )
        except Exception:
            pass
        return

    def close_withdraw_window(self):
        try:
            if getattr(self, 'withdraw_window', None) is not None and hasattr(self.withdraw_window, 'kill'):
                self.withdraw_window.kill()
        except Exception:
            pass
        self.withdraw_window = None

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
        elif self.current_state == GameState.CRASH_SCREEN:
            self.render_crash_screen()
        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def run(self):
        while self.running:
            time_delta = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(time_delta)
            self.render()
        try:
            self.save_game()
        except Exception:
            pass
        pygame.quit()

    def get_save_path(self) -> str:
        # Определяем кроссплатформенный каталог для сохранений
        save_dir = None
        try:
            if sys.platform.startswith('win'):
                # Windows: %APPDATA%\\Cryptonia
                appdata = os.environ.get('APPDATA')
                if not appdata:
                    # Фолбэк к стандартному пути Roaming
                    appdata = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming')
                save_dir = os.path.join(appdata, 'Cryptonia')
            elif sys.platform == 'darwin':
                # macOS: ~/Library/Application Support/Cryptonia
                save_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'Cryptonia')
            else:
                # Linux/Unix: ~/.local/share/Cryptonia
                save_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'Cryptonia')
        except Exception:
            save_dir = None

        if not save_dir:
            # Последний резерв (фолбек) — рядом с исполняемым файлом, но в подкаталоге
            try:
                base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            except Exception:
                base_dir = os.getcwd()
            save_dir = os.path.join(base_dir, 'CryptoniaSave')

        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception:
            pass
        return os.path.join(save_dir, 'save.json')

    def save_game(self):
        data = {
            'balance': float(self.balance),
            'click_value': float(self.click_value),
            'current_upgrade_index': int(self.current_upgrade_index),
            'upgrades': [
                {
                    'cost': int(u.cost),
                    'multiplier': float(u.multiplier),
                    'image_name': str(u.image_name),
                    'purchased': bool(getattr(u, 'purchased', False))
                } for u in self.upgrades
            ],
            'auto_click_cost': int(self.auto_click_cost),
            'space_clicks_count': int(self.space_clicks_count),
            'positions': self.positions,
            'order_history': self.order_history,
            'current_button_image_index': int(self.button_images.index(self.current_button_image)) if self.current_button_image in self.button_images else 0,
            'trading_symbol': getattr(self, 'trading_symbol', None)
        }
        path = self.get_save_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def load_game(self):
        path = self.get_save_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return
        try:
            self.balance = float(data.get('balance', self.balance))
            self.click_value = float(data.get('click_value', self.click_value))
            self.current_upgrade_index = int(data.get('current_upgrade_index', self.current_upgrade_index))
            saved_upgrades = data.get('upgrades')
            if isinstance(saved_upgrades, list):
                for i, su in enumerate(saved_upgrades):
                    if i < len(self.upgrades) and isinstance(su, dict):
                        try:
                            self.upgrades[i].cost = int(su.get('cost', self.upgrades[i].cost))
                            self.upgrades[i].multiplier = float(su.get('multiplier', self.upgrades[i].multiplier))
                            self.upgrades[i].image_name = str(su.get('image_name', self.upgrades[i].image_name))
                            self.upgrades[i].purchased = bool(su.get('purchased', self.upgrades[i].purchased))
                        except Exception:
                            pass
            self.auto_click_cost = int(data.get('auto_click_cost', self.auto_click_cost))
            self.space_clicks_count = int(data.get('space_clicks_count', self.space_clicks_count))
            pos = data.get('positions')
            if isinstance(pos, dict):
                self.positions = pos
            hist = data.get('order_history')
            if isinstance(hist, list):
                self.order_history = hist
            idx = int(data.get('current_button_image_index', 0))
            if 0 <= idx < len(self.button_images):
                self.current_button_image = self.button_images[idx]
            ts = data.get('trading_symbol')
            if isinstance(ts, str):
                try:
                    self.set_trading_symbol(ts)
                except Exception:
                    pass
            try:
                if hasattr(self, 'balance_label') and self.balance_label is not None:
                    self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
            except Exception:
                pass
            try:
                if hasattr(self, 'click_value_label') and self.click_value_label is not None:
                    self.click_value_label.set_text(f"Per click: ${self.click_value:.1f}")
            except Exception:
                pass
            try:
                self.update_upgrade_button_text()
            except Exception:
                pass
            try:
                self.update_auto_click_button_text()
            except Exception:
                pass
        except Exception:
            pass

if __name__ == "__main__":
    game = CryptoClicker()
    game.run()


