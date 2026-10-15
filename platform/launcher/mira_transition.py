#!/usr/bin/env python3
"""Animated MIRA bridge between Plymouth and the automotive launcher."""
from collections import OrderedDict
from pathlib import Path
import sys

from PyQt5.QtCore import Qt, QElapsedTimer, QTimer
from PyQt5.QtGui import QPainter, QPixmap, QColor
from PyQt5.QtWidgets import QApplication, QWidget

FRAME_DIR = Path("/usr/share/plymouth/themes/mira")
READY = Path("/run/user/1000/mira-launcher-ready")
VISIBLE = Path("/run/user/1000/mira-transition-visible")
FRAME_COUNT = 156
FPS = 15


class MiraTransition(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setCursor(Qt.BlankCursor)

        self.clock = QElapsedTimer()
        self.clock.start()
        self.cache = OrderedDict()
        self.visible_signalled = False

        self.timer = QTimer(self)
        self.timer.setInterval(67)
        self.timer.timeout.connect(self.advance)
        self.timer.start()

    def frame(self, index):
        if index not in self.cache:
            pixmap = QPixmap(str(FRAME_DIR / f"frame-{index}.png"))
            if pixmap.isNull():
                return None
            self.cache[index] = pixmap
            while len(self.cache) > 6:
                self.cache.popitem(last=False)
        else:
            self.cache.move_to_end(index)
        return self.cache[index]

    def advance(self):
        if READY.exists():
            self.timer.stop()
            self.close()
            QApplication.quit()
            return
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#101419"))

        index = (self.clock.elapsed() * FPS // 1000) % FRAME_COUNT
        pixmap = self.frame(index)
        if pixmap is not None:
            painter.drawPixmap(self.rect(), pixmap)
        painter.end()

        if not self.visible_signalled:
            self.visible_signalled = True
            QTimer.singleShot(150, self.signal_visible)

    def signal_visible(self):
        if not READY.exists():
            VISIBLE.touch()


def main():
    app = QApplication(sys.argv)
    window = MiraTransition()
    window.showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
