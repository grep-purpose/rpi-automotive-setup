#!/usr/bin/env python3

import os
import sys
import subprocess

from PyQt5.QtCore import Qt
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


# -------------------------------------------------
# Farben
# -------------------------------------------------

BACKGROUND = QColor(8, 8, 8)

HEADER_TEXT = QColor(235, 235, 235)
NORMAL_TEXT = QColor(220, 220, 220)
SECONDARY_TEXT = QColor(145, 145, 145)

PANEL = QColor(22, 22, 22)
PANEL_SELECTED = QColor(32, 32, 32)

BORDER = QColor(70, 70, 70)

AUDI_ORANGE = QColor(225, 105, 20)

WHITE = QColor(245, 245, 245)


OPTIONS = [
    {
        "title": "ANDROID AUTO",
        "subtitle": "HUDIY",
        "type": "android",
        "script": HUDIY_SCRIPT,
    },
    {
        "title": "MEDIEN",
        "subtitle": "KODI",
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

        self.setCursor(
            Qt.BlankCursor
        )

        self.setFocusPolicy(
            Qt.StrongFocus
        )

        self.setFocus()


    # =============================================
    # OpenGL
    # =============================================

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


    # =============================================
    # Zeichnen
    # =============================================

    def paintGL(self):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        # Hintergrund
        painter.fillRect(
            0,
            0,
            800,
            480,
            BACKGROUND
        )

        self.draw_header(painter)

        self.draw_option(
            painter,
            index=0,
            x=55,
            y=145,
            width=330,
            height=225
        )

        self.draw_option(
            painter,
            index=1,
            x=415,
            y=145,
            width=330,
            height=225
        )

        self.draw_footer(painter)

        painter.end()


    # =============================================
    # Header
    # =============================================

    def draw_header(self, painter):

        painter.setPen(
            HEADER_TEXT
        )

        font = QFont(
            "DejaVu Sans",
            18
        )

        font.setBold(True)

        painter.setFont(font)

        painter.drawText(
            38,
            26,
            300,
            35,
            Qt.AlignLeft |
            Qt.AlignVCenter,
            "AUDI INFOTAINMENT"
        )

        painter.setPen(
            SECONDARY_TEXT
        )

        font = QFont(
            "DejaVu Sans",
            10
        )

        painter.setFont(font)

        painter.drawText(
            40,
            59,
            300,
            25,
            Qt.AlignLeft |
            Qt.AlignVCenter,
            "Audi A4"
        )

        painter.setPen(
            QPen(
                QColor(210, 210, 210),
                1
            )
        )

        painter.drawLine(
            35,
            96,
            765,
            96
        )

        painter.setPen(
            NORMAL_TEXT
        )

        font = QFont(
            "DejaVu Sans",
            15
        )

        painter.setFont(font)

        painter.drawText(
            0,
            106,
            800,
            30,
            Qt.AlignCenter,
            "System auswählen"
        )


    # =============================================
    # Auswahlbox
    # =============================================

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

        option = OPTIONS[index]

        painter.fillRect(
            x,
            y,
            width,
            height,
            PANEL_SELECTED
            if selected
            else PANEL
        )

        painter.setPen(
            QPen(
                AUDI_ORANGE
                if selected
                else BORDER,

                4
                if selected
                else 1
            )
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

        icon_y = (
            y + 76
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

        # Haupttitel
        painter.setPen(
            WHITE
        )

        font = QFont(
            "DejaVu Sans",
            16
        )

        font.setBold(True)

        painter.setFont(font)

        painter.drawText(
            x,
            y + 127,
            width,
            34,
            Qt.AlignCenter,
            option["title"]
        )

        # Untertitel
        painter.setPen(
            AUDI_ORANGE
            if selected
            else SECONDARY_TEXT
        )

        font = QFont(
            "DejaVu Sans",
            11
        )

        painter.setFont(font)

        painter.drawText(
            x,
            y + 168,
            width,
            30,
            Qt.AlignCenter,
            option["subtitle"]
        )


    # =============================================
    # Android-Auto / Smartphone Symbol
    # =============================================

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
            else WHITE
        )

        painter.setPen(
            QPen(
                color,
                3
            )
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawRoundedRect(
            cx - 23,
            cy - 38,
            46,
            76,
            5,
            5
        )

        painter.drawLine(
            cx - 8,
            cy + 28,
            cx + 8,
            cy + 28
        )


    # =============================================
    # Media Symbol
    # =============================================

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
            else WHITE
        )

        painter.setPen(
            QPen(
                color,
                3
            )
        )

        painter.setBrush(
            Qt.NoBrush
        )

        points = [
            (cx - 24, cy - 33),
            (cx - 24, cy + 33),
            (cx + 34, cy),
        ]

        from PyQt5.QtCore import QPoint

        qpoints = [
            QPoint(x, y)
            for x, y in points
        ]

        painter.drawPolygon(
            *qpoints
        )


    # =============================================
    # Footer
    # =============================================

    def draw_footer(self, painter):

        painter.setPen(
            QPen(
                QColor(210, 210, 210),
                1
            )
        )

        painter.drawLine(
            35,
            413,
            765,
            413
        )

        painter.setPen(
            SECONDARY_TEXT
        )

        font = QFont(
            "DejaVu Sans",
            9
        )

        painter.setFont(font)

        painter.drawText(
            0,
            425,
            800,
            35,
            Qt.AlignCenter,
            "Auswahl     •     Drücken zum Starten"
        )


    # =============================================
    # Eingabe
    # =============================================

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

        # LINKS / HOCH
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


        # RECHTS / RUNTER / TAB
        if key in (
            Qt.Key_Right,
            Qt.Key_Down,
            Qt.Key_Tab,
            Qt.Key_2
        ):

            self.selected += 1

            if self.selected >= len(OPTIONS):
                self.selected = 0

            self.update()

            return


        # ENTER
        if key in (
            Qt.Key_Return,
            Qt.Key_Enter,
            Qt.Key_Space
        ):

            self.launch_selected()

            return


        # ESCAPE
        if key == Qt.Key_Escape:

            QApplication.quit()


    # =============================================
    # Anwendung starten
    # =============================================

    def launch_selected(self):

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

        # Launcher ausblenden
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

        # Launcher wieder anzeigen
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
