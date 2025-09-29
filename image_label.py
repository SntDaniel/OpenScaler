# 包含 ImageLabel 类，负责图像显示和绘制功能
import sys
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QLabel, QPushButton,
    QVBoxLayout, QWidget, QMessageBox, QHBoxLayout, QScrollArea,
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QMouseEvent, QColor, QAction
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QGuiApplication

from dialogs import LengthInputDialog
from utils import snap_angle, point_to_line_distance


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
            dx, dy = snap_angle(dx, dy, threshold_deg=1)
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
                dx, dy = snap_angle(dx, dy, threshold_deg=1)
                self.temp_end = (self.temp_start[0] + dx, self.temp_start[1] + dy)
                self.drawing_active = False
                self.update()
            self.dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """处理双击事件，用于输入目标长度"""
        if not self.pixmap():
            return
            
        click_pos = event.position().toPoint()
        
        # 检查是否双击了任何一条线
        for i, line in enumerate(self.lines):
            if self._is_point_near_line(click_pos, line):
                self._open_length_dialog(i, "line", line)
                return
                
        for i, gradient in enumerate(self.gradients):
            if self._is_point_near_line(click_pos, gradient):
                self._open_length_dialog(i, "gradient", gradient)
                return

    def _is_point_near_line(self, point, line):
        """检查点是否在线附近"""
        start = line["start"]
        end = line["end"]
        
        # 将原始坐标转换为当前缩放下的坐标
        sp = QPoint(int(start[0] * self.scale_factor), int(start[1] * self.scale_factor))
        ep = QPoint(int(end[0] * self.scale_factor), int(end[1] * self.scale_factor))
        
        # 计算点到线段的距离
        distance = point_to_line_distance(point, sp, ep)
        return distance <= 5  # 5像素的容差范围

    def _open_length_dialog(self, index, line_type, line):
        """打开对话框输入实际长度"""
        dialog = LengthInputDialog(self)
        if "real_length" in line:
            dialog.set_length(str(line["real_length"]))
        if dialog.exec() == QDialog.Accepted:
            try:
                real_length = float(dialog.get_length())
                # 更新线的数据
                if line_type == "line":
                    self.lines[index]["real_length"] = real_length
                else:
                    self.gradients[index]["real_length"] = real_length
                self.update()
            except ValueError:
                QMessageBox.warning(self, "输入错误", "请输入有效的数字")

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
        # 显示文本逻辑：如果设置了实际长度，则显示实际长度，否则显示像素长度
        if "real_length" in line:
            txt = f"{line['real_length']:.2f} units"
        else:
            L = math.dist(p1, p2)
            txt = f"{L:.1f} px"
            
        sp = QPoint(int(p1[0]*self.scale_factor), int(p1[1]*self.scale_factor))
        ep = QPoint(int(p2[0]*self.scale_factor), int(p2[1]*self.scale_factor))
        midx = (sp.x()+ep.x())/2
        midy = (sp.y()+ep.y())/2
        painter.drawText(midx+5, midy, txt)