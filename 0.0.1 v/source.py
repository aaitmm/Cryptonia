import os
import pygame
import pygame_gui
from config import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, BACKGROUND_COLOR, TEXT_COLOR

class GameState:
    MAIN_MENU = "main_menu"
    EARN_SCREEN = "earn_screen"
    TRADING_SCREEN = "trading_screen"

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
        
        # Загрузка оригинального изображения кнопки
        self.original_button_image = self.load_image("D:\\Porject_python\\Cryptonia\\0.0.1 v\\assets\\mine_button.png", (200, 200))
        
        # Параметры кнопки
        self.button_base_size = 200  # Базовый размер кнопки
        self.button_current_size = 200  # Текущий размер кнопки
        self.button_target_size = 200  # Целевой размер кнопки
        self.button_scale_duration = 0.08  # Длительность анимации масштабирования
        self.button_scale_time = 0  # Таймер анимации
        
        # Позиция круглой кнопки (по центру экрана)
        self.mine_button_rect = self.original_button_image.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 50))
        
        # Только баланс, без счетчика кликов
        self.balance = 100.0
        
        # Эффекты пульсации при клике
        self.click_effects = []  # Список активных эффектов
        
        # Создание UI элементов
        self.create_main_menu()
        self.create_earn_screen()

    def load_image(self, path, size):
        """Загрузка и масштабирование изображения"""
        try:
            # Используем прямой путь
            print(f"Пытаюсь загрузить: {path}")
            
            # Проверяем существование файла
            if not os.path.exists(path):
                print(f"ФАЙЛ НЕ НАЙДЕН: {path}")
                print("Создаю временную кнопку...")
                raise FileNotFoundError(f"Файл {path} не найден")
                
            image = pygame.image.load(path).convert_alpha()
            print("Изображение успешно загружено!")
            return pygame.transform.scale(image, size)
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            # Если изображение не найдено, создаем временную круглую кнопку
            surf = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.circle(surf, (65, 105, 225), (size[0]//2, size[1]//2), size[0]//2)
            pygame.draw.circle(surf, (255, 255, 255), (size[0]//2, size[1]//2), size[0]//2 - 5, 3)
            font = pygame.font.Font(None, 30)
            text = font.render("MINE", True, (255, 255, 255))
            surf.blit(text, (size[0]//2 - text.get_width()//2, size[1]//2 - text.get_height()//2))
            return surf

    def create_main_menu(self):
        """Создание элементов главного меню"""
        # Кнопка Earn (расположена ниже)
        self.earn_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 150, 300), (300, 80)),  
            text="Earn",
            manager=self.ui_manager
        )
        
        # Кнопка Trading (расположена еще ниже)
        self.trading_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH//2 - 150, 400), (300, 80)),  
            text="Trading",
            manager=self.ui_manager
        )
        
        # Скрываем кнопки изначально (будут показаны в главном меню)
        self.earn_button.hide()
        self.trading_button.hide()

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
            text="Earn Screen",
            manager=self.ui_manager
        )
        
        # Label для отображения баланса
        self.balance_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((WINDOW_WIDTH - 300, 50), (250, 50)),
            text=f"Balance: ${self.balance:.2f}",
            manager=self.ui_manager
        )
        
        # Скрываем элементы экрана Earn изначально
        self.back_button.hide()
        self.earn_title.hide()
        self.balance_label.hide()

    def show_main_menu(self):
        """Показать главное меню"""
        self.earn_button.show()
        self.trading_button.show()
        self.back_button.hide()
        self.earn_title.hide()
        self.balance_label.hide()
        self.current_state = GameState.MAIN_MENU

    def show_earn_screen(self):
        """Показать экран Earn"""
        self.earn_button.hide()
        self.trading_button.hide()
        self.back_button.show()
        self.earn_title.show()
        self.balance_label.show()
        self.current_state = GameState.EARN_SCREEN

    def handle_events(self):
        # Обработка событий pygame
        for event in pygame.event.get():
            # Обработка событий UI
            self.ui_manager.process_events(event)
            
            # Обработка выхода из игры
            if event.type == pygame.QUIT:
                self.running = False
                
            # Обработка нажатия кнопок
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.earn_button:
                    self.show_earn_screen()
                    print("Переход в Earn screen")
                
                elif event.ui_element == self.trading_button:
                    print("Trading button clicked (пока никуда не ведет)")
                
                elif event.ui_element == self.back_button:
                    self.show_main_menu()
                    print("Возврат в главное меню")
            
            # Обработка кликов по круглой кнопке
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Левая кнопка мыши
                if self.current_state == GameState.EARN_SCREEN and self.mine_button_rect.collidepoint(event.pos):
                    self.handle_mine_click()

    def handle_mine_click(self):
        """Обработка клика по круглой кнопке с созданием эффекта пульсации"""
        # Запускаем анимацию уменьшения кнопки
        self.button_target_size = 180  # Уменьшаем размер
        self.button_scale_time = self.button_scale_duration
        
        # Создаем новый эффект пульсации
        click_effect = {
            'position': self.mine_button_rect.center,
            'start_radius': self.button_current_size // 2,
            'current_radius': self.button_current_size // 2,
            'max_radius': self.button_current_size // 2 + 40,  # Максимальный радиус волны
            'duration': 0.6,  # Длительность анимации в секундах
            'time_remaining': 0.6,  # Оставшееся время анимации
            'alpha': 200  # Начальная прозрачность
        }
        self.click_effects.append(click_effect)
        
        # Основная логика клика
        self.balance += 1
        self.balance_label.set_text(f"Balance: ${self.balance:.2f}")
        print(f"Клик! Баланс: ${self.balance:.2f}")

    def update(self, time_delta):
        # Обновление UI
        self.ui_manager.update(time_delta)
        
        # Обновление анимации масштабирования кнопки
        if self.button_scale_time > 0:
            self.button_scale_time -= time_delta
            
            if self.button_scale_time <= 0:
                # Анимация завершена, возвращаем к нормальному размеру
                self.button_target_size = self.button_base_size
                self.button_scale_time = self.button_scale_duration
            else:
                # Интерполируем размер кнопки
                progress = 1 - (self.button_scale_time / self.button_scale_duration)
                if self.button_target_size < self.button_base_size:
                    # Уменьшение: быстрое сжатие
                    self.button_current_size = self.button_base_size - (self.button_base_size - self.button_target_size) * progress
                else:
                    # Увеличение: плавное возвращение
                    self.button_current_size = self.button_target_size - (self.button_target_size - self.button_base_size) * (1 - progress)
        
        # Обновление эффектов пульсации
        for effect in self.click_effects[:]:
            effect['time_remaining'] -= time_delta
            
            if effect['time_remaining'] <= 0:
                # Удаляем завершенный эффект
                self.click_effects.remove(effect)
            else:
                # Обновляем параметры анимации
                progress = 1 - (effect['time_remaining'] / effect['duration'])
                
                # Радиус увеличивается от начального до максимального
                effect['current_radius'] = effect['start_radius'] + (
                    effect['max_radius'] - effect['start_radius']) * progress
                
                # Прозрачность уменьшается со временем
                effect['alpha'] = int(200 * (1 - progress))

    def render_main_menu(self):
        """Отрисовка главного меню"""
        # Заголовок игры
        title = self.font.render("Cryptonia", True, TEXT_COLOR)
        self.screen.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 150))
        
        # Подзаголовок
        subtitle = self.small_font.render("Выберите режим игры", True, TEXT_COLOR)
        self.screen.blit(subtitle, (WINDOW_WIDTH//2 - subtitle.get_width()//2, 220))

    def render_earn_screen(self):
        """Отрисовка экрана Earn"""
        # Информация о экране Earn
        info = self.small_font.render("Eaaarn!!", True, TEXT_COLOR)
        self.screen.blit(info, (WINDOW_WIDTH//2 - info.get_width()//2, 180))
        
        # Масштабируем кнопку до текущего размера
        scaled_button = pygame.transform.scale(
            self.original_button_image, 
            (int(self.button_current_size), int(self.button_current_size))
        )
        button_rect = scaled_button.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 50))
        
        # Сначала отрисовываем эффекты пульсации (под кнопкой)
        for effect in self.click_effects:
            # Создаем поверхность с прозрачностью для эффекта
            effect_surface = pygame.Surface((effect['current_radius'] * 2, effect['current_radius'] * 2), pygame.SRCALPHA)
            
            # Рисуем круговую волну
            pygame.draw.circle(
                effect_surface, 
                (255, 255, 255, effect['alpha']),  # Белый цвет с прозрачностью
                (effect['current_radius'], effect['current_radius']), 
                effect['current_radius'], 
                3  # Толщина линии
            )
            
            # Размещаем эффект на экране
            effect_rect = effect_surface.get_rect(center=effect['position'])
            self.screen.blit(effect_surface, effect_rect)
        
        # Отрисовка основной кнопки поверх эффектов
        self.screen.blit(scaled_button, button_rect)
        
        # Обновляем rect кнопки для обработки кликов
        self.mine_button_rect = button_rect
        
        # Анимация при наведении (подсветка)
        mouse_pos = pygame.mouse.get_pos()
        if self.mine_button_rect.collidepoint(mouse_pos):
            # Рисуем круг подсветки
            pygame.draw.circle(
                self.screen, 
                (255, 255, 255, 100), 
                self.mine_button_rect.center, 
                self.button_current_size // 2.145 + 2, 
                3
            )

    def render(self):
        # Очистка экрана
        self.screen.fill(BACKGROUND_COLOR)
        
        # Отрисовка в зависимости от состояния
        if self.current_state == GameState.MAIN_MENU:
            self.render_main_menu()
        elif self.current_state == GameState.EARN_SCREEN:
            self.render_earn_screen()
        
        # Отрисовка UI
        self.ui_manager.draw_ui(self.screen)
        
        # Обновление дисплея
        pygame.display.flip()

    def run(self):
        # Показать главное меню при запуске
        self.show_main_menu()
        
        # Главный игровой цикл
        while self.running:
            # Дельта времени для плавного обновления
            time_delta = self.clock.tick(FPS) / 1000.0
            
            # Обработка событий
            self.handle_events()
            
            # Обновление игры
            self.update(time_delta)
            
            # Отрисовка
            self.render()
        
        # Завершение работы pygame
        pygame.quit()

if __name__ == "__main__":
    game = CryptoClicker()
    game.run()