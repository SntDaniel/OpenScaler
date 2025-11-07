# image_label.py
# 包含 ImageLabel 类，负责图像显示和绘制功能
import math
from PySide6.QtWidgets import (
    QLabel, QMessageBox, QDialog, QScrollArea, QMenu
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QMouseEvent, QColor
from PySide6.QtCore import Qt, QPoint, Signal, QRectF
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtGui import QPageSize, QPageLayout

from dialogs import LengthInputDialog
from utils import snap_angle, point_to_line_distance


class ImageItem:
    """表示一张图片及其相关信息的类"""
    def __init__(self, pixmap, offset_ratios=(0.05, 0.05)):
        self.pixmap = pixmap
        self.offset_ratios = offset_ratios  # (x_ratio, y_ratio) 相对于纸张的边距比例
        self.image_scale_factor = 1.0
        self.lines = []
        self.gradients = []
        

class ImageLabel(QLabel):
    scale_changed = Signal(float)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.scale_factor = 0.5
        self.allow_drawing = False
        self.draw_mode = "single"

        self.temp_start = None
        self.temp_end = None
        self.line_color = QColor(Qt.red)

        self.dragging = False
        self.last_mouse_pos = None
        self.drawing_active = False

        self.btn_confirm = None
        self.btn_confirm_move = None
        
        # 纸张设置
        self.paper_settings = {
            "size_name": "A4",
            "width_mm": 210,
            "height_mm": 297,
            "is_portrait": True
        }
        
        # 多图片支持
        self.images = []  # 图片列表
        self.selected_image_index = -1  # 当前选中的图片索引
        self.next_image_offset_ratio = (0.05, 0.05)  # 下一张图片的默认边距比例
        
        # 图片移动相关属性
        self.image_move_mode = False
        self.image_dragging = False
        self.image_drag_start_pos = None
        self.original_offset_ratios = (0.0, 0.0)  # 初始化为比例值
        self.original_image_offset = QPoint(0, 0)  # 保存拖动开始时的实际偏移量
        
        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.context_menu = QMenu(self)
        self.delete_action = self.context_menu.addAction("删除图片")
        self.delete_action.triggered.connect(self.delete_selected_image)

    def set_paper_settings(self, settings):
        """设置纸张参数"""
        old_settings = self.paper_settings.copy()
        self.paper_settings = settings
        if self.images:
            # 更新所有图片的位置以适应新的纸张尺寸
            self._update_image_positions_for_new_paper(old_settings)
            self._update_paper_display()

    def _update_image_positions_for_new_paper(self, old_settings):
        """根据新纸张尺寸更新图片位置"""
        # 计算新旧纸张尺寸
        old_width_mm = old_settings["width_mm"]
        old_height_mm = old_settings["height_mm"]
        new_width_mm = self.paper_settings["width_mm"]
        new_height_mm = self.paper_settings["height_mm"]
        
        # 更新每张图片的位置比例
        for image_item in self.images:
            if image_item.pixmap:
                # 保持相对于纸张边缘的比例不变
                x_ratio, y_ratio = image_item.offset_ratios
                image_item.offset_ratios = (x_ratio, y_ratio)

    def get_scroll_area(self):
        p = self.parentWidget()
        while p is not None:
            if isinstance(p, QScrollArea):
                return p
            p = p.parentWidget()
        return None

    def load_image_on_paper(self, path, paper_settings=None):
        """在纸上加载图片"""
        if paper_settings:
            self.paper_settings = paper_settings
            
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "加载失败", "无法加载图片。")
            return
            
        # 检查是否是第一张图片，如果是则设置居中的offset_ratios
        is_first_image = len(self.images) == 0
        
        if is_first_image:
            # 第一张图片居中放置 (水平居中，垂直方向保留5%边距)
            center_offset_ratio = (0.5, 0.05)  # 水平居中，垂直方向5%
            new_image = ImageItem(pixmap, center_offset_ratio)
        else:
            # 后续图片使用原来的逻辑
            new_image = ImageItem(pixmap, self.next_image_offset_ratio)
            
        self.images.append(new_image)
        self.selected_image_index = len(self.images) - 1
        
        # 计算初始缩放因子
        self._calculate_initial_scale_for_image(self.selected_image_index)
        
        # 对于第一张图片，需要特殊处理offset_ratios以实现真正的居中
        if is_first_image:
            self._center_first_image()
        
        # 更新下一张图片的偏移位置比例
        self.next_image_offset_ratio = (
            min(0.9, self.next_image_offset_ratio[0] + 0.05),
            min(0.9, self.next_image_offset_ratio[1] + 0.05)
        )
        
        self._update_paper_display()
        self.update()
        self.scale_changed.emit(1.0)
        
        # 导入图片后自动进入移动模式
        self.set_image_move_mode(True)
        # 显示移动确认按钮
        if self.btn_confirm_move:
            self.btn_confirm_move.show()
        # 更新状态栏消息
        main_window = self.window()
        if hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage("图片移动模式: 点击并拖拽图片来移动位置，点击确认移动完成")

    def _center_first_image(self):
        """确保第一张图片在纸张上水平居中"""
        if len(self.images) > 0:
            first_image = self.images[0]
            # 设置水平居中，垂直方向5%
            first_image.offset_ratios = (0.5, 0.05)
    def add_image(self, path):
        """添加新图片到页面"""
        self.load_image_on_paper(path)

    def _calculate_initial_scale_for_image(self, image_index):
        """为指定图片计算初始缩放因子"""
        if image_index < 0 or image_index >= len(self.images):
            return
            
        image_item = self.images[image_index]
        pixmap = image_item.pixmap
        
        if not pixmap:
            return
            
        # 纸张可用空间（留出一点边距）
        margin_mm = 10
        available_width_mm = self.paper_settings["width_mm"] - 2 * margin_mm
        available_height_mm = self.paper_settings["height_mm"] - 2 * margin_mm
        
        # 计算如果宽度贴边时的缩放因子
        scale_by_width = available_width_mm / pixmap.width()  # mm/像素
        
        # 计算如果高度贴边时的缩放因子
        scale_by_height = available_height_mm / pixmap.height()  # mm/像素
        
        # 选择较小的缩放因子（使图片至少一边贴边）
        image_item.image_scale_factor = min(scale_by_width, scale_by_height)

    def reload_image_on_paper(self, paper_settings):
        """重新加载图片以适应纸张设置"""
        if self.images:
            self.paper_settings = paper_settings
            self._update_paper_display()
            self.update()

    def _get_image_offset_from_ratios(self, image_item):
        """根据比例计算图片在当前纸张上的实际偏移量"""
        display_scale = 8
        paper_width = int(self.paper_settings["width_mm"] * display_scale * self.scale_factor)
        paper_height = int(self.paper_settings["height_mm"] * display_scale * self.scale_factor)
        
        if image_item.pixmap:
            display_width = int(image_item.pixmap.width() * image_item.image_scale_factor * display_scale * self.scale_factor)
            display_height = int(image_item.pixmap.height() * image_item.image_scale_factor * display_scale * self.scale_factor)
            
            # 如果offset_ratios[0]是0.5，则实现水平居中
            if image_item.offset_ratios[0] == 0.5:
                x_offset = (paper_width - display_width) // 2
            else:
                x_offset = int((paper_width - display_width) * image_item.offset_ratios[0])
                
            y_offset = int((paper_height - display_height) * image_item.offset_ratios[1])
            return QPoint(x_offset, y_offset)
        return QPoint(0, 0)

    def _get_image_physical_offset(self, image_item):
        """获取图片的物理偏移量（毫米）"""
        if image_item.pixmap:
            # 偏移比例转为物理毫米
            paper_width_mm = self.paper_settings["width_mm"]
            paper_height_mm = self.paper_settings["height_mm"]
            x_offset_mm = (paper_width_mm - image_item.pixmap.width() * image_item.image_scale_factor) * image_item.offset_ratios[0]
            y_offset_mm = (paper_height_mm - image_item.pixmap.height() * image_item.image_scale_factor) * image_item.offset_ratios[1]
            return (x_offset_mm, y_offset_mm)
        return (0, 0)

    def _update_paper_display(self):
        """更新纸张显示"""
        # 创建纸张大小的Pixmap
        # 使用更高的分辨率显示 (每毫米8像素)
        display_scale = 8
        paper_width = int(self.paper_settings["width_mm"] * display_scale * self.scale_factor)
        paper_height = int(self.paper_settings["height_mm"] * display_scale * self.scale_factor)
        
        # 创建白色背景
        paper_pixmap = QPixmap(paper_width, paper_height)
        paper_pixmap.fill(Qt.white)
        
        # 绘制所有图片
        painter = QPainter(paper_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        for i, image_item in enumerate(self.images):
            if image_item.pixmap:
                # 根据image_scale_factor计算图片显示大小
                display_width = int(image_item.pixmap.width() * image_item.image_scale_factor * display_scale * self.scale_factor)
                display_height = int(image_item.pixmap.height() * image_item.image_scale_factor * display_scale * self.scale_factor)
                
                # 使用更高的质量缩放
                scaled_image = image_item.pixmap.scaled(display_width, display_height, 
                                                       Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # 根据比例计算图片偏移量
                image_offset = self._get_image_offset_from_ratios(image_item)
                image_item.image_offset = image_offset  # 保存当前偏移量
                
                # 在纸张上绘制图片
                painter.drawPixmap(image_offset.x(), image_offset.y(), scaled_image)
                
                # 只有在移动模式下且是选中的图片，才绘制蓝色边框
                if self.image_move_mode and i == self.selected_image_index:
                    pen = QPen(QColor(0, 120, 215), 2, Qt.DashLine)
                    painter.setPen(pen)
                    painter.drawRect(image_offset.x(), image_offset.y(), 
                                   display_width, display_height)
                
        painter.end()
        
        # 设置显示
        self.setPixmap(paper_pixmap)
        self.resize(paper_pixmap.size())

    def apply_zoom(self, factor, mouse_pos=None):
        """缩放纸张+图片，智能选择缩放锚点"""
        if not self.pixmap() or not self.images:
            return

        old_factor = self.scale_factor
        self.scale_factor *= factor
        self.scale_factor = max(0.1, min(5.0, self.scale_factor))
        scroll_area = self.get_scroll_area()
        if scroll_area:
            hbar = scroll_area.horizontalScrollBar()
            vbar = scroll_area.verticalScrollBar()
            viewport_w = scroll_area.viewport().width()
            viewport_h = scroll_area.viewport().height()

            # 纸张当前显示大小
            display_scale = 8
            old_paper_w = int(self.paper_settings["width_mm"] * display_scale * old_factor)
            old_paper_h = int(self.paper_settings["height_mm"] * display_scale * old_factor)
            new_paper_w = int(self.paper_settings["width_mm"] * display_scale * self.scale_factor)
            new_paper_h = int(self.paper_settings["height_mm"] * display_scale * self.scale_factor)

            # 保存当前滚动位置相对于纸张的比率
            if old_paper_w > 0:
                h_ratio = hbar.value() / old_paper_w
            else:
                h_ratio = 0
                
            if old_paper_h > 0:
                v_ratio = vbar.value() / old_paper_h
            else:
                v_ratio = 0

            # 更新显示
            self._update_paper_display()
            self.update()

            # 根据保存的比率设置新的滚动位置
            new_h_value = int(h_ratio * new_paper_w)
            new_v_value = int(v_ratio * new_paper_h)
            
            hbar.setValue(max(0, new_h_value))
            vbar.setValue(max(0, new_v_value))
        else:
            self._update_paper_display()
            self.update()

        self.scale_changed.emit(self.scale_factor)

    def wheelEvent(self, event):
        if not self.pixmap():
            return
        pos = event.position().toPoint()
        if event.angleDelta().y() > 0:
            self.apply_zoom(1.1, pos)
        else:
            self.apply_zoom(0.9, pos)

    def reset_zoom(self):
        if not self.images:
            return
        self.scale_factor = 1.0
        # Update paper display at original scale
        self._update_paper_display()
        self.update()
        self.scale_changed.emit(1.0)

    def set_drawing_enabled(self, enabled: bool, mode=None, clear_previous=False):
        self.allow_drawing = enabled
        if mode:
            self.draw_mode = mode
        if clear_previous:
            if self.selected_image_index >= 0:
                image_item = self.images[self.selected_image_index]
                image_item.lines.clear()
                image_item.gradients.clear()
        self.temp_start = None
        self.temp_end = None
        self.drawing_active = False
        self.update()

    def set_image_move_mode(self, enabled: bool):
        """设置图片移动模式"""
        self.image_move_mode = enabled
        if enabled:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self.image_dragging = False
        # 更新显示以显示或隐藏蓝色边框
        self._update_paper_display()
        self.update()

    def _screen_to_image_coords(self, screen_x, screen_y, image_index):
        """将屏幕坐标转换为指定图片的坐标（像素单位）"""
        if image_index < 0 or image_index >= len(self.images):
            return (0, 0)
            
        image_item = self.images[image_index]
        display_scale = 8  # 显示时每毫米8像素
        # 考虑缩放和偏移
        img_x = (screen_x - image_item.image_offset.x()) / (image_item.image_scale_factor * display_scale * self.scale_factor)
        img_y = (screen_y - image_item.image_offset.y()) / (image_item.image_scale_factor * display_scale * self.scale_factor)
        return (img_x, img_y)

    def _image_to_screen_coords(self, img_x, img_y, image_index):
        """将指定图片的坐标（像素单位）转换为屏幕坐标"""
        if image_index < 0 or image_index >= len(self.images):
            return (0, 0)
            
        image_item = self.images[image_index]
        display_scale = 8  # 显示时每毫米8像素
        screen_x = img_x * image_item.image_scale_factor * display_scale * self.scale_factor + image_item.image_offset.x()
        screen_y = img_y * image_item.image_scale_factor * display_scale * self.scale_factor + image_item.image_offset.y()
        return (screen_x, screen_y)

    def _is_point_on_image(self, point, image_index):
        """检查点是否在指定图片区域内"""
        if image_index < 0 or image_index >= len(self.images):
            return False
            
        image_item = self.images[image_index]
        if not image_item.pixmap:
            return False
            
        # 获取图片在屏幕上的边界
        display_scale = 8
        display_width = int(image_item.pixmap.width() * image_item.image_scale_factor * display_scale * self.scale_factor)
        display_height = int(image_item.pixmap.height() * image_item.image_scale_factor * display_scale * self.scale_factor)
        
        image_rect = QRectF(
            image_item.image_offset.x(),
            image_item.image_offset.y(),
            display_width,
            display_height
        )
        
        return image_rect.contains(point.x(), point.y())

    def _get_image_at_point(self, point):
        """获取点击位置的图片索引"""
        for i in range(len(self.images) - 1, -1, -1):  # 从上到下查找（后添加的在上层）
            if self._is_point_on_image(point, i):
                return i
        return -1

    def mousePressEvent(self, event: QMouseEvent):
        if not self.pixmap():
            return
            
        if event.button() == Qt.LeftButton:
            # 检查是否在图片移动模式下
            if self.image_move_mode:
                # 查找点击的是哪张图片
                clicked_image_index = self._get_image_at_point(event.position().toPoint())
                if clicked_image_index >= 0:
                    self.selected_image_index = clicked_image_index
                    self.image_dragging = True
                    self.image_drag_start_pos = event.position().toPoint()
                    image_item = self.images[self.selected_image_index]
                    self.original_offset_ratios = image_item.offset_ratios
                    # 保存拖动开始时的实际偏移量
                    self.original_image_offset = QPoint(image_item.image_offset.x(), image_item.image_offset.y())
                    self.setCursor(Qt.ClosedHandCursor)
                    self._update_paper_display()
                    self.update()
                return
                
            # 检查是否点击了某张图片来选中它（但不显示边框，除非在移动模式下）
            clicked_image_index = self._get_image_at_point(event.position().toPoint())
            if clicked_image_index >= 0:
                self.selected_image_index = clicked_image_index
                # 不再更新显示，因为我们不希望在非移动模式下显示边框
                self.update()
            
            # 检查是否允许绘图
            if not self.allow_drawing:
                self.dragging = True
                self.last_mouse_pos = event.globalPosition().toPoint()
                return
                
            # 只有当选中了图片时才能绘图
            if self.selected_image_index >= 0:
                pos = event.position().toPoint()
                # 转换为相对于选中图片的坐标（以原始图片像素为单位）
                img_x, img_y = self._screen_to_image_coords(pos.x(), pos.y(), self.selected_image_index)
                self.temp_start = (img_x, img_y)
                self.temp_end = self.temp_start
                self.drawing_active = True
                self.update()
                
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.image_dragging and self.image_move_mode and self.selected_image_index >= 0:
            # 移动图片
            image_item = self.images[self.selected_image_index]
            if image_item.pixmap:
                # 计算当前纸张尺寸
                display_scale = 8
                paper_width = int(self.paper_settings["width_mm"] * display_scale * self.scale_factor)
                paper_height = int(self.paper_settings["height_mm"] * display_scale * self.scale_factor)
                
                # 计算图片尺寸
                display_width = int(image_item.pixmap.width() * image_item.image_scale_factor * display_scale * self.scale_factor)
                display_height = int(image_item.pixmap.height() * image_item.image_scale_factor * display_scale * self.scale_factor)
                
                # 计算可移动范围
                max_x_offset = max(0, paper_width - display_width)
                max_y_offset = max(0, paper_height - display_height)
                
                # 计算鼠标拖动偏移
                delta = event.position().toPoint() - self.image_drag_start_pos
                
                # 计算新位置 - 使用保存的实际原始偏移量
                new_x = self.original_image_offset.x() + delta.x()
                new_y = self.original_image_offset.y() + delta.y()
                
                # 限制在纸张范围内
                new_x = max(0, min(new_x, max_x_offset))
                new_y = max(0, min(new_y, max_y_offset))
                
                # 计算新的边距比例
                if max_x_offset > 0:
                    x_ratio = new_x / max_x_offset
                else:
                    x_ratio = 0.0
                    
                if max_y_offset > 0:
                    y_ratio = new_y / max_y_offset
                else:
                    y_ratio = 0.0
                
                image_item.offset_ratios = (x_ratio, y_ratio)
                
                self._update_paper_display()
                self.update()
            return
            
        if self.temp_start and self.allow_drawing and self.drawing_active and self.selected_image_index >= 0:
            pos = event.position().toPoint()
            # 转换为相对于选中图片的坐标（以原始图片像素为单位）
            img_x, img_y = self._screen_to_image_coords(pos.x(), pos.y(), self.selected_image_index)
            ex, ey = img_x, img_y
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
            if self.image_dragging:
                self.image_dragging = False
                self.setCursor(Qt.OpenHandCursor)
                # 确认新的图片位置
                if self.selected_image_index >= 0:
                    image_item = self.images[self.selected_image_index]
                    # 保持当前的offset_ratios值
                    pass
                return
            if self.allow_drawing and self.temp_start and self.drawing_active and self.selected_image_index >= 0:
                pos = event.position().toPoint()
                # 转换为相对于选中图片的坐标（以原始图片像素为单位）
                img_x, img_y = self._screen_to_image_coords(pos.x(), pos.y(), self.selected_image_index)
                ex, ey = img_x, img_y
                dx = ex - self.temp_start[0]
                dy = ey - self.temp_start[1]
                dx, dy = snap_angle(dx, dy, threshold_deg=1)
                self.temp_end = (self.temp_start[0] + dx, self.temp_start[1] + dy)
                self.drawing_active = False
                self.update()
            self.dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """处理双击事件，用于输入目标长度"""
        if not self.pixmap() or not self.images:
            return
            
        click_pos = event.position().toPoint()
        
        # 查找点击的是哪张图片
        image_index = self._get_image_at_point(click_pos)
        if image_index < 0:
            return
            
        self.selected_image_index = image_index
        self._update_paper_display()
        self.update()
        
        image_item = self.images[image_index]
        
        # 检查是否双击了任何一条线 (扩大识别区域到15像素)
        for i, line in enumerate(image_item.lines):
            if self._is_point_near_line(click_pos, line, image_index, tolerance=15):
                self._open_length_dialog(i, "line", line, image_index)
                return
                
        for i, gradient in enumerate(image_item.gradients):
            if self._is_point_near_line(click_pos, gradient, image_index, tolerance=15):
                self._open_length_dialog(i, "gradient", gradient, image_index)
                return

    def show_context_menu(self, position):
        """显示右键菜单"""
        # 检查是否有图片
        if not self.images:
            return
            
        # 检查点击位置是否在图片上
        local_point = QPoint(position)
        
        # 查找点击的是哪张图片
        clicked_image_index = self._get_image_at_point(local_point)
        if clicked_image_index >= 0:
            self.selected_image_index = clicked_image_index
            self._update_paper_display()
            self.update()
            # 显示菜单
            self.context_menu.exec(self.mapToGlobal(position))

    def delete_selected_image(self):
        """删除选中的图片"""
        if 0 <= self.selected_image_index < len(self.images):
            reply = QMessageBox.question(
                self, 
                "确认删除", 
                "确定要删除这张图片吗？", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self._delete_image(self.selected_image_index)

    def _is_point_near_line(self, point, line, image_index, tolerance=15):
        """检查点是否在线附近"""
        start = line["start"]
        end = line["end"]
        
        # 将原始坐标转换为当前缩放下的坐标
        sp_x, sp_y = self._image_to_screen_coords(start[0], start[1], image_index)
        ep_x, ep_y = self._image_to_screen_coords(end[0], end[1], image_index)
        
        sp = QPoint(int(sp_x), int(sp_y))
        ep = QPoint(int(ep_x), int(ep_y))
        
        # 计算点到线段的距离
        distance = point_to_line_distance(point, sp, ep)
        return distance <= tolerance  # 扩大容差范围

    def _open_length_dialog(self, index, line_type, line, image_index):
        """打开对话框输入实际长度"""
        dialog = LengthInputDialog(self)
        if "real_length" in line:
            # 从存储的值中提取数值和单位
            real_length_mm = line["real_length"]
            original_value = line.get("original_value", real_length_mm)
            original_unit = line.get("original_unit", "mm")
            dialog.set_length(str(original_value))
            dialog.set_unit(original_unit)
        if dialog.exec() == QDialog.Accepted:
            try:
                # 获取输入的数值和单位
                length_value = float(dialog.get_length())
                unit = dialog.get_unit()
                
                # 转换为毫米
                real_length_mm = length_value
                if unit == "cm":
                    real_length_mm = length_value * 10
                elif unit == "inch":
                    real_length_mm = length_value * 25.4
                
                # 更新线的数据
                image_item = self.images[image_index]
                if line_type == "line":
                    image_item.lines[index]["real_length"] = real_length_mm
                    image_item.lines[index]["original_value"] = length_value
                    image_item.lines[index]["original_unit"] = unit
                    # 根据实际长度调整图片缩放
                    self._adjust_image_scale(line, real_length_mm, image_index)
                else:
                    image_item.gradients[index]["real_length"] = real_length_mm
                    image_item.gradients[index]["original_value"] = length_value
                    image_item.gradients[index]["original_unit"] = unit
                    # 根据实际长度调整图片缩放
                    self._adjust_image_scale(line, real_length_mm, image_index)
                self.update()
            except ValueError:
                QMessageBox.warning(self, "输入错误", "请输入有效的数字")

    def _adjust_image_scale(self, line, real_length_mm, image_index):
        """根据实际长度调整指定图片的缩放"""
        # 计算当前像素长度
        pixel_length = math.dist(line["start"], line["end"])
        if pixel_length <= 0:
            return
            
        # 计算新的缩放因子 (毫米/像素)
        new_scale = real_length_mm / pixel_length
        
        # 更新图片缩放因子
        if image_index >= 0:
            image_item = self.images[image_index]
            image_item.image_scale_factor = new_scale
            
            # 重新显示图片
            self._update_paper_display()
            
            # 显示状态消息
            self.window().statusBar().showMessage(f"图片已根据参考长度调整缩放: 1像素 = {new_scale:.4f}毫米")

    def confirm_line(self):
        """确认线条并自动弹出长度输入框"""
        if self.temp_start and self.temp_end and self.selected_image_index >= 0:
            new_line = {"start": self.temp_start, "end": self.temp_end, "scale_ratio": None}
            image_item = self.images[self.selected_image_index]
            if self.draw_mode == "single":
                image_item.lines.append(new_line)
                # 自动打开长度输入对话框
                self._open_length_dialog_for_new_line(len(image_item.lines) - 1, "line", new_line, self.selected_image_index)
            elif self.draw_mode == "gradient":
                image_item.gradients.append(new_line)
                # 自动打开长度输入对话框
                self._open_length_dialog_for_new_line(len(image_item.gradients) - 1, "gradient", new_line, self.selected_image_index)
        self.temp_start = None
        self.temp_end = None
        self.allow_drawing = False
        self.drawing_active = False
        self.update()
        if self.btn_confirm: 
            self.btn_confirm.hide()

    def _open_length_dialog_for_new_line(self, index, line_type, line, image_index):
        """为新添加的线条打开长度输入对话框"""
        dialog = LengthInputDialog(self)
        if dialog.exec() == QDialog.Accepted:
            try:
                # 获取输入的数值和单位
                length_value = float(dialog.get_length())
                unit = dialog.get_unit()
                
                # 转换为毫米
                real_length_mm = length_value
                if unit == "cm":
                    real_length_mm = length_value * 10
                elif unit == "inch":
                    real_length_mm = length_value * 25.4
                
                # 更新线的数据
                image_item = self.images[image_index]
                if line_type == "line":
                    image_item.lines[index]["real_length"] = real_length_mm
                    image_item.lines[index]["original_value"] = length_value
                    image_item.lines[index]["original_unit"] = unit
                    # 根据实际长度调整图片缩放
                    self._adjust_image_scale(line, real_length_mm, image_index)
                else:
                    image_item.gradients[index]["real_length"] = real_length_mm
                    image_item.gradients[index]["original_value"] = length_value
                    image_item.gradients[index]["original_unit"] = unit
                    # 根据实际长度调整图片缩放
                    self._adjust_image_scale(line, real_length_mm, image_index)
                self.update()
            except ValueError:
                QMessageBox.warning(self, "输入错误", "请输入有效的数字")

    def paintEvent(self, event):
        if not self.pixmap():
            return
        painter = QPainter(self)
        # 提高渲染质量
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(0, 0, self.pixmap())
        pen = QPen(self.line_color, 2)
        painter.setPen(pen)
        
        # 绘制所有图片的线条
        for image_index, image_item in enumerate(self.images):
            # 绘制已完成的线条（只显示设置了实际长度的线条）
            for line in image_item.lines:
                self._draw_line_with_arrows(painter, line["start"], line["end"], image_index)
                # 只有设置了实际长度才显示文本
                if "real_length" in line:
                    self._draw_length_text(painter, line, image_index)
                    
            for g in image_item.gradients:
                self._draw_line_with_arrows(painter, g["start"], g["end"], image_index)
                self._draw_gradient_like(painter, g["start"], g["end"], image_index)
                # 只有设置了实际长度才显示文本
                if "real_length" in g:
                    self._draw_length_text(painter, g, image_index)
                
        # 绘制临时线条（不显示长度）
        if self.temp_start and self.temp_end and self.selected_image_index >= 0:
            self._draw_line_with_arrows(painter, self.temp_start, self.temp_end, self.selected_image_index)
            if self.draw_mode == "gradient":
                self._draw_gradient_like(painter, self.temp_start, self.temp_end, self.selected_image_index)
            # 临时线条不显示长度文本
        painter.end()

    def _draw_line_with_arrows(self, painter, start, end, image_index, arrow_size=10):
        # 考虑图片在纸张上的偏移和缩放
        display_scale = 8  # 显示时每毫米8像素
        sp_x, sp_y = self._image_to_screen_coords(start[0], start[1], image_index)
        ep_x, ep_y = self._image_to_screen_coords(end[0], end[1], image_index)
        
        sp = QPoint(int(sp_x), int(sp_y))
        ep = QPoint(int(ep_x), int(ep_y))
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

    def _draw_gradient_like(self, painter, start, end, image_index, extend=2000):
        # 考虑图片在纸张上的偏移和缩放
        display_scale = 8  # 显示时每毫米8像素
        sp_x, sp_y = self._image_to_screen_coords(start[0], start[1], image_index)
        ep_x, ep_y = self._image_to_screen_coords(end[0], end[1], image_index)
        
        sp = QPoint(int(sp_x), int(sp_y))
        ep = QPoint(int(ep_x), int(ep_y))
        dx, dy = ep.x()-sp.x(), ep.y()-sp.y()
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy/length, dx/length
        a1 = sp + QPoint(int(nx*extend), int(ny*extend))
        a2 = sp - QPoint(int(nx*extend), int(ny*extend))
        b1 = ep + QPoint(int(nx*extend), int(ny*extend))
        b2 = ep - QPoint(int(nx*extend), int(ny*extend))
        painter.drawLine(a1, a2)
        painter.drawLine(b1, b2)

    def _draw_length_text(self, painter, line, image_index):
        p1, p2 = line["start"], line["end"]
        # 显示文本逻辑：只显示设置了实际长度的线条
        if "real_length" in line and "original_value" in line and "original_unit" in line:
            # 使用用户输入的原始值和单位显示
            txt = f"{line['original_value']:.2f} {line['original_unit']}"
        elif "real_length" in line:
            # 如果没有原始值信息，则显示转换后的毫米值
            txt = f"{line['real_length']:.2f} mm"
        else:
            # 如果没有设置实际长度，不显示文本
            return
            
        # 考虑图片在纸张上的偏移和缩放
        display_scale = 8  # 显示时每毫米8像素
        sp_x, sp_y = self._image_to_screen_coords(p1[0], p1[1], image_index)
        ep_x, ep_y = self._image_to_screen_coords(p2[0], p2[1], image_index)
        
        sp = QPoint(int(sp_x), int(sp_y))
        ep = QPoint(int(ep_x), int(ep_y))
        midx = (sp.x()+ep.x())/2
        midy = (sp.y()+ep.y())/2
        # 修正文本位置，使其显示在线段中间而不是偏移
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(txt)
        text_height = font_metrics.height()
        painter.drawText(int(midx - text_width/2), int(midy - text_height/2), txt)


    def _delete_image(self, image_index):
        """删除指定索引的图片"""
        if 0 <= image_index < len(self.images):
            # 删除图片
            del self.images[image_index]
            
            # 更新选中索引
            if self.selected_image_index == image_index:
                self.selected_image_index = -1
            elif self.selected_image_index > image_index:
                self.selected_image_index -= 1
                
            # 更新显示
            self._update_paper_display()
            self.update()
            
            # 如果没有图片了，隐藏确认按钮
            if not self.images:
                if self.btn_confirm_move:
                    self.btn_confirm_move.hide()
                if self.btn_confirm:
                    self.btn_confirm.hide()

    def export_to_pdf(self, file_path, paper_settings):
        """导出为PDF，确保与程序显示一致"""
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            
            # 设置纸张大小和方向
            page_size = None
            if paper_settings["size_name"] == "A4":
                page_size = QPageSize(QPageSize.A4)
            elif paper_settings["size_name"] == "A3":
                page_size = QPageSize(QPageSize.A3)
            elif paper_settings["size_name"] == "A5":
                page_size = QPageSize(QPageSize.A5)
            elif paper_settings["size_name"] == "Letter":
                page_size = QPageSize(QPageSize.Letter)
            elif paper_settings["size_name"] == "Legal":
                page_size = QPageSize(QPageSize.Legal)
                
            # 根据方向设置页面大小
            if not paper_settings["is_portrait"]:
                # 如果是横向，使用LandscapeOrientation
                printer.setPageSize(page_size)
                printer.setPageOrientation(QPageLayout.Landscape)
            else:
                # 默认是纵向
                printer.setPageSize(page_size)
                printer.setPageOrientation(QPageLayout.Portrait)
            
            painter = QPainter()
            painter.begin(printer)
            # 设置渲染质量
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            
            # 获取PDF页面的DPI和尺寸信息
            dpi = printer.resolution()
            page_rect = printer.pageRect(QPrinter.DevicePixel)
            page_width_px = page_rect.width()
            page_height_px = page_rect.height()
            
            # 使用与程序中相同的缩放因子来保持一致性
            display_scale = 8
            current_scale_factor = 1.0  # PDF导出使用1:1比例，不使用界面缩放
            
            # 绘制所有图片，保持与程序显示一致的逻辑
            for image_item in self.images:
                if image_item.pixmap:
                    # 根据image_scale_factor计算图片显示大小（与程序中一致）
                    # 这里需要将毫米转换为像素点进行绘制
                    img_width_mm = image_item.pixmap.width() * image_item.image_scale_factor
                    img_height_mm = image_item.pixmap.height() * image_item.image_scale_factor
                    
                    # 转换为像素点 (1英寸=25.4毫米, 1英寸=dpi像素)
                    display_width = int(img_width_mm * dpi / 25.4)
                    display_height = int(img_height_mm * dpi / 25.4)
                    
                    # 使用更高的质量缩放（与程序中一致）
                    scaled_image = image_item.pixmap.scaled(display_width, display_height, 
                                                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    # 根据比例计算图片偏移量（与程序中一致）
                    x_offset_ratio, y_offset_ratio = image_item.offset_ratios
                    max_x_offset = max(0, page_width_px - display_width)
                    max_y_offset = max(0, page_height_px - display_height)
                    x_offset = int(max_x_offset * x_offset_ratio)
                    y_offset = int(max_y_offset * y_offset_ratio)
                    
                    # 在PDF页面上绘制图片
                    painter.drawPixmap(x_offset, y_offset, scaled_image)
            
            painter.end()
            return True
        except Exception as e:
            print(f"导出PDF时出错: {e}")
            return False