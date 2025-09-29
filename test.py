import sys
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QLabel, QPushButton,
    QVBoxLayout, QWidget, QMessageBox, QHBoxLayout, QScrollArea
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QMouseEvent, QColor, QAction
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QGuiApplication


class ImageLabel(QLabel):
    scale_changed = Signal(float)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.pixmap_original = None
        self.scale_factor = 1.0
        self.allow_drawing = False
        self.draw_mode = "single"

        self.lines = []
        self.gradients = []
        self.temp_start = None
        self.temp_end = None
        self.line_color = QColor(Qt.red)

        self.dragging = False
        self.last_mouse_pos = None
        self.drawing_active = False

        self.btn_confirm = None
        self.btn_redraw = None

    def get_scroll_area(self):
        p = self.parentWidget()
        while p is not None:
            if isinstance(p, QScrollArea):
                return p
            p = p.parentWidget()
        return None

    def load_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "加载失败", "无法加载图片。")
            return
        screen_size = QGuiApplication.primaryScreen().availableSize()
        max_w, max_h = int(screen_size.width() * 0.8), int(screen_size.height() * 0.8)
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
        self.scale_changed.emit(1.0)

    def apply_zoom(self, factor, center=None):
        if not self.pixmap_original:
            return
        old_factor = self.scale_factor
        self.scale_factor *= factor
        self.scale_factor = max(0.1, min(5.0, self.scale_factor))
        new_w = int(self.pixmap_original.width() * self.scale_factor)
        new_h = int(self.pixmap_original.height() * self.scale_factor)
        scaled_pixmap = self.pixmap_original.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled_pixmap)
        self.resize(scaled_pixmap.size())
        self.update()
        if center:
            scroll_area = self.get_scroll_area()
            if scroll_area:
                hbar = scroll_area.horizontalScrollBar()
                vbar = scroll_area.verticalScrollBar()
                offset_x = hbar.value()
                offset_y = vbar.value()
                view_x = center.x()
                view_y = center.y()
                content_x = (offset_x + view_x) / old_factor
                content_y = (offset_y + view_y) / old_factor
                new_x = content_x * self.scale_factor
                new_y = content_y * self.scale_factor
                hbar.setValue(int(new_x - view_x))
                vbar.setValue(int(new_y - view_y))
        self.scale_changed.emit(self.scale_factor)

    def reset_zoom(self):
        if not self.pixmap_original:
            return
        self.scale_factor = 1.0
        self.setPixmap(self.pixmap_original)
        self.resize(self.pixmap_original.size())
        self.update()
        self.scale_changed.emit(1.0)

    def wheelEvent(self, event):
        if not self.pixmap_original:
            return
        if event.angleDelta().y() > 0:
            self.apply_zoom(1.25, event.position().toPoint())
        else:
            self.apply_zoom(0.8, event.position().toPoint())

    def set_drawing_enabled(self, enabled: bool, mode=None, clear_previous=False):
        self.allow_drawing = enabled
        if mode:
            self.draw_mode = mode
        if clear_previous:
            self.lines.clear()
            self.gradients.clear()
        self.temp_start = None
        self.temp_end = None
        self.drawing_active = False
        self.update()

    def _snap_angle(self, dx, dy, threshold_deg=1):
        if dx == 0 and dy == 0:
            return (dx, dy)
        ang = math.degrees(math.atan2(dy, dx))
        if abs(ang) < threshold_deg or abs(abs(ang)-180) < threshold_deg:
            return (dx, 0)
        if abs(abs(ang)-90) < threshold_deg:
            return (0, dy)
        return (dx, dy)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.pixmap() or not self.allow_drawing:
            if event.button() == Qt.LeftButton:
                self.dragging = True
                self.last_mouse_pos = event.globalPosition().toPoint()
            return
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            self.temp_start = (pos.x()/self.scale_factor, pos.y()/self.scale_factor)
            self.temp_end = self.temp_start
            self.drawing_active = True
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.temp_start and self.allow_drawing and self.drawing_active:
            pos = event.position().toPoint()
            ex, ey = pos.x()/self.scale_factor, pos.y()/self.scale_factor
            dx = ex - self.temp_start[0]
            dy = ey - self.temp_start[1]
            dx, dy = self._snap_angle(dx, dy, threshold_deg=1)
            self.temp_end = (self.temp_start[0] + dx, self.temp_start[1] + dy)
            self.update()
        elif self.dragging and self.last_mouse_pos:
            delta = event.globalPosition().toPoint() - self.last_mouse_pos
            scroll_area = self.get_scroll_area()
            if scroll_area:
                scroll_area.horizontalScrollBar().setValue(scroll_area.horizontalScrollBar().value()-delta.x())
                scroll_area.verticalScrollBar().setValue(scroll_area.verticalScrollBar().value()-delta.y())
            self.last_mouse_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.allow_drawing and self.temp_start and self.drawing_active:
                pos = event.position().toPoint()
                ex, ey = pos.x()/self.scale_factor, pos.y()/self.scale_factor
                dx = ex - self.temp_start[0]
                dy = ey - self.temp_start[1]
                dx, dy = self._snap_angle(dx, dy, threshold_deg=1)
                self.temp_end = (self.temp_start[0] + dx, self.temp_start[1] + dy)
                self.drawing_active = False
                self.update()
            self.dragging = False

    def confirm_line(self):
        if self.temp_start and self.temp_end:
            if self.draw_mode == "single":
                self.lines.append({"start": self.temp_start, "end": self.temp_end, "scale_ratio": None})
            elif self.draw_mode == "gradient":
                self.gradients.append({"start": self.temp_start, "end": self.temp_end, "scale_ratio": None})
        self.temp_start = None
        self.temp_end = None
        self.allow_drawing = False
        self.drawing_active = False
        self.update()
        if self.btn_confirm: self.btn_confirm.hide()
        if self.btn_redraw: self.btn_redraw.hide()

    def redraw_line(self):
        self.temp_start = None
        self.temp_end = None
        self.drawing_active = False
        self.update()

    def paintEvent(self, event):
        if not self.pixmap():
            return
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap())
        pen = QPen(self.line_color, 2)
        painter.setPen(pen)
        for line in self.lines:
            self._draw_line_with_arrows(painter, line["start"], line["end"])
            self._draw_length_text(painter, line)
        for g in self.gradients:
            self._draw_line_with_arrows(painter, g["start"], g["end"])
            self._draw_gradient_like(painter, g["start"], g["end"])
            self._draw_length_text(painter, g)
        if self.temp_start and self.temp_end:
            self._draw_line_with_arrows(painter, self.temp_start, self.temp_end)
            if self.draw_mode == "gradient":
                self._draw_gradient_like(painter, self.temp_start, self.temp_end)
            self._draw_length_text(
                painter, {"start": self.temp_start, "end": self.temp_end, "scale_ratio": None}
            )

    def _draw_line_with_arrows(self, painter, start, end, arrow_size=10):
        sp = QPoint(int(start[0]*self.scale_factor), int(start[1]*self.scale_factor))
        ep = QPoint(int(end[0]*self.scale_factor), int(end[1]*self.scale_factor))
        painter.drawLine(sp, ep)
        dx, dy = ep.x()-sp.x(), ep.y()-sp.y()
        length = math.hypot(dx, dy) or 1
        ux, uy = dx/length, dy/length
        perp1, perp2 = (-uy, ux), (uy, -ux)
        def draw_tip(point, back=False):
            d = -1 if back else 1
            bx = point.x()-ux*arrow_size*d
            by = point.y()-uy*arrow_size*d
            p1 = QPoint(int(bx+perp1[0]*arrow_size*0.5), int(by+perp1[1]*arrow_size*0.5))
            p2 = QPoint(int(bx+perp2[0]*arrow_size*0.5), int(by+perp2[1]*arrow_size*0.5))
            painter.drawLine(point, p1)
            painter.drawLine(point, p2)
        draw_tip(sp, True)
        draw_tip(ep, False)

    def _draw_gradient_like(self, painter, start, end, extend=2000):
        sp = QPoint(int(start[0]*self.scale_factor), int(start[1]*self.scale_factor))
        ep = QPoint(int(end[0]*self.scale_factor), int(end[1]*self.scale_factor))
        dx, dy = ep.x()-sp.x(), ep.y()-sp.y()
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy/length, dx/length
        a1 = sp + QPoint(int(nx*extend), int(ny*extend))
        a2 = sp - QPoint(int(nx*extend), int(ny*extend))
        b1 = ep + QPoint(int(nx*extend), int(ny*extend))
        b2 = ep - QPoint(int(nx*extend), int(ny*extend))
        painter.drawLine(a1, a2)
        painter.drawLine(b1, b2)

    def _draw_length_text(self, painter, line):
        p1, p2 = line["start"], line["end"]
        L = math.dist(p1, p2)
        txt = f"{L:.1f} px"
        sp = QPoint(int(p1[0]*self.scale_factor), int(p1[1]*self.scale_factor))
        ep = QPoint(int(p2[0]*self.scale_factor), int(p2[1]*self.scale_factor))
        midx = (sp.x()+ep.x())/2
        midy = (sp.y()+ep.y())/2
        painter.drawText(midx+5, midy, txt)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("测量工具 (缩放+箭头+确认+角度吸附)")

        self.image_loaded = False   # ⭐ 是否已经加载过至少一张图片

        self.image_label = ImageLabel()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.btn_confirm = QPushButton("确认")
        self.btn_redraw = QPushButton("重画")
        self.btn_confirm.clicked.connect(self.image_label.confirm_line)
        self.btn_redraw.clicked.connect(self.image_label.redraw_line)
        self.btn_confirm.hide()
        self.btn_redraw.hide()
        self.image_label.btn_confirm = self.btn_confirm
        self.image_label.btn_redraw = self.btn_redraw

        # 添加照片按钮
        self.btn_add_photo = QPushButton("添加照片")
        self.btn_add_photo.setFixedSize(200, 60)
        self.btn_add_photo.setStyleSheet("font-size:20px;")
        self.btn_add_photo.clicked.connect(self.load_image)

        bl = QHBoxLayout()
        bl.addWidget(self.btn_confirm)
        bl.addWidget(self.btn_redraw)

        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.addLayout(bl)

        c = QWidget()
        c.setLayout(layout)
        self.setCentralWidget(c)

        # overlay 界面，按钮居中
        self.overlay = QWidget(self)
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.addStretch()
        overlay_layout.addWidget(self.btn_add_photo, alignment=Qt.AlignCenter)
        overlay_layout.addStretch()
        self.overlay.setLayout(overlay_layout)
        self.overlay.setGeometry(self.rect())
        self.overlay.show()

        menubar = self.menuBar()
        fm = menubar.addMenu("文件")
        oa = QAction("打开图片", self)
        oa.triggered.connect(self.load_image)
        fm.addAction(oa)

        vm = menubar.addMenu("视图")
        zai = QAction("放大", self)
        zai.triggered.connect(lambda: self.image_label.apply_zoom(1.25, self.image_label.rect().center()))
        zao = QAction("缩小", self)
        zao.triggered.connect(lambda: self.image_label.apply_zoom(0.8, self.image_label.rect().center()))
        zr = QAction("还原", self)
        zr.triggered.connect(self.image_label.reset_zoom)
        vm.addAction(zai)
        vm.addAction(zao)
        vm.addAction(zr)

        mm = menubar.addMenu("测量")
        sa = QAction("单线测量", self)
        sa.triggered.connect(self.enable_single)
        ga = QAction("渐变线测量", self)
        ga.triggered.connect(self.enable_gradient)
        mm.addAction(sa)
        mm.addAction(ga)

        self.statusBar().showMessage("缩放: 100%")
        self.image_label.scale_changed.connect(self.update_statusbar)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.bmp *.jpeg)")
        if file:  # 用户选择了文件
            self.image_label.load_image(file)
            self.btn_confirm.hide()
            self.btn_redraw.hide()
            self.overlay.hide()
            self.image_loaded = True
        else:  # 用户取消
            if not self.image_loaded:
                self.overlay.show()   # 只在从未加载过图片时，才显示按钮
            else:
                self.overlay.hide()   # 已经加载过，就保持隐藏

    def enable_single(self):
        self.image_label.set_drawing_enabled(True, mode="single", clear_previous=True)
        self.btn_confirm.show()
        self.btn_redraw.show()

    def enable_gradient(self):
        self.image_label.set_drawing_enabled(True, mode="gradient", clear_previous=True)
        self.btn_confirm.show()
        self.btn_redraw.show()

    def update_statusbar(self, factor):
        self.statusBar().showMessage(f"缩放: {int(factor*100)}%")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1000, 700)
    w.show()
    sys.exit(app.exec())