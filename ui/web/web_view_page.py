from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtWebChannel import QWebChannel

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ModuleNotFoundError:
    QWebEngineView = None


class WebViewPage(QWidget):
    def __init__(self, html_path: str, bridge: object):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if QWebEngineView is None:
            error_label = QLabel(
                "WebView-Komponente fehlt. Bitte installieren Sie 'PyQt6-WebEngine' oder nutzen Sie eine Umgebung mit Qt WebEngine."
            )
            error_label.setWordWrap(True)
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
        else:
            self.view = QWebEngineView(self)
            self.channel = QWebChannel(self.view.page())
            self.channel.registerObject("bridge", bridge)
            self.view.page().setWebChannel(self.channel)
            self.view.setUrl(QUrl.fromLocalFile(str(Path(html_path).resolve())))
            layout.addWidget(self.view)

        self.setLayout(layout)
