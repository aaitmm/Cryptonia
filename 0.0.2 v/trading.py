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
        self.max_points = max_points
        self.y_min = y_min
        self.y_max = y_max
        self.bg_color = bg_color
        self.grid_color = grid_color
        self.line_color = line_color
        self.data = deque(maxlen=max_points)
        # начальное значение — середина диапазона
        self.last_value = (y_min + y_max) / 2
        # таймер для управления частотой дискретизации
        self._accum = 0.0
        self.sample_interval = 0.12  # сек
        # параметры поведения
        self.step_min = -1.3
        self.step_max = 1.3
        self.inertia = 0.85
        self.mid_pull = 0.02

    def set_rect(self, rect: pygame.Rect):
        self.rect = rect

    def push_value(self, value: float):
        # ограничиваем значение диапазоном
        clamped = max(self.y_min, min(self.y_max, value))
        self.data.append(clamped)
        self.last_value = clamped

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
            self.push_value(new_val)

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
        step_x = self.rect.width / max(1, self.max_points - 1)
        points = []
        # заполняем с правой стороны, чтобы график шёл слева направо
        start_x = self.rect.right - step_x * (len(self.data) - 1)
        for idx, val in enumerate(self.data):
            x = start_x + idx * step_x
            # верх — max, низ — min
            norm = (val - self.y_min) / y_range
            y = self.rect.bottom - norm * self.rect.height
            # гарантируем, что точка остаётся в пределах прямоугольника графика по вертикали
            iy = int(max(self.rect.top, min(self.rect.bottom - 1, y)))
            points.append((int(x), iy))

        if len(points) >= 2:
            pygame.draw.lines(surface, self.line_color, False, points, 2)

