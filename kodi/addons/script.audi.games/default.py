#!/usr/bin/env python3
"""Kodi-native games: 1920x1080 coordinates, no external GUI dependency."""
import math
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

def main():
    # Dialog.select uses Kodi's own focus/input navigation for the wheel.
    selected = xbmcgui.Dialog().select('AUDI Entertainment  /  Spiele', ['Breakout', 'Zurück'])
    if selected != 0:
        return
    window = GameWindow()
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
