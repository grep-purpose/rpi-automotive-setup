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
        self.paddle = 800.0
        self.ball_x, self.ball_y = 960.0, 805.0
        self.vx, self.vy = 320.0, -430.0
        self.blocks = []
        self.add_box(0, 0, W, H, 'FF05070A')
        self.title = self.add_label('AUDI ENTERTAINMENT  /  BREAKOUT', 100, 42, 1720, 95, 'FFFF6B00', 60)
        self.status = self.add_label('DREHEN Bewegen   |   DRÜCKEN Start/Pause   |   RETURN Ende', 100, 905, 1720, 105, 'FFFFFFFF', 45)
        self.score_label = self.add_label('PUNKTE  0', 100, 143, 700, 85, 'FFFFFFFF', 45)
        self.add_box(100, 242, 1720, 6, 'FF8D99AE')
        self.add_box(100, 876, 1720, 6, 'FF8D99AE')
        self.paddle_view = self.add_box(int(self.paddle), 835, 320, 35, 'FFFF6B00')
        self.ball_view = self.add_box(944, 789, 32, 32, 'FFFFFFFF')
        colors = ('FFD90429', 'FFFF6B00', 'FF8D99AE', 'FFFFFFFF')
        for row in range(4):
            for col in range(9):
                x, y = 150 + col * 180, 270 + row * 112
                view = self.add_box(x, y, 165, 85, colors[row])
                self.blocks.append([x, y, True, view])

    def add_box(self, x, y, w, h, color):
        control = xbmcgui.ControlImage(int(x * self.scale_x), int(y * self.scale_y), max(1, int(w * self.scale_x)), max(1, int(h * self.scale_y)), WHITE, colorDiffuse=color)
        self.addControl(control)
        return control

    def add_label(self, value, x, y, w, h, color, size):
        # Kodi resolves the font name through the current skin.
        font = 'font60' if size >= 60 else 'font45_title' if size >= 40 else 'font30_title'
        control = xbmcgui.ControlLabel(int(x * self.scale_x), int(y * self.scale_y), max(1, int(w * self.scale_x)), max(1, int(h * self.scale_y)), value, font=font, textColor=color)
        self.addControl(control)
        return control

    def onAction(self, action):
        key = action.getId()
        if key in BACK:
            self.closed = True
            return
        if key in LEFT or key in RIGHT:
            if not self.finished:
                amount = -100 if key in LEFT else 100
                self.paddle = max(108, min(1492, self.paddle + amount))
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

    def reset(self):
        self.score = 0
        self.score_label.setLabel('PUNKTE  0')
        self.ball_x, self.ball_y = 960.0, 805.0
        self.vx, self.vy = 320.0, -430.0
        self.paddle = 800.0
        self.started = True
        self.paused = self.finished = self.won = False
        for x, y, alive, view in self.blocks:
            view.setVisible(True)
        for block in self.blocks:
            block[2] = True
        self.status.setLabel('DREHEN Bewegen   |   DRÜCKEN Pause   |   RETURN Ende')

    def tick(self, dt):
        self.paddle_view.setPosition(int(self.paddle * self.scale_x), int(835 * self.scale_y))
        if not self.started or self.paused or self.finished:
            return
        # Substeps reduce tunneling through the thin blocks on a busy Pi.
        steps = max(1, min(8, int(math.ceil(dt / 0.012))))
        for _ in range(steps):
            step = dt / steps
            old_y = self.ball_y
            self.ball_x += self.vx * step
            self.ball_y += self.vy * step
            if self.ball_x < 116:
                self.ball_x, self.vx = 116, abs(self.vx)
            if self.ball_x > 1804:
                self.ball_x, self.vx = 1804, -abs(self.vx)
            if self.ball_y < 260:
                self.ball_y, self.vy = 260, abs(self.vy)
            if self.vy > 0 and old_y <= 819 and self.ball_y >= 819 and self.paddle - 16 <= self.ball_x <= self.paddle + 336:
                self.ball_y = 819
                offset = max(-1, min(1, (self.ball_x - self.paddle - 160) / 160))
                self.vx = 490 * offset
                self.vy = -math.sqrt(max(80000, 490 * 490 - self.vx * self.vx))
            for block in self.blocks:
                x, y, alive, view = block
                if alive and x - 16 <= self.ball_x <= x + 181 and y - 16 <= self.ball_y <= y + 101:
                    block[2] = False
                    view.setVisible(False)
                    self.vy = -self.vy
                    self.score += 10
                    self.score_label.setLabel('PUNKTE  {}'.format(self.score))
                    break
            if self.ball_y > 885:
                self.finished = True
                self.status.setLabel('GAME OVER   |   DRÜCKEN Neustart   |   RETURN Ende')
                break
            if all(not b[2] for b in self.blocks):
                self.finished = self.won = True
                self.status.setLabel('GESCHAFFT!   |   DRÜCKEN Neustart   |   RETURN Ende')
                break
        self.ball_view.setPosition(int((self.ball_x - 16) * self.scale_x), int((self.ball_y - 16) * self.scale_y))


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
