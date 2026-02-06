import pygame
from collections import deque
import random


class LineChart:
    def __init__(self, rect: pygame.Rect, max_points: int = 240,
                 y_min: float = 0.0, y_max: float = 100.0,
                 bg_color=(20, 20, 30, 160),
                 grid_color=(60, 60, 80),
                 line_color=(0, 200, 255)):
        self.rect = rect
        # Максимальное количество точек, хранимых в истории
        self.max_points = max_points
        self.y_min = y_min
        self.y_max = y_max
        self.bg_color = bg_color
        self.grid_color = grid_color
        self.line_color = line_color
        # Толщина линии графика (может изменяться из вне)
        self.line_width = 2
        # Авто-масштабирование: при выходе за диапазон расширяем его с запасом
        self.auto_scale_on_overflow = True
        self.auto_scale_margin = 0.10  # 10% запаса
        # Исторические данные
        self.data = deque(maxlen=max_points)
        # Окно отображения: сколько точек показывать и смещение от правого края истории
        self.display_points = min(240, max_points)
        self.view_offset = 0  # 0 — следуем за последними точками; >0 — пролистано влево
        # начальное значение — середина диапазона
        self.last_value = (y_min + y_max) / 2
        # Абсолютный индекс последней добавленной точки (возрастает навсегда)
        self.abs_index = 0
        # таймер для управления частотой дискретизации
        self._accum = 0.0
        self.sample_interval = 0.12  # сек
        # параметры поведения
        self.step_min = -1.3
        self.step_max = 1.3
        self.inertia = 0.85
        self.mid_pull = 0.02
        # Минимальный пол (если задан), ниже которого значения не опускаются
        self.min_floor = None

    def set_rect(self, rect: pygame.Rect):
        self.rect = rect

    def push_value(self, value: float):
        # Применяем нижний пол, если задан
        if getattr(self, 'min_floor', None) is not None:
            value = max(self.min_floor, value)
        # При необходимости расширяем диапазон (только наружу), чтобы уместить значение
        if self.auto_scale_on_overflow:
            # Если значение ниже текущего минимума
            if value < self.y_min:
                # добавим запас относительно новой высоты диапазона
                # запас рассчитываем как процент от расстояния до текущего верха
                margin = (self.y_max - value) * self.auto_scale_margin
                self.y_min = value - margin
            # Если значение выше текущего максимума
            elif value > self.y_max:
                margin = (value - self.y_min) * self.auto_scale_margin
                self.y_max = value + margin

        # ограничиваем значение текущим (возможно расширенным) диапазоном
        clamped = max(self.y_min, min(self.y_max, value))
        self.data.append(clamped)
        self.last_value = clamped
        self.abs_index += 1

    def update(self, dt: float):
        # простой рандом-волк, чтобы не прыгало резко
        self._accum += dt
        while self._accum >= self.sample_interval:
            self._accum -= self.sample_interval
            step = random.uniform(self.step_min, self.step_max)
            inertia = self.inertia
            new_val = self.last_value * inertia + (self.last_value + step) * (1 - inertia)
            # легкий дрейф к середине
            mid = (self.y_min + self.y_max) / 2
            new_val = new_val * (1 - self.mid_pull) + mid * self.mid_pull
            # Применяем нижний пол
            if getattr(self, 'min_floor', None) is not None:
                new_val = max(self.min_floor, new_val)
            self.push_value(new_val)

    def clamp_view(self):
        # Максимально допустимое смещение так, чтобы осталось не меньше display_points видимых точек
        max_offset = max(0, len(self.data) - self.display_points)
        if self.view_offset < 0:
            self.view_offset = 0
        elif self.view_offset > max_offset:
            self.view_offset = max_offset

    def pan_by(self, points: int):
        # Положительное значение — пан влево (увеличиваем смещение)
        self.view_offset += int(points)
        self.clamp_view()

    def set_display_points(self, points: int):
        # Минимум 10 точек для корректной отрисовки
        self.display_points = max(10, min(self.max_points, int(points)))
        self.clamp_view()

    def draw(self, surface: pygame.Surface):
        # фон с альфой
        bg_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        bg_surf.fill(self.bg_color)
        surface.blit(bg_surf, self.rect)

        # сетка
        grid_lines = 4
        for i in range(grid_lines + 1):
            y = self.rect.top + i * (self.rect.height // grid_lines)
            pygame.draw.line(surface, self.grid_color, (self.rect.left, y), (self.rect.right, y), 1)

        # если недостаточно точек — выходим
        if len(self.data) < 2:
            return

        # нормализация точек по высоте
        y_range = max(1e-6, self.y_max - self.y_min)
        # Сколько точек отображаем сейчас
        vis_count = min(self.display_points, len(self.data))
        if vis_count < 2:
            return
        # Индексы окна данных с учётом смещения
        end_idx = len(self.data) - self.view_offset
        start_idx = max(0, end_idx - vis_count)
        # Шаг по X между видимыми точками
        step_x = self.rect.width / max(1, vis_count - 1)
        points = []
        # Рисуем окно слева направо
        for i, val in enumerate(list(self.data)[start_idx:end_idx]):
            x = self.rect.left + i * step_x
            # верх — max, низ — min
            norm = (val - self.y_min) / y_range
            y = self.rect.bottom - norm * self.rect.height
            # гарантируем, что точка остаётся в пределах прямоугольника графика по вертикали
            iy = int(max(self.rect.top, min(self.rect.bottom - 1, y)))
            points.append((int(x), iy))

        if len(points) >= 2:
            pygame.draw.lines(surface, self.line_color, False, points, self.line_width)


