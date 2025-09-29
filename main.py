import sys
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QLabel, QPushButton,
    QVBoxLayout, QWidget, QInputDialog, QMessageBox, QHBoxLayout, QScrollArea
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
        self.drawing = False
        self.start_orig = None
        self.end_orig = None
        self.lines = []
        self.line_color = QColor(Qt.red)

        self.dragging = False
        self.last_mouse_pos = None

    def load_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "加载失败", "无法加载图片。")
            return

        # 限制最大尺寸，避免太大撑爆
        screen_size = QGuiApplication.primaryScreen().availableSize()
        max_w, max_h = int(screen_size.width() * 0.8), int(screen_size.height() * 0.8)
        if pixmap.width() > max_w or pixmap.height() > max_h:
            pixmap = pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.pixmap_original = pixmap
        self.scale_factor = 1.0
        self.setPixmap(pixmap)
        self.resize(pixmap.size())
        self.lines.clear()
        self.start_orig = None
        self.end_orig = None
        self.update()

    def set_drawing_enabled(self, enabled: bool, clear_previous=False):
        self.allow_drawing = enabled
        self.drawing = False
        self.start_orig = None
        self.end_orig = None
        if clear_previous:
            self.lines.clear()
        self.update()


    def apply_zoom(self, factor, center=None):
        if not self.pixmap_original:
            return

        old_factor = self.scale_factor
        self.scale_factor *= factor
        self.scale_factor = max(0.1, min(5.0, self.scale_factor))

        # 缩放后的 QPixmap
        new_w = int(self.pixmap_original.width() * self.scale_factor)
        new_h = int(self.pixmap_original.height() * self.scale_factor)
        scaled_pixmap = self.pixmap_original.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled_pixmap)
        self.resize(scaled_pixmap.size())
        self.update()

        # 关键部分：保持鼠标为缩放中心
        if center:
            # 获取 QScrollArea
            scroll_area = self.parentWidget()
            if scroll_area and scroll_area.parentWidget():
                scroll_area = scroll_area.parentWidget()

                hbar = scroll_area.horizontalScrollBar()
                vbar = scroll_area.verticalScrollBar()

                # 视口左上角在内容中的位置
                offset_x = hbar.value()
                offset_y = vbar.value()

                # 鼠标位置相对于视口的坐标
                view_x = center.x()
                view_y = center.y()

                # 鼠标在内容中的坐标（缩放前）
                content_x = (offset_x + view_x) / old_factor
                content_y = (offset_y + view_y) / old_factor

                # 缩放后，内容坐标对应到新位置
                new_content_x = content_x * self.scale_factor
                new_content_y = content_y * self.scale_factor

                # 让缩放点保持在原视口位置
                hbar.setValue(int(new_content_x - view_x))
                vbar.setValue(int(new_content_y - view_y))

        self.scale_changed.emit(self.scale_factor)

    def reset_zoom(self):
        if not self.pixmap_original:
            return
        self.scale_factor = 1.0
        self.setPixmap(self.pixmap_original)
        self.resize(self.pixmap_original.size())
        self.update()
        self.scale_changed.emit(self.scale_factor)

    def wheelEvent(self, event):
        if not self.pixmap_original:
            return
        if event.angleDelta().y() > 0:
            self.apply_zoom(1.25, event.position().toPoint())
        else:
            self.apply_zoom(0.8, event.position().toPoint())

    def mousePressEvent(self, event: QMouseEvent):
        if not self.pixmap() or not self.allow_drawing:
            if event.button() == Qt.LeftButton:
                self.dragging = True
                self.last_mouse_pos = event.globalPosition().toPoint()
            return

        if event.button() == Qt.LeftButton:
            self.drawing = True
            pos = event.position().toPoint()
            self.start_orig = (pos.x() / self.scale_factor, pos.y() / self.scale_factor)
            self.end_orig = self.start_orig
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drawing and self.start_orig:
            pos = event.position().toPoint()
            ex = pos.x() / self.scale_factor
            ey = pos.y() / self.scale_factor
            dx = ex - self.start_orig[0]
            dy = ey - self.start_orig[1]
            if abs(dx) > abs(dy):
                ey = self.start_orig[1]
            else:
                ex = self.start_orig[0]
            self.end_orig = (ex, ey)
            self.update()
        elif self.dragging and self.last_mouse_pos:
            delta = event.globalPosition().toPoint() - self.last_mouse_pos
            self.parentWidget().horizontalScrollBar().setValue(
                self.parentWidget().horizontalScrollBar().value() - delta.x()
            )
            self.parentWidget().verticalScrollBar().setValue(
                self.parentWidget().verticalScrollBar().value() - delta.y()
            )
            self.last_mouse_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.drawing:
                self.drawing = False
                self.update()
            if self.dragging:
                self.dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if not self.lines:
            return
        pos = event.position().toPoint()
        px = pos.x() / self.scale_factor
        py = pos.y() / self.scale_factor
        for line in self.lines:
            if self._point_near_line((px, py), line["start"], line["end"]):
                real_length, ok = QInputDialog.getDouble(
                    self, "修改真实长度", "请输入这条线的真实长度（单位：cm）：",
                    decimals=3, min=0.0001,
                )
                if ok and real_length > 0:
                    pixel_length = math.dist(line["start"], line["end"])
                    line["scale_ratio"] = real_length / pixel_length
                    self.update()
                break

    def _point_near_line(self, p, p1, p2, threshold=5):
        x0, y0 = p
        x1, y1 = p1
        x2, y2 = p2
        if (x1, y1) == (x2, y2):
            return math.hypot(x0 - x1, y0 - y1) <= threshold / self.scale_factor
        t = ((x0 - x1) * (x2 - x1) + (y0 - y1) * (y2 - y1)) / ((x2 - x1) ** 2 + (y2 - y1) ** 2)
        t = max(0, min(1, t))
        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)
        return math.hypot(x0 - proj_x, y0 - proj_y) <= threshold / self.scale_factor

    def paintEvent(self, event):
        if not self.pixmap():
            return
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap())
        pen = QPen(self.line_color, 2)
        painter.setPen(pen)

        # 已确认的线
        for line in self.lines:
            sp = QPoint(int(line["start"][0] * self.scale_factor), int(line["start"][1] * self.scale_factor))
            ep = QPoint(int(line["end"][0] * self.scale_factor), int(line["end"][1] * self.scale_factor))
            painter.drawLine(sp, ep)
            self._draw_length_text(painter, sp, ep, line)

        # 临时线
        if self.start_orig and self.end_orig:
            sp = QPoint(int(self.start_orig[0] * self.scale_factor), int(self.start_orig[1] * self.scale_factor))
            ep = QPoint(int(self.end_orig[0] * self.scale_factor), int(self.end_orig[1] * self.scale_factor))
            painter.drawLine(sp, ep)
            temp_line = {"start": self.start_orig, "end": self.end_orig, "scale_ratio": None}
            self._draw_length_text(painter, sp, ep, temp_line)

    def _draw_length_text(self, painter, sp, ep, line):
        p1 = line["start"]
        p2 = line["end"]
        pixel_length = math.dist(p1, p2)
        if line.get("scale_ratio") is not None:
            text = f"{pixel_length * line['scale_ratio']:.2f} cm"
        else:
            text = f"{pixel_length:.1f} px"
        mid_x = (sp.x() + ep.x()) / 2
        mid_y = (sp.y() + ep.y()) / 2
        painter.drawText(mid_x + 5, mid_y, text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片缩放工具")
        self.image_label = ImageLabel()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        # 按钮
        self.confirm_button = QPushButton("确定")
        self.confirm_button.clicked.connect(self.confirm_line)
        self.confirm_button.hide()
        self.redraw_button = QPushButton("重新画线")
        self.redraw_button.clicked.connect(self.redraw_line)
        self.redraw_button.hide()

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.confirm_button)
        btn_layout.addWidget(self.redraw_button)

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

        view_menu = menubar.addMenu("视图")
        zoom_in_action = QAction("放大 (Ctrl +)", self)
        zoom_in_action.triggered.connect(lambda: self.zoom_via_menu(1.25))
        zoom_out_action = QAction("缩小 (Ctrl -)", self)
        zoom_out_action.triggered.connect(lambda: self.zoom_via_menu(0.8))
        reset_action = QAction("还原 (Ctrl 0)", self)
        reset_action.triggered.connect(self.image_label.reset_zoom)
        for a in (zoom_in_action, zoom_out_action, reset_action):
            view_menu.addAction(a)

        measure_menu = menubar.addMenu("测量")
        custom_line_action = QAction("自定义线条", self)
        custom_line_action.triggered.connect(self.enable_custom_line)
        measure_menu.addAction(custom_line_action)

        # 状态栏
        self.statusBar().showMessage("缩放: 100%")
        self.image_label.scale_changed.connect(self.update_statusbar)

        self._first_load_done = False

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "Images (*.png *.jpg *.bmp *.jpeg)"
        )
        if file_path:
            self.image_label.load_image(file_path)
            self.confirm_button.hide()
            self.redraw_button.hide()
            self.update_statusbar(self.image_label.scale_factor)

            img_size = self.image_label.pixmap().size()
            screen = QGuiApplication.primaryScreen().availableGeometry()
            if not self._first_load_done:
                w = min(img_size.width() + 50, screen.width() * 0.9)
                h = min(img_size.height() + 100, screen.height() * 0.9)
                self.resize(w, h)
                self.move((screen.width() - self.width()) // 2,
                          (screen.height() - self.height()) // 2)
                self._first_load_done = True
            else:
                geo = self.geometry()
                center = geo.center()
                w = min(img_size.width() + 50, screen.width() * 0.9)
                h = min(img_size.height() + 100, screen.height() * 0.9)
                self.resize(w, h)
                geo = self.geometry()
                geo.moveCenter(center)
                self.setGeometry(geo)

    def zoom_via_menu(self, factor):
        # 菜单缩放：以图片中心为基准
        center_point = self.image_label.rect().center()
        self.image_label.apply_zoom(factor, center_point)

    def enable_custom_line(self):
        if not self.image_label.pixmap():
            QMessageBox.information(self, "提示", "请先加载图片。")
            return
        self.image_label.set_drawing_enabled(True, clear_previous=True)
        self.confirm_button.show()
        self.redraw_button.show()

    def confirm_line(self):
        if self.image_label.start_orig and self.image_label.end_orig:
            sp = tuple(self.image_label.start_orig)
            ep = tuple(self.image_label.end_orig)
            self.image_label.lines.append({"start": sp, "end": ep, "scale_ratio": None})
        self.image_label.start_orig = None
        self.image_label.end_orig = None
        self.image_label.set_drawing_enabled(False)
        self.confirm_button.hide()
        self.redraw_button.hide()
        self.image_label.update()

    def redraw_line(self):
        self.image_label.start_orig = None
        self.image_label.end_orig = None
        self.image_label.update()

    def update_statusbar(self, factor):
        zoom_percent = int(factor * 100)
        self.statusBar().showMessage(f"缩放: {zoom_percent}%")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())