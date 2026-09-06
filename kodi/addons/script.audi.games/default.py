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
        self.paddle = 820.0
        self.ball_x, self.ball_y = 960.0, 830.0
        self.vx, self.vy = 320.0, -430.0
        self.blocks = []
        self.add_box(0, 0, W, H, 'FF05070A')
        self.title = self.add_label('AUDI MULTIMEDIA INTERFACE  /  BREAKOUT', 100, 65, 1720, 75, 'FFFF6B00', 42)
        self.status = self.add_label('Drehen: bewegen   |   Drücken: Start/Pause   |   Zurück: Ende', 100, 910, 1720, 85, 'FFFFFFFF', 30)
        self.score_label = self.add_label('PUNKTE  0', 100, 160, 600, 60, 'FFFFFFFF', 30)
        self.add_box(100, 242, 1720, 5, 'FF8D99AE')
        self.add_box(100, 876, 1720, 5, 'FF8D99AE')
        self.paddle_view = self.add_box(int(self.paddle), 840, 280, 25, 'FFFF6B00')
        self.ball_view = self.add_box(948, 818, 24, 24, 'FFFFFFFF')
        colors = ('FFD90429', 'FFFF6B00', 'FF8D99AE', 'FFFFFFFF')
        for row in range(4):
            for col in range(9):
                x, y = 150 + col * 180, 280 + row * 85
                view = self.add_box(x, y, 155, 55, colors[row])
                self.blocks.append([x, y, True, view])

    def add_box(self, x, y, w, h, color):
        control = xbmcgui.ControlImage(int(x * self.scale_x), int(y * self.scale_y), max(1, int(w * self.scale_x)), max(1, int(h * self.scale_y)), WHITE, colorDiffuse=color)
        self.addControl(control)
        return control

    def add_label(self, value, x, y, w, h, color, size):
        # Kodi resolves the font name through the current skin.
        font = 'font45' if size >= 40 else 'font30_title'
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
                amount = -85 if key in LEFT else 85
                self.paddle = max(108, min(1532, self.paddle + amount))
            return
        if key in SELECT:
            if self.finished:
                self.reset()
            elif not self.started:
                self.started = True
                self.status.setLabel('Drehen: bewegen   |   Drücken: Pause   |   Zurück: Ende')
            else:
                self.paused = not self.paused
                self.status.setLabel('PAUSE  —  Drücken zum Fortsetzen' if self.paused else
                                     'Drehen: bewegen   |   Drücken: Pause   |   Zurück: Ende')

    def reset(self):
        self.score = 0
        self.score_label.setLabel('PUNKTE  0')
        self.ball_x, self.ball_y = 960.0, 830.0
        self.vx, self.vy = 320.0, -430.0
        self.paddle = 820.0
        self.started = True
        self.paused = self.finished = self.won = False
        for x, y, alive, view in self.blocks:
            view.setVisible(True)
        for block in self.blocks:
            block[2] = True
        self.status.setLabel('Drehen: bewegen   |   Drücken: Pause   |   Zurück: Ende')

    def tick(self, dt):
        self.paddle_view.setPosition(int(self.paddle * self.scale_x), int(840 * self.scale_y))
        if not self.started or self.paused or self.finished:
            return
        # Substeps reduce tunneling through the thin blocks on a busy Pi.
        steps = max(1, min(8, int(math.ceil(dt / 0.012))))
        for _ in range(steps):
            step = dt / steps
            old_y = self.ball_y
            self.ball_x += self.vx * step
            self.ball_y += self.vy * step
            if self.ball_x < 112:
                self.ball_x, self.vx = 112, abs(self.vx)
            if self.ball_x > 1808:
                self.ball_x, self.vx = 1808, -abs(self.vx)
            if self.ball_y < 260:
                self.ball_y, self.vy = 260, abs(self.vy)
            if self.vy > 0 and old_y <= 828 and self.ball_y >= 828 and self.paddle - 12 <= self.ball_x <= self.paddle + 292:
                self.ball_y = 828
                offset = max(-1, min(1, (self.ball_x - self.paddle - 140) / 140))
                self.vx = 490 * offset
                self.vy = -math.sqrt(max(80000, 490 * 490 - self.vx * self.vx))
            for block in self.blocks:
                x, y, alive, view = block
                if alive and x - 12 <= self.ball_x <= x + 167 and y - 12 <= self.ball_y <= y + 67:
                    block[2] = False
                    view.setVisible(False)
                    self.vy = -self.vy
                    self.score += 10
                    self.score_label.setLabel('PUNKTE  {}'.format(self.score))
                    break
            if self.ball_y > 880:
                self.finished = True
                self.status.setLabel('GAME OVER  —  Drücken für Neustart   |   Zurück: Ende')
                break
            if all(not b[2] for b in self.blocks):
                self.finished = self.won = True
                self.status.setLabel('GESCHAFFT!  —  Drücken für Neustart   |   Zurück: Ende')
                break
        self.ball_view.setPosition(int((self.ball_x - 12) * self.scale_x), int((self.ball_y - 12) * self.scale_y))


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
