#!/usr/bin/env python3

import os
import sys
import subprocess
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
)
from PyQt5.QtWidgets import (
    QApplication,
    QOpenGLWidget,
)


# ============================================================
# Pfade
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

HUDIY_SCRIPT = os.path.join(
    BASE_DIR,
    "launch_hudiy.sh"
)

KODI_SCRIPT = os.path.join(
    BASE_DIR,
    "launch_kodi.sh"
)


# ============================================================
# Farben
# ============================================================

BACKGROUND = QColor(
    8, 8, 8
)

PANEL = QColor(
    22, 22, 22
)

PANEL_SELECTED = QColor(
    30, 30, 30
)

PANEL_BORDER = QColor(
    65, 65, 65
)

AUDI_ORANGE = QColor(
    255, 107, 0
)

TEXT_WHITE = QColor(
    240, 242, 245
)

TEXT_MUTED = QColor(
    141, 153, 174
)

LINE_WHITE = QColor(
    255, 255, 255, 155
)


# ============================================================
# Menüeinträge
# ============================================================

OPTIONS = [
    {
        "title": "Android Auto",
        "type": "android",
        "script": HUDIY_SCRIPT,
    },
    {
        "title": "Medien",
        "type": "media",
        "script": KODI_SCRIPT,
    },
]


