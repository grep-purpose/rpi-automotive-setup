#!/usr/bin/env python3
"""Kodi-native games: 1920x1080 coordinates, no external GUI dependency."""
import math
import random
import os
import base64
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

W, H = 1920, 1080
WHITE = os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile')), 'white.png')
if not os.path.isfile(WHITE):
    os.makedirs(os.path.dirname(WHITE), exist_ok=True)
    with open(WHITE, 'wb') as image_file:
        image_file.write(base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP8//8/AwMDEwMDAwMDAwAkBgMB/DXemwAAAABJRU5ErkJggg=='))
LEFT = (1, 3)   # Kodi Left, Up (RNS-E wheel one)
RIGHT = (2, 4)  # Kodi Right, Down (RNS-E wheel two)
SELECT = (7,)
BACK = (9, 10, 92)


class GameWindow(xbmcgui.WindowDialog):
    """Breakout on a 1920x1080 design grid, fitted to Kodi's GUI window."""

    WALL_LEFT, WALL_RIGHT = 24, 1896
    BALL_RADIUS = 20
    PADDLE_Y = 870
    PADDLE_HEIGHT = 42
    PADDLE_START_WIDTH = 430
    PADDLE_MIN_WIDTH = 164
    PADDLE_STEP = 38
    BRICK_WIDTH, BRICK_HEIGHT = 194, 110

    def __init__(self):
        super().__init__()
        self.scale_x = self.getWidth() / W
        self.scale_y = self.getHeight() / H
        self.closed = False
        self.started = False
        self.paused = False
        self.finished = False
        self.won = False
        self.score = 0
        self.paddle_width = self.PADDLE_START_WIDTH
        self.paddle = (W - self.paddle_width) / 2
        self.ball_x, self.ball_y = W / 2, 835.0
        self.vx, self.vy = 320.0, -430.0
        self.blocks = []

        self.add_box(0, 0, W, H, 'FF05070A')
        self.title = self.add_label('AUDI ENTERTAINMENT  /  BREAKOUT', 30, 18, 1860, 92, 'FFFF6B00', 60)
        self.score_label = self.add_label('PUNKTE  0     STUFE  1', 30, 110, 1500, 75, 'FFFFFFFF', 45)
        self.add_box(30, 196, 1860, 6, 'FF8D99AE')
        self.add_box(30, 945, 1860, 6, 'FF8D99AE')
        self.status = self.add_label('DREHEN Bewegen   |   DRÜCKEN Start/Pause   |   RETURN Ende',
                                     30, 968, 1860, 100, 'FFFFFFFF', 45)
        self.paddle_view = self.add_box(int(self.paddle), self.PADDLE_Y,
                                        self.paddle_width, self.PADDLE_HEIGHT, 'FFFF6B00')
        self.ball_view = self.add_box(int(self.ball_x - self.BALL_RADIUS),
                                      int(self.ball_y - self.BALL_RADIUS),
                                      2 * self.BALL_RADIUS, 2 * self.BALL_RADIUS, 'FFFFFFFF')
        colors = ('FFD90429', 'FFFF6B00', 'FF8D99AE', 'FFFFFFFF')
        for row in range(4):
            for col in range(9):
                x, y = 30 + col * 208, 235 + row * 125
                view = self.add_box(x, y, self.BRICK_WIDTH, self.BRICK_HEIGHT, colors[row])
                self.blocks.append([x, y, True, view])

    def add_box(self, x, y, w, h, color):
        control = xbmcgui.ControlImage(int(x * self.scale_x), int(y * self.scale_y),
                                        max(1, int(w * self.scale_x)), max(1, int(h * self.scale_y)),
                                        WHITE, colorDiffuse=color)
        self.addControl(control)
        return control

    def add_label(self, value, x, y, w, h, color, size):
        font = 'font60' if size >= 60 else 'font45_title'
        control = xbmcgui.ControlLabel(int(x * self.scale_x), int(y * self.scale_y),
                                        max(1, int(w * self.scale_x)), max(1, int(h * self.scale_y)),
                                        value, font=font, textColor=color)
        self.addControl(control)
        return control

    def onAction(self, action):
        key = action.getId()
        if key in BACK:
            self.closed = True
            return
        if key in LEFT or key in RIGHT:
            if not self.finished:
                self.paddle += -110 if key in LEFT else 110
                self.clamp_paddle()
            return
        if key in SELECT:
            if self.finished:
                self.reset()
            elif not self.started:
                self.started = True
                self.status.setLabel('DREHEN Bewegen   |   DRÜCKEN Pause   |   RETURN Ende')
            else:
                self.paused = not self.paused
                self.status.setLabel('PAUSE   |   DRÜCKEN Weiter   |   RETURN Ende' if self.paused else
                                     'DREHEN Bewegen   |   DRÜCKEN Pause   |   RETURN Ende')

    def clamp_paddle(self):
        self.paddle = max(self.WALL_LEFT, min(self.WALL_RIGHT - self.paddle_width, self.paddle))

    def update_difficulty(self):
        # Shrink after 50, 100, ... points; keep the paddle centred while shrinking.
        new_width = max(self.PADDLE_MIN_WIDTH,
                        self.PADDLE_START_WIDTH - (self.score // 50) * self.PADDLE_STEP)
        if new_width != self.paddle_width:
            self.paddle += (self.paddle_width - new_width) / 2
            self.paddle_width = new_width
            self.clamp_paddle()
            self.paddle_view.setWidth(max(1, int(new_width * self.scale_x)))
        level = 1 + (self.PADDLE_START_WIDTH - new_width) // self.PADDLE_STEP
        self.score_label.setLabel('PUNKTE  {}     STUFE  {}'.format(self.score, level))

    def reset(self):
        self.score = 0
        self.paddle_width = self.PADDLE_START_WIDTH
        self.paddle = (W - self.paddle_width) / 2
        self.paddle_view.setWidth(max(1, int(self.paddle_width * self.scale_x)))
        self.ball_x, self.ball_y = W / 2, 835.0
        self.vx, self.vy = 320.0, -430.0
        self.started = True
        self.paused = self.finished = self.won = False
        for block in self.blocks:
            block[2] = True
            block[3].setVisible(True)
        self.update_difficulty()
        self.ball_view.setPosition(int((self.ball_x - self.BALL_RADIUS) * self.scale_x),
                                   int((self.ball_y - self.BALL_RADIUS) * self.scale_y))
        self.status.setLabel('DREHEN Bewegen   |   DRÜCKEN Pause   |   RETURN Ende')

    def tick(self, dt):
        self.paddle_view.setPosition(int(self.paddle * self.scale_x), int(self.PADDLE_Y * self.scale_y))
        if not self.started or self.paused or self.finished:
            return
        steps = max(1, min(8, int(math.ceil(dt / 0.012))))
        for _ in range(steps):
            step = dt / steps
            old_y = self.ball_y
            self.ball_x += self.vx * step
            self.ball_y += self.vy * step
            if self.ball_x < self.WALL_LEFT + self.BALL_RADIUS:
                self.ball_x, self.vx = self.WALL_LEFT + self.BALL_RADIUS, abs(self.vx)
            if self.ball_x > self.WALL_RIGHT - self.BALL_RADIUS:
                self.ball_x, self.vx = self.WALL_RIGHT - self.BALL_RADIUS, -abs(self.vx)
            if self.ball_y < 216:
                self.ball_y, self.vy = 216, abs(self.vy)
            hit_y = self.PADDLE_Y - self.BALL_RADIUS
            if (self.vy > 0 and old_y <= hit_y <= self.ball_y and
                    self.paddle - self.BALL_RADIUS <= self.ball_x <=
                    self.paddle + self.paddle_width + self.BALL_RADIUS):
                self.ball_y = hit_y
                offset = max(-1, min(1, (self.ball_x - self.paddle - self.paddle_width / 2)
                                       / (self.paddle_width / 2)))
                self.vx = 490 * offset
                self.vy = -math.sqrt(max(80000, 490 * 490 - self.vx * self.vx))
            for block in self.blocks:
                x, y, alive, view = block
                if (alive and x - self.BALL_RADIUS <= self.ball_x <= x + self.BRICK_WIDTH + self.BALL_RADIUS
                        and y - self.BALL_RADIUS <= self.ball_y <= y + self.BRICK_HEIGHT + self.BALL_RADIUS):
                    block[2] = False
                    view.setVisible(False)
                    self.vy = -self.vy
                    self.score += 10
                    self.update_difficulty()
                    break
            if self.ball_y > 955:
                self.finished = True
                self.status.setLabel('GAME OVER   |   DRÜCKEN Neustart   |   RETURN Ende')
                break
            if all(not b[2] for b in self.blocks):
                self.finished = self.won = True
                self.status.setLabel('GESCHAFFT!   |   DRÜCKEN Neustart   |   RETURN Ende')
                break
        self.ball_view.setPosition(int((self.ball_x - self.BALL_RADIUS) * self.scale_x),
                                   int((self.ball_y - self.BALL_RADIUS) * self.scale_y))

class LaneRunnerWindow(xbmcgui.WindowDialog):
    """Three-lane arcade game with a lightweight perspective effect."""

    def __init__(self):
        super().__init__()
        self.sx, self.sy = self.getWidth() / W, self.getHeight() / H
        self.rng = random.Random()
        self.closed = self.started = self.paused = self.finished = False
        self.lane = 1
        self.score = 0
        self.spawn_elapsed = 0.0
        self.obstacles = []
        self.image(0, 0, W, H, 'road.png')
        self.label('AUDI ENTERTAINMENT  /  LANE RUNNER', 30, 18, 1850, 92, 'FFFF6B00', 'font60')
        self.score_label = self.label('PUNKTE  0', 30, 110, 1100, 75, 'FFFFFFFF', 'font45_title')
        self.box(30, 195, 1860, 6, 'FF8D99AE')
        self.box(30, 940, 1860, 6, 'FF8D99AE')
        self.status = self.label('DREHEN Spur wechseln  |  DRÜCKEN Start/Pause  |  RETURN Ende',
                                 30, 962, 1860, 105, 'FFFFFFFF', 'font45_title')
        self.player_visual_x = self.lane_center(self.lane, 1.0)
        self.player = self.make_car('player.png')
        for index in range(8):
            sprite = ('traffic_red.png', 'traffic_blue.png', 'traffic_silver.png')[index % 3]
            parts = self.make_car(sprite)
            self.set_car(parts, 960, 270, 55, 70, False)
            self.obstacles.append({'lane': 1, 'depth': 0.0, 'active': False, 'parts': parts})
        self.set_car(self.player, self.lane_center(self.lane, 1.0), 830, 150, 170, True)

    def box(self, x, y, width, height, color):
        control = xbmcgui.ControlImage(int(x * self.sx), int(y * self.sy),
                                        max(1, int(width * self.sx)), max(1, int(height * self.sy)),
                                        WHITE, colorDiffuse=color)
        self.addControl(control)
        return control

    def label(self, value, x, y, width, height, color, font):
        control = xbmcgui.ControlLabel(int(x * self.sx), int(y * self.sy),
                                        int(width * self.sx), int(height * self.sy),
                                        value, font=font, textColor=color)
        self.addControl(control)
        return control

    def image(self, x, y, width, height, filename):
        path = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'media', filename)
        control = xbmcgui.ControlImage(int(x * self.sx), int(y * self.sy),
                                        max(1, int(width * self.sx)), max(1, int(height * self.sy)), path)
        self.addControl(control)
        return control

    def make_car(self, sprite):
        return self.image(0, 0, 10, 10, sprite)

    def set_car(self, control, cx, cy, width, height, visible):
        control.setPosition(int((cx - width / 2) * self.sx), int((cy - height / 2) * self.sy))
        control.setWidth(max(1, int(width * self.sx)))
        control.setHeight(max(1, int(height * self.sy)))
        control.setVisible(visible)

    @staticmethod
    def lane_center(lane, depth):
        # Use the car's actual screen height to follow the straight lane in road.png.
        # The road widens linearly from 490 px at y=224 to 1760 px at y=944.
        depth = max(0.0, min(1.0, depth))
        car_y = 285 + 550 * depth * depth
        road_t = max(0.0, min(1.0, (car_y - 224) / 720))
        road_width = 490 + 1270 * road_t
        return W / 2 + (lane - 1) * road_width / 3

    def onAction(self, action):
        key = action.getId()
        if key in BACK:
            self.closed = True
        elif key in LEFT or key in RIGHT:
            if not self.finished:
                self.lane = max(0, min(2, self.lane + (-1 if key in LEFT else 1)))
        elif key in SELECT:
            if self.finished:
                self.reset()
            elif not self.started:
                self.started = True
                self.status.setLabel('DREHEN Spur wechseln  |  DRÜCKEN Pause  |  RETURN Ende')
            else:
                self.paused = not self.paused
                self.status.setLabel('PAUSE  |  DRÜCKEN Weiter  |  RETURN Ende' if self.paused else
                                     'DREHEN Spur wechseln  |  DRÜCKEN Pause  |  RETURN Ende')

    def reset(self):
        self.lane = 1
        self.score = 0
        self.spawn_elapsed = 0.0
        self.started, self.paused, self.finished = True, False, False
        self.score_label.setLabel('PUNKTE  0')
        self.status.setLabel('DREHEN Spur wechseln  |  DRÜCKEN Pause  |  RETURN Ende')
        self.player_visual_x = self.lane_center(self.lane, 1.0)
        self.set_car(self.player, self.player_visual_x, 830, 150, 170, True)
        for car in self.obstacles:
            car['active'] = False
            self.set_car(car['parts'], 960, 270, 55, 70, False)

    def spawn(self):
        for car in self.obstacles:
            if not car['active']:
                car['active'] = True
                car['lane'] = self.rng.randrange(3)
                car['depth'] = 0.0
                return

    def tick(self, dt):
        target_x = self.lane_center(self.lane, 1.0)
        self.player_visual_x += (target_x - self.player_visual_x) * min(1.0, dt * 10.0)
        self.set_car(self.player, self.player_visual_x, 830, 150, 170, True)
        if not self.started or self.paused or self.finished:
            return
        self.spawn_elapsed += dt
        interval = max(0.85, 1.50 - self.score * .0012)
        if self.spawn_elapsed >= interval:
            self.spawn_elapsed -= interval
            self.spawn()
        speed = min(.56, .30 + self.score * .00055)
        for car in self.obstacles:
            if not car['active']:
                continue
            car['depth'] += speed * dt
            depth = car['depth']
            if depth >= .87 and car['lane'] == self.lane:
                self.finished = True
                self.status.setLabel('GAME OVER  |  DRÜCKEN Neustart  |  RETURN Ende')
                break
            if depth >= 1.04:
                car['active'] = False
                self.set_car(car['parts'], 960, 270, 55, 70, False)
                self.score += 10
                self.score_label.setLabel('PUNKTE  {}'.format(self.score))
                continue
            size = min(1.0, depth)
            width, height = 48 + 108 * size, 65 + 105 * size
            cy = 285 + 550 * size * size
            self.set_car(car['parts'], self.lane_center(car['lane'], size), cy,
                         width, height, True)

class RooftopRunnerWindow(xbmcgui.WindowDialog):
    """Automatic runner: turn only at a visible corner, jump over gaps/barriers."""

    EVENTS = ('right', 'gap', 'left', 'barrier')
    JUMP_TIME = 0.92

    def __init__(self):
        super().__init__()
        self.sx, self.sy = self.getWidth() / W, self.getHeight() / H
        self.closed = self.started = self.finished = False
        self.rng = random.Random()
        self.scenes = {}
        self.scene_name = None
        self.scenes['straight'] = self.image('runner_straight.png', 0, 0, W, H)
        for direction in ('left', 'right'):
            for frame in range(5):
                key = '{}_{}'.format(direction, frame)
                self.scenes[key] = self.image('runner_{}_{}.png'.format(direction, frame), 0, 0, W, H)
        for view in self.scenes.values():
            view.setVisible(False)
        self.title = self.label('AUDI ENTERTAINMENT  /  ROOFTOP RUNNER',
                                30, 18, 1860, 92, 'FFFF6B00', 'font60')
        self.score_label = self.label('PUNKTE  0', 30, 110, 1200, 80,
                                      'FFFFFFFF', 'font45_title')
        self.status = self.label('DREHEN Abbiegen  |  DRÜCKEN Springen  |  RETURN Ende',
                                 30, 962, 1860, 105, 'FFFFFFFF', 'font45_title')
        self.hazards = {
            'gap': self.image('runner_gap.png', 0, 0, 40, 20),
            'barrier': self.image('runner_barrier.png', 0, 0, 40, 20),
        }
        for view in self.hazards.values():
            view.setVisible(False)
        self.player = self.image('runner_player.png', 887, 755, 146, 180)
        self.reset(started=False)

    def image(self, filename, x, y, width, height):
        path = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'media', filename)
        control = xbmcgui.ControlImage(int(x * self.sx), int(y * self.sy),
                                        max(1, int(width * self.sx)), max(1, int(height * self.sy)), path)
        self.addControl(control)
        return control

    def label(self, value, x, y, width, height, color, font):
        control = xbmcgui.ControlLabel(int(x * self.sx), int(y * self.sy),
                                        int(width * self.sx), int(height * self.sy),
                                        value, font=font, textColor=color)
        self.addControl(control)
        return control

    def show_scene(self, name):
        if name == self.scene_name:
            return
        if self.scene_name is not None:
            self.scenes[self.scene_name].setVisible(False)
        self.scenes[name].setVisible(True)
        self.scene_name = name

    def reset(self, started=True):
        self.started, self.finished = started, False
        self.score = 0
        self.event_index = 0
        self.event = self.EVENTS[0]
        self.progress = 0.0
        self.rest = 0.0
        self.turn_cooldown = 0.0
        self.jump_age = None
        self.score_label.setLabel('PUNKTE  0')
        self.status.setLabel('DREHEN Abbiegen  |  DRÜCKEN Springen  |  RETURN Ende' if started else
                             'DRÜCKEN Start  |  DREHEN Abbiegen  |  RETURN Ende')
        for view in self.hazards.values():
            view.setVisible(False)
        self.player.setPosition(int(887 * self.sx), int(755 * self.sy))
        self.show_scene('right_0')

    def fail(self, reason):
        self.finished = True
        self.status.setLabel('{}  |  DRÜCKEN Neustart  |  RETURN Ende'.format(reason))

    def next_event(self, turned=False):
        self.score += 10
        self.score_label.setLabel('PUNKTE  {}'.format(self.score))
        self.event_index += 1
        self.event = (self.EVENTS[self.event_index] if self.event_index < len(self.EVENTS)
                      else self.rng.choice(self.EVENTS))
        self.progress = 0.0
        self.rest = 0.55
        self.turn_cooldown = 0.28 if turned else 0.0
        for view in self.hazards.values():
            view.setVisible(False)
        self.show_scene('straight' if self.event in self.hazards else '{}_0'.format(self.event))

    def onAction(self, action):
        key = action.getId()
        if key in BACK:
            self.closed = True
        elif key in SELECT:
            if self.finished:
                self.reset()
            elif not self.started:
                self.started = True
                self.status.setLabel('DREHEN Abbiegen  |  DRÜCKEN Springen  |  RETURN Ende')
            elif self.jump_age is None:
                self.jump_age = 0.0
        elif key in LEFT or key in RIGHT:
            if not self.started or self.finished or self.turn_cooldown > 0:
                return
            direction = 'left' if key in LEFT else 'right'
            if self.event not in ('left', 'right') or self.rest > 0 or self.progress < 0.76:
                self.fail('ZU FRÜH GEDREHT')
            elif direction != self.event:
                self.fail('FALSCHE RICHTUNG')
            elif self.progress < 1.0:
                self.next_event(turned=True)
            else:
                self.fail('KURVE VERPASST')

    def tick(self, dt):
        if not self.started or self.finished:
            return
        self.turn_cooldown = max(0.0, self.turn_cooldown - dt)
        jump_height = 0.0
        if self.jump_age is not None:
            self.jump_age += dt
            if self.jump_age >= self.JUMP_TIME:
                self.jump_age = None
            else:
                jump_height = 140 * math.sin(math.pi * self.jump_age / self.JUMP_TIME)
        self.player.setPosition(int(887 * self.sx), int((755 - jump_height) * self.sy))
        if self.rest > 0:
            self.rest = max(0.0, self.rest - dt)
            return
        duration = max(3.25, 4.6 - self.score * .012)
        self.progress += dt / duration
        if self.event in ('left', 'right'):
            frame = min(4, int(self.progress * 5))
            self.show_scene('{}_{}'.format(self.event, frame))
            if self.progress >= 1.0:
                self.fail('KURVE VERPASST')
        else:
            view = self.hazards[self.event]
            z = min(1.0, self.progress)
            y = 280 + 540 * z ** 1.5
            width = (250 + 1450 * z) if self.event == 'gap' else (110 + 550 * z)
            height = (35 + 115 * z) if self.event == 'gap' else (65 + 130 * z)
            view.setPosition(int((W - width) / 2 * self.sx), int((y - height / 2) * self.sy))
            view.setWidth(max(1, int(width * self.sx)))
            view.setHeight(max(1, int(height * self.sy)))
            view.setVisible(True)
            if self.progress >= 1.0:
                if jump_height >= 50:
                    self.next_event()
                else:
                    self.fail('NICHT GESPRUNGEN')

class TorwandWindow(xbmcgui.WindowDialog):
    """Six alternating targets, with visible sway and accuracy-based scoring."""

    SHOTS = 6
    HOLES = ((710, 390), (1210, 650))
    PAGE_UP, PAGE_DOWN = 5, 6
    RADII = (105, 88, 70)
    SWAY = (24, 68, 108)

    def __init__(self):
        super().__init__()
        self.sx, self.sy = self.getWidth() / W, self.getHeight() / H
        self.closed = False
        self.aim_x, self.aim_y = 960, 520
        self.shots = self.hits = 0
        self.points = self.streak = 0
        self.phase = 0.0
        self.flight = None
        self.image('torwand_background.png', 0, 0, W, H)
        self.title = self.label('AUDI ENTERTAINMENT  /  TORWANDSCHIESSEN',
                                30, 18, 1860, 92, 'FFFF6B00', 'font60')
        self.score_label = self.label('', 30, 100, 1270, 86, 'FFFFFFFF', 'font45_title')
        self.target_label = self.label('', 1300, 100, 600, 86, 'FF72F0CF', 'font45_title')
        self.status = self.label('DREHEN Links/Rechts  |  STEUERKREUZ Hoch/Runter  |  DRÜCKEN Schuss',
                                 30, 966, 1860, 103, 'FFFFFFFF', 'font45_title')
        self.target_ring = self.image('torwand_target.png', 0, 0, 230, 230)
        self.marker = [self.box(0, 0, 12, 55, 'FFFF6B00') for _ in range(4)]
        self.ball = self.image('torwand_ball.png', 915, 820, 90, 90)
        self.ball.setVisible(False)
        self.update_hud()
        self.update_target()
        self.update_marker()

    def image(self, filename, x, y, width, height):
        path = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'media', filename)
        control = xbmcgui.ControlImage(int(x * self.sx), int(y * self.sy),
                                        max(1, int(width * self.sx)), max(1, int(height * self.sy)), path)
        self.addControl(control)
        return control

    def box(self, x, y, width, height, color):
        control = xbmcgui.ControlImage(int(x * self.sx), int(y * self.sy),
                                        max(1, int(width * self.sx)), max(1, int(height * self.sy)),
                                        WHITE, colorDiffuse=color)
        self.addControl(control)
        return control

    def label(self, value, x, y, width, height, color, font):
        control = xbmcgui.ControlLabel(int(x * self.sx), int(y * self.sy),
                                        int(width * self.sx), int(height * self.sy),
                                        value, font=font, textColor=color)
        self.addControl(control)
        return control

    def update_marker(self):
        x, y = self.aim_position()
        segments = ((x-7, y-65, 14, 42), (x-7, y+23, 14, 42),
                    (x-65, y-7, 42, 14), (x+23, y-7, 42, 14))
        for control, (px, py, width, height) in zip(self.marker, segments):
            control.setPosition(int(px * self.sx), int(py * self.sy))
            control.setWidth(max(1, int(width * self.sx)))
            control.setHeight(max(1, int(height * self.sy)))

    def stage(self):
        return min(2, self.shots // 2)

    def aim_position(self):
        amplitude = self.SWAY[self.stage()]
        # Two different periods make the marker drift without sudden jumps.
        return (self.aim_x + amplitude * math.sin(self.phase * 2.1),
                self.aim_y + amplitude * 0.75 * math.sin(self.phase * 2.9 + 1.1))

    def update_target(self):
        hole = self.HOLES[self.shots % 2]
        radius = self.RADII[self.stage()]
        self.target_ring.setPosition(int((hole[0] - radius) * self.sx),
                                     int((hole[1] - radius) * self.sy))
        self.target_ring.setWidth(max(1, int(2 * radius * self.sx)))
        self.target_ring.setHeight(max(1, int(2 * radius * self.sy)))
        self.target_label.setLabel('ZIEL  ' + ('OBEN LINKS' if self.shots % 2 == 0 else 'UNTEN RECHTS'))

    def update_hud(self):
        self.score_label.setLabel('PUNKTE  {}   TREFFER  {}/6   SCHUSS  {}/6'.format(
            self.points, self.hits, min(self.SHOTS, self.shots + 1)))

    def reset(self):
        self.aim_x, self.aim_y = 960, 520
        self.shots = self.hits = 0
        self.points = self.streak = 0
        self.phase = 0.0
        self.flight = None
        self.ball.setVisible(False)
        self.target_ring.setVisible(True)
        self.update_hud()
        self.update_target()
        self.status.setLabel('DREHEN Links/Rechts  |  STEUERKREUZ Hoch/Runter  |  DRÜCKEN Schuss')
        self.update_marker()

    def onAction(self, action):
        key = action.getId()
        if key in BACK:
            self.closed = True
            return
        if self.flight is not None:
            return
        if key in SELECT:
            if self.shots >= self.SHOTS:
                self.reset()
            else:
                x, y = self.aim_position()
                self.flight = {'time': 0.0, 'x': x, 'y': y,
                               'target': self.HOLES[self.shots % 2],
                               'radius': self.RADII[self.stage()]}
                self.ball.setVisible(True)
            return
        if self.shots >= self.SHOTS:
            return
        if key in LEFT:
            self.aim_x = max(570, self.aim_x - 80)
            note = 'LINKS erkannt'
        elif key in RIGHT:
            self.aim_x = min(1350, self.aim_x + 80)
            note = 'RECHTS erkannt'
        elif key == self.PAGE_UP:
            self.aim_y = max(310, self.aim_y - 65)
            note = 'OBEN erkannt'
        elif key == self.PAGE_DOWN:
            self.aim_y = min(730, self.aim_y + 65)
            note = 'UNTEN erkannt'
        else:
            return
        self.update_marker()
        self.status.setLabel(note + '  |  DRÜCKEN zum Schießen  |  RETURN Ende')

    def tick(self, dt):
        if self.flight is None:
            if self.shots < self.SHOTS:
                self.phase += max(0.0, dt)
                self.update_marker()
            return
        self.flight['time'] += dt
        t = min(1.0, self.flight['time'] / 0.72)
        easing = t * t * (3 - 2 * t)
        x = 960 + (self.flight['x'] - 960) * easing
        y = 865 + (self.flight['y'] - 865) * easing
        size = int(100 - 66 * t)
        self.ball.setPosition(int((x - size/2) * self.sx), int((y - size/2) * self.sy))
        self.ball.setWidth(max(1, int(size * self.sx)))
        self.ball.setHeight(max(1, int(size * self.sy)))
        if t < 1.0:
            return
        self.ball.setVisible(False)
        x, y = self.flight['x'], self.flight['y']
        hx, hy = self.flight['target']
        radius = self.flight['radius']
        distance = math.hypot(x - hx, y - hy)
        hit = distance <= radius
        self.hits += int(hit)
        self.streak = self.streak + 1 if hit else 0
        earned = (int(50 + 50 * (1 - distance / radius)) +
                  20 * (self.streak - 1)) if hit else 0
        self.points += earned
        self.shots += 1
        self.flight = None
        self.update_hud()
        if self.shots >= self.SHOTS:
            self.target_ring.setVisible(False)
            self.status.setLabel('RUNDE ENDE: {} TREFFER, {} PUNKTE  |  DRÜCKEN Neustart'.format(
                self.hits, self.points))
        else:
            self.aim_x, self.aim_y = 960, 520
            self.update_target()
            self.update_marker()
            self.status.setLabel(('TREFFER! +{} PUNKTE'.format(earned) if hit else 'DANEBEN') +
                                 '  |  NÄCHSTES ZIEL  |  DRÜCKEN Schuss')

def main():
    # Dialog.select uses Kodi's own focus/input navigation for the wheel.
    selected = xbmcgui.Dialog().select('AUDI Entertainment  /  Spiele', ['Breakout', 'Lane Runner', 'Rooftop Runner', 'Torwandschießen', 'Zurück'])
    if selected not in (0, 1, 2, 3):
        return
    window = (GameWindow() if selected == 0 else
              LaneRunnerWindow() if selected == 1 else
              RooftopRunnerWindow() if selected == 2 else TorwandWindow())
    monitor = xbmc.Monitor()
    try:
        window.show()
        previous = time.monotonic()
        while not window.closed and not monitor.abortRequested():
            now = time.monotonic()
            window.tick(min(now - previous, 0.05))
            previous = now
            if monitor.waitForAbort(0.033):
                break
    finally:
        window.close()
        del window


if __name__ == '__main__':
    main()
