"""Short first-launch transition using the same frames as Plymouth."""
import os
from collections import OrderedDict
from PyQt5.QtCore import QElapsedTimer, QTimer, QRectF
from PyQt5.QtGui import QPixmap, QColor


class MiraSplash:
    def __init__(self, widget):
        self.widget = widget
        self.folder = os.path.join(os.path.dirname(__file__), '..', 'boot',
                                   'mira-animation', 'theme')
        self.clock = QElapsedTimer()
        self.cache = OrderedDict()
        self.active = os.environ.get('MIRA_DISABLE') != '1'
        self.timer = QTimer(widget)
        self.timer.timeout.connect(widget.update)
        if self.active and self.frame(0) is not None:
            self.timer.start(67)
        else:
            self.finish()

    def frame(self, index):
        if index not in self.cache:
            pix = QPixmap(os.path.join(self.folder, 'frame-%d.png' % index))
            if pix.isNull():
                return None
            self.cache[index] = pix
            while len(self.cache) > 6:
                self.cache.popitem(last=False)
        return self.cache[index]

    def finish(self):
        self.active = False
        self.timer.stop()
        self.cache.clear()

    def paint(self, painter):
        if not self.active:
            return
        if not self.clock.isValid():
            self.clock.start()
        elapsed = self.clock.elapsed()
        if elapsed >= 1200:
            self.finish()
            return
        pix = self.frame(int(elapsed * 15 / 1000) % 156)
        if pix is None:
            self.finish()
            return
        painter.save()
        painter.setOpacity(min(1.0, (1200 - elapsed) / 300.0))
        painter.drawPixmap(QRectF(0, 0, 800, 480), pix, QRectF(pix.rect()))
        painter.restore()
