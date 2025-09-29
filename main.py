import sys
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QLabel, QPushButton,
    QVBoxLayout, QWidget, QMessageBox, QHBoxLayout, QScrollArea
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QMouseEvent, QColor, QAction
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QGuiApplication


class ImageLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.pixmap_original = None
        self.scale_factor = 1.0
        self.draw_mode = "single"
        self.allow_drawing = False

        # 正式保存的线
        self.lines = []
        self.gradients = []

        # 临时线
        self.temp_start = None
        self.temp_end = None

        self.line_color = QColor(Qt.red)

        # 按钮引用（供控制显示隐藏）
        self.btn_confirm = None
        self.btn_redraw = None

    def load_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "加载失败", "无法加载图片。")
            return

        # 屏幕适配
        screen_size = QGuiApplication.primaryScreen().availableSize()
        max_w, max_h = int(screen_size.width()*0.8), int(screen_size.height()*0.8)
        if pixmap.width() > max_w or pixmap.height() > max_h:
            pixmap = pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.pixmap_original = pixmap
        self.scale_factor = 1.0
        self.setPixmap(pixmap)
        self.resize(pixmap.size())

        self.lines.clear()
        self.gradients.clear()
        self.temp_start = None
        self.temp_end = None
        self.update()

    def set_drawing_enabled(self, enabled: bool, mode=None, clear_previous=False):
        self.allow_drawing = enabled
        if mode:
            self.draw_mode = mode
        if clear_previous:
            self.lines.clear()
            self.gradients.clear()
        self.temp_start = None
        self.temp_end = None
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if not self.pixmap() or not self.allow_drawing:
            return
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            px, py = pos.x()/self.scale_factor, pos.y()/self.scale_factor
            self.temp_start = (px, py)
            self.temp_end = self.temp_start
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.allow_drawing or not self.temp_start:
            return
        pos = event.position().toPoint()
        ex, ey = pos.x()/self.scale_factor, pos.y()/self.scale_factor

        if self.draw_mode == "single":
            # 单线模式时自动横竖对齐
            dx = ex - self.temp_start[0]
            dy = ey - self.temp_start[1]
            if abs(dx) > abs(dy):
                ey = self.temp_start[1]
            else:
                ex = self.temp_start[0]
        self.temp_end = (ex, ey)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.update()

    def confirm_line(self):
        """点击确认按钮调用"""
        if self.temp_start and self.temp_end:
            if self.draw_mode == "single":
                self.lines.append({"start": self.temp_start, "end": self.temp_end})
            elif self.draw_mode == "gradient":
                self.gradients.append({"start": self.temp_start, "end": self.temp_end})

        # 清空临时线
        self.temp_start = None
        self.temp_end = None
        self.allow_drawing = False
        self.update()

        # 隐藏按钮
        if self.btn_confirm:
            self.btn_confirm.hide()
        if self.btn_redraw:
            self.btn_redraw.hide()

    def redraw_line(self):
        """点击重新画线，丢弃临时线"""
        self.temp_start = None
        self.temp_end = None
        self.update()

    def paintEvent(self, event):
        if not self.pixmap():
            return
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap())
        pen = QPen(self.line_color, 2)
        painter.setPen(pen)

        # 已确认的线
        for line in self.lines:
            sp = QPoint(int(line["start"][0]*self.scale_factor), int(line["start"][1]*self.scale_factor))
            ep = QPoint(int(line["end"][0]*self.scale_factor), int(line["end"][1]*self.scale_factor))
            painter.drawLine(sp, ep)

        for g in self.gradients:
            self._draw_gradient_like(painter, g["start"], g["end"])

        # 临时线
        if self.temp_start and self.temp_end:
            if self.draw_mode == "single":
                sp = QPoint(int(self.temp_start[0]*self.scale_factor), int(self.temp_start[1]*self.scale_factor))
                ep = QPoint(int(self.temp_end[0]*self.scale_factor), int(self.temp_end[1]*self.scale_factor))
                painter.drawLine(sp, ep)
            elif self.draw_mode == "gradient":
                self._draw_gradient_like(painter, self.temp_start, self.temp_end)

    def _draw_gradient_like(self, painter, start, end, extend=2000):
        sp = QPoint(int(start[0]*self.scale_factor), int(start[1]*self.scale_factor))
        ep = QPoint(int(end[0]*self.scale_factor), int(end[1]*self.scale_factor))
        dx, dy = ep.x()-sp.x(), ep.y()-sp.y()
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy/length, dx/length
        a1 = sp + QPoint(int(nx*extend), int(ny*extend))
        a2 = sp - QPoint(int(nx*extend), int(ny*extend))
        painter.drawLine(a1, a2)
        b1 = ep + QPoint(int(nx*extend), int(ny*extend))
        b2 = ep - QPoint(int(nx*extend), int(ny*extend))
        painter.drawLine(b1, b2)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("带确认的测量工具")

        self.image_label = ImageLabel()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)

        # 确认/重画按钮
        self.btn_confirm = QPushButton("确认")
        self.btn_redraw = QPushButton("重新画线")

        # 注册事件
        self.btn_confirm.clicked.connect(self.image_label.confirm_line)
        self.btn_redraw.clicked.connect(self.image_label.redraw_line)

        # 默认隐藏
        self.btn_confirm.hide()
        self.btn_redraw.hide()

        # 让内部能控制按钮
        self.image_label.btn_confirm = self.btn_confirm
        self.image_label.btn_redraw = self.btn_redraw

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_confirm)
        btn_layout.addWidget(self.btn_redraw)

        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.addLayout(btn_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 菜单
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        open_action = QAction("打开图片", self)
        open_action.triggered.connect(self.load_image)
        file_menu.addAction(open_action)

        measure_menu = menubar.addMenu("测量")
        single_action = QAction("单线测量", self)
        single_action.triggered.connect(self.enable_single)
        gradient_action = QAction("渐变线测量", self)
        gradient_action.triggered.connect(self.enable_gradient)
        measure_menu.addAction(single_action)
        measure_menu.addAction(gradient_action)

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "Images (*.png *.jpg *.bmp *.jpeg)"
        )
        if file:
            self.image_label.load_image(file)
            self.btn_confirm.hide()
            self.btn_redraw.hide()

    def enable_single(self):
        self.image_label.set_drawing_enabled(True, mode="single", clear_previous=True)
        self.btn_confirm.show()
        self.btn_redraw.show()

    def enable_gradient(self):
        self.image_label.set_drawing_enabled(True, mode="gradient", clear_previous=True)
        self.btn_confirm.show()
        self.btn_redraw.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1000, 700)
    w.show()
    sys.exit(app.exec())