class AudiLauncher(QOpenGLWidget):

    def __init__(self):
        super().__init__()

        self.selected = 0
        self.launching = False

        self.setFixedSize(
            800,
            480
        )

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )

        # Cursor im Launcher unsichtbar
        self.setCursor(
            Qt.BlankCursor
        )

        self.setFocusPolicy(
            Qt.StrongFocus
        )

        self.setFocus()

        # Uhr aktualisieren
        self.clock_timer = QTimer(self)

        self.clock_timer.timeout.connect(
            self.update
        )

        self.clock_timer.start(
            1000
        )


    # ========================================================
    # OpenGL
    # ========================================================

    def initializeGL(self):

        print(
            "OpenGL context:",
            self.context().isValid(),
            flush=True
        )

        print(
            "Launcher resolution: 800x480",
            flush=True
        )


    # ========================================================
    # Hauptzeichnung
    # ========================================================

    def paintGL(self):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        # Tiefschwarzer Audi-Hintergrund
        painter.fillRect(
            0,
            0,
            800,
            480,
            BACKGROUND
        )

        self.draw_header(
            painter
        )

        self.draw_option(
            painter,
            index=0,
            x=32,
            y=102,
            width=354,
            height=286
        )

        self.draw_option(
            painter,
            index=1,
            x=414,
            y=102,
            width=354,
            height=286
        )

        self.draw_footer(
            painter
        )

        painter.end()


    # ========================================================
    # HEADER
    # ========================================================

    def draw_header(
        self,
        painter
    ):

        # Große Überschrift
        painter.setPen(
            TEXT_WHITE
        )

        font = QFont(
            "DejaVu Sans",
            22
        )

        font.setBold(
            True
        )

        painter.setFont(
            font
        )

        painter.drawText(
            38,
            12,
            724,
            48,
            Qt.AlignLeft | Qt.AlignVCenter,
            "Audi Multimedia Interface"
        )

        # Weiße Linie direkt unter dem Header
        painter.setPen(
            QPen(
                LINE_WHITE,
                2
            )
        )

        painter.drawLine(
            17,
            72,
            783,
            72
        )


    # ========================================================
    # KACHELN
    # ========================================================

    def draw_option(
        self,
        painter,
        index,
        x,
        y,
        width,
        height
    ):

        selected = (
            index == self.selected
        )

        option = OPTIONS[
            index
        ]

        # Hintergrund
        painter.fillRect(
            x,
            y,
            width,
            height,
            PANEL_SELECTED
            if selected
            else PANEL
        )

        # Rahmen
        painter.setPen(
            QPen(
                AUDI_ORANGE
                if selected
                else PANEL_BORDER,

                5
                if selected
                else 1
            )
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawRect(
            x,
            y,
            width,
            height
        )

        centre_x = (
            x + width // 2
        )

        # Symbolposition
        icon_y = (
            y + 105
        )

        if option["type"] == "android":

            self.draw_phone_icon(
                painter,
                centre_x,
                icon_y,
                selected
            )

        elif option["type"] == "media":

            self.draw_media_icon(
                painter,
                centre_x,
                icon_y,
                selected
            )

        # Titel
        painter.setPen(
            TEXT_WHITE
        )

        title_font = QFont(
            "DejaVu Sans",
            20
        )

        title_font.setBold(
            True
        )

        painter.setFont(
            title_font
        )

        painter.drawText(
            x + 10,
            y + 205,
            width - 20,
            54,
            Qt.AlignCenter,
            option["title"]
        )


    # ========================================================
    # Android-Auto-Symbol
    # ========================================================

    def draw_phone_icon(
        self,
        painter,
        cx,
        cy,
        selected
    ):

        color = (
            AUDI_ORANGE
            if selected
            else TEXT_MUTED
        )

        painter.setPen(
            QPen(
                color,
                4
            )
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawRoundedRect(
            cx - 31,
            cy - 53,
            62,
            106,
            7,
            7
        )

        painter.drawLine(
            cx - 11,
            cy + 39,
            cx + 11,
            cy + 39
        )


    # ========================================================
    # Medien-Symbol
    # ========================================================

    def draw_media_icon(
        self,
        painter,
        cx,
        cy,
        selected
    ):

        color = (
            AUDI_ORANGE
            if selected
            else TEXT_MUTED
        )

        painter.setPen(
            QPen(
                color,
                4
            )
        )

        painter.setBrush(
            Qt.NoBrush
        )

        points = [
            QPoint(
                cx - 38,
                cy - 52
            ),
            QPoint(
                cx - 38,
                cy + 52
            ),
            QPoint(
                cx + 48,
                cy
            ),
        ]

        painter.drawPolygon(
            *points
        )


    # ========================================================
    # KODI-ARTIGER FOOTER
    # ========================================================

    def draw_footer(
        self,
        painter
    ):

        # Kodi-Skin:
        # Footer links/rechts eingerückt
        # weiße kräftige Trennlinie
        # große helle Typografie

        footer_left = 17
        footer_right = 783

        line_y = 414

        # Weiße Trennlinie
        painter.setPen(
            QPen(
                LINE_WHITE,
                3
            )
        )

        painter.drawLine(
            footer_left,
            line_y,
            footer_right,
            line_y
        )

        # Aktuelle Uhrzeit
        current_time = datetime.now().strftime(
            "%H:%M"
        )

        painter.setPen(
            TEXT_WHITE
        )

        clock_font = QFont(
            "DejaVu Sans",
            22
        )

        clock_font.setBold(
            True
        )

        painter.setFont(
            clock_font
        )

        # Bewusst nur Uhrzeit.
        # Wetter folgt erst später über Kodi.
        painter.drawText(
            0,
            425,
            800,
            43,
            Qt.AlignCenter |
            Qt.AlignVCenter,
            current_time
        )


    # ========================================================
    # Eingabe
    # ========================================================

    def keyPressEvent(
        self,
        event
    ):

        if self.launching:
            return

        key = event.key()

        print(
            "KEY:",
            key,
            event.text(),
            flush=True
        )


        # ----------------------------------------------------
        # LINKS
        #
        # RNS-E Drehknopf links:
        # Key 49 / "1"
        # ----------------------------------------------------

        if key in (
            Qt.Key_Left,
            Qt.Key_Up,
            Qt.Key_1
        ):

            self.selected -= 1

            if self.selected < 0:
                self.selected = (
                    len(OPTIONS) - 1
                )

            self.update()

            return


        # ----------------------------------------------------
        # RECHTS
        #
        # RNS-E Drehknopf rechts:
        # Key 50 / "2"
        # ----------------------------------------------------

        if key in (
            Qt.Key_Right,
            Qt.Key_Down,
            Qt.Key_Tab,
            Qt.Key_2
        ):

            self.selected += 1

            if self.selected >= len(
                OPTIONS
            ):
                self.selected = 0

            self.update()

            return


        # ----------------------------------------------------
        # AUSWÄHLEN
        # ----------------------------------------------------

        if key in (
            Qt.Key_Return,
            Qt.Key_Enter,
            Qt.Key_Space
        ):

            self.launch_selected()

            return


        # ----------------------------------------------------
        # ESCAPE
        # ----------------------------------------------------

        if key == Qt.Key_Escape:

            QApplication.quit()


    # ========================================================
    # Anwendung starten
    # ========================================================

    def launch_selected(
        self
    ):

        self.launching = True

        option = OPTIONS[
            self.selected
        ]

        script = option[
            "script"
        ]

        print(
            "Starting:",
            option["title"],
            flush=True
        )

        self.hide()

        QApplication.processEvents()

        try:

            subprocess.run(
                [script],
                check=False
            )

        except Exception as exc:

            print(
                "Launch error:",
                exc,
                flush=True
            )

        # Nach Beenden wieder zum Launcher
        self.showFullScreen()

        self.raise_()

        self.activateWindow()

        self.setFocus()

        self.launching = False

        self.update()


def main():

    app = QApplication(
        sys.argv
    )

    # Cursor zusätzlich global verstecken
    QApplication.setOverrideCursor(
        Qt.BlankCursor
    )

    print(
        "Qt platform:",
        app.platformName(),
        flush=True
    )

    launcher = AudiLauncher()

    launcher.showFullScreen()

    launcher.setFocus()

    sys.exit(
        app.exec_()
    )


if __name__ == "__main__":
    main()
