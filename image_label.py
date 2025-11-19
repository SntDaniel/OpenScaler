# image_label.py
# 包含 ImageLabel 类，负责图像显示和绘制功能
import math
from PySide6.QtWidgets import (
    QLabel, QMessageBox, QDialog, QScrollArea, QMenu
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QMouseEvent, QColor, QCursor, QAction
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
        
        # 缓存相关的属性，用于性能优化
        self._cached_scaled_pixmap = None
        self._last_render_params = None  # (width, height)
        
        # 存储在屏幕(widget)上的实际显示尺寸
        self.display_width_on_widget = 0
        self.display_height_on_widget = 0
        self.image_offset = QPoint(0, 0)

    def get_scaled_pixmap(self, target_width, target_height):
        """获取缓存的缩放图片，如果尺寸改变则重新缩放"""
        if (self._cached_scaled_pixmap is None or 
            self._last_render_params != (target_width, target_height)):
            
            self._cached_scaled_pixmap = self.pixmap.scaled(
                target_width, target_height,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self._last_render_params = (target_width, target_height)
            
        return self._cached_scaled_pixmap


class ImageLabel(QLabel):
    scale_changed = Signal(float)
    
    # 常量定义
    DISPLAY_SCALE = 8.0  # 每毫米的显示像素数

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
        self.setFocusPolicy(Qt.StrongFocus)

        # 纸张设置
        self.paper_settings = {
            "size_name": "A4",
            "width_mm": 210,
            "height_mm": 297,
            "is_portrait": True
        }
        
        # 多图片支持
        self.images = []
        self.selected_image_index = -1
        # self.next_image_offset_ratio 已不再需要，由自动排版代替
        
        # 图片移动相关属性
        self.image_move_mode = False
        self.image_dragging = False
        self.image_drag_start_pos = None
        self.original_offset_ratios = (0.0, 0.0)
        self.original_image_offset = QPoint(0, 0)
        
        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.context_menu = QMenu(self)
        self.delete_action = self.context_menu.addAction("删除图片")
        self.delete_action.triggered.connect(self.delete_selected_image)
        
        # 吸附阈值, 单位: 屏幕像素
        self.edge_snap_threshold_press = 4
        self.edge_snap_threshold_drag = 4
        
        # 用于防止光标翘曲(warp)时抖动
        self.last_warped_pos = None

    def set_paper_settings(self, settings):
        """设置纸张参数"""
        old_settings = self.paper_settings.copy()
        self.paper_settings = settings
        if self.images:
            # 纸张改变时，我们可以选择重新排版或者保持相对位置
            # 这里保持相对位置不变（无需额外操作，因为存储的是 ratio）
            self._update_paper_display()

    def get_scroll_area(self):
        p = self.parentWidget()
        while p is not None:
            if isinstance(p, QScrollArea):
                return p
            p = p.parentWidget()
        return None

    def load_image_on_paper(self, path, paper_settings=None):
        """兼容旧接口：加载单张图片"""
        self.add_images([path], paper_settings)

    def add_images(self, paths, paper_settings=None):
        """批量添加图片并自动排版"""
        if paper_settings:
            self.paper_settings = paper_settings
            
        new_images_start_index = len(self.images)
        added_count = 0
        
        for path in paths:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                continue
            
            # 创建新图片对象，初始位置给(0,0)，稍后自动排版会覆盖
            new_image = ImageItem(pixmap, (0.0, 0.0))
            self.images.append(new_image)
            added_count += 1
            
        if added_count == 0:
            # 如果没有添加成功（可能是无效路径或空列表）
            if not self.images: 
                QMessageBox.warning(self, "加载失败", "无法加载图片。")
            return

        # 选中最后一张
        self.selected_image_index = len(self.images) - 1
        
        # 1. 计算初始缩放
        # 如果是一次性导入多张，或者画布上已经有图片，则视为批量/追加模式
        # 这种模式下我们将图片默认缩放得更小一点，方便排列
        is_batch_mode = len(paths) > 1 or new_images_start_index > 0
        
        for i in range(new_images_start_index, len(self.images)):
            self._calculate_initial_scale_for_image(i, is_batch_mode=is_batch_mode)

        # 2. 自动排版 (重新排列所有图片，防止重叠)
        self._auto_arrange_images()
        
        self._update_paper_display()
        self.update()
        self.scale_changed.emit(1.0)
        
        self.set_image_move_mode(True)
        if self.btn_confirm_move:
            self.btn_confirm_move.show()
        
        main_window = self.window()
        if hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(f"已加载 {added_count} 张图片。拖拽可调整位置，点击确认完成。")

    def _calculate_initial_scale_for_image(self, image_index, is_batch_mode=False):
        if not (0 <= image_index < len(self.images)):
            return
            
        image_item = self.images[image_index]
        pixmap = image_item.pixmap
        if not pixmap:
            return
            
        margin_mm = 10
        available_width_mm = self.paper_settings["width_mm"] - 2 * margin_mm
        available_height_mm = self.paper_settings["height_mm"] - 2 * margin_mm
        
        if pixmap.width() == 0 or pixmap.height() == 0:
            return

        scale_by_width = available_width_mm / pixmap.width()
        scale_by_height = available_height_mm / pixmap.height()
        
        base_scale = min(scale_by_width, scale_by_height)
        
        # 如果是批量导入，缩小到 45% 左右，类似缩略图排列
        if is_batch_mode:
            image_item.image_scale_factor = base_scale * 0.45
        else:
            image_item.image_scale_factor = base_scale

    def _auto_arrange_images(self):
        """
        流式布局算法：从左到右放置，放不下就换行。
        计算出的位置将被转换为 offset_ratios。
        """
        if not self.images:
            return

        # 使用模拟的像素尺寸进行计算 (基于 scale_factor=1.0)
        # 这样计算出的 ratio 是通用的
        simulated_scale = 1.0
        display_scale = self.DISPLAY_SCALE # 8 pixels per mm
        
        paper_w = int(self.paper_settings["width_mm"] * display_scale)
        paper_h = int(self.paper_settings["height_mm"] * display_scale)
        
        # 布局参数
        padding = int(5 * display_scale) # 5mm 间距
        margin_top = int(10 * display_scale)
        margin_left = int(10 * display_scale)
        
        current_x = margin_left
        current_y = margin_top
        row_max_height = 0
        
        for img in self.images:
            if not img.pixmap:
                continue
                
            # 计算图片在 scale=1.0 下的显示尺寸
            img_w = int(img.pixmap.width() * img.image_scale_factor * display_scale * simulated_scale)
            img_h = int(img.pixmap.height() * img.image_scale_factor * display_scale * simulated_scale)
            
            # 检查是否需要换行 (如果是第一张图，不需要换行)
            if current_x + img_w > paper_w - margin_left and current_x > margin_left:
                current_x = margin_left
                current_y += row_max_height + padding
                row_max_height = 0
            
            # 确保图片不会超出纸张底部太多（可选：如果超出底部，也可以继续往下排，反正ScrollArea能滚）
            
            # 计算 ratio
            # pixel_offset = (paper_dim - img_dim) * ratio
            # ratio = pixel_offset / (paper_dim - img_dim)
            
            free_w = paper_w - img_w
            free_h = paper_h - img_h
            
            ratio_x = 0.0
            ratio_y = 0.0
            
            if free_w != 0:
                ratio_x = current_x / free_w
            else:
                ratio_x = 0.0 # 填满宽度时居左/居中均可，这里设0相当于居左(如果有margin的话)
                
            if free_h != 0:
                ratio_y = current_y / free_h
            else:
                ratio_y = 0.0
                
            # 限制 ratio 范围（虽然数学上允许<0或>1表示出界，但为了UI体验最好限制一下）
            # 注意：如果图片比纸张大，free_w < 0，此时除法结果符号会反，这里做个简单保护
            if free_w > 0:
                ratio_x = max(0.0, min(1.0, ratio_x))
            
            if free_h > 0:
                ratio_y = max(0.0, min(1.0, ratio_y))
            
            img.offset_ratios = (ratio_x, ratio_y)
            
            # 更新游标
            current_x += img_w + padding
            row_max_height = max(row_max_height, img_h)

    def add_image(self, path):
        self.load_image_on_paper(path)

    def reload_image_on_paper(self, paper_settings):
        if self.images:
            self.paper_settings = paper_settings
            self._update_paper_display()
            self.update()

    def _get_display_metrics(self):
        """获取当前纸张的像素尺寸"""
        paper_width = int(self.paper_settings["width_mm"] * self.DISPLAY_SCALE * self.scale_factor)
        paper_height = int(self.paper_settings["height_mm"] * self.DISPLAY_SCALE * self.scale_factor)
        return paper_width, paper_height

    def _get_image_offset_from_ratios(self, image_item):
        """根据比例计算图片在当前纸张上的实际偏移量"""
        paper_width, paper_height = self._get_display_metrics()
        
        if image_item.pixmap:
            # 使用缓存的显示尺寸
            display_width = image_item.display_width_on_widget
            display_height = image_item.display_height_on_widget
            
            # 计算剩余空间
            free_w = paper_width - display_width
            free_h = paper_height - display_height
            
            x_offset = int(free_w * image_item.offset_ratios[0])
            y_offset = int(free_h * image_item.offset_ratios[1])
            
            return QPoint(x_offset, y_offset)
        return QPoint(0, 0)

    def _update_paper_display(self):
        """更新纸张显示 - 优化版：使用缓存的缩放图片"""
        paper_width, paper_height = self._get_display_metrics()
        
        # 创建白色背景
        paper_pixmap = QPixmap(paper_width, paper_height)
        paper_pixmap.fill(Qt.white)
        
        painter = QPainter(paper_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, False) # 混合位图不需要抗锯齿
        
        for i, image_item in enumerate(self.images):
            if image_item.pixmap:
                # 计算目标显示大小
                target_width = int(image_item.pixmap.width() * image_item.image_scale_factor * self.DISPLAY_SCALE * self.scale_factor)
                target_height = int(image_item.pixmap.height() * image_item.image_scale_factor * self.DISPLAY_SCALE * self.scale_factor)
                
                # 更新尺寸记录
                image_item.display_width_on_widget = target_width
                image_item.display_height_on_widget = target_height
                
                # 获取缓存的缩放后图片 (避免每帧都进行高质量缩放)
                scaled_image = image_item.get_scaled_pixmap(target_width, target_height)
                
                # 计算偏移
                image_offset = self._get_image_offset_from_ratios(image_item)
                image_item.image_offset = image_offset
                
                # 绘制图片
                painter.drawPixmap(image_offset, scaled_image)
                
                # 选中框绘制 (移动模式下)
                if self.image_move_mode and i == self.selected_image_index:
                    painter.save()
                    pen = QPen(QColor(0, 120, 215), 2, Qt.DashLine)
                    painter.setPen(pen)
                    # 绘制外框
                    painter.drawRect(image_offset.x(), image_offset.y(), target_width, target_height)
                    painter.restore()
                
        painter.end()
        
        self.setPixmap(paper_pixmap)
        self.resize(paper_pixmap.size())

    def apply_zoom(self, factor, mouse_pos=None):
            if not self.pixmap() or not self.images:
                return

            scroll_area = self.get_scroll_area()
            
            # 1. 计算动态的最小缩放比例 (Fit Window)
            min_scale = 0.1 # 默认保底值
            if scroll_area:
                vp = scroll_area.viewport()
                # 获取视口当前的像素尺寸
                vp_w = vp.width()
                vp_h = vp.height()
                
                # 计算纸张在 scale=1.0 时的基准像素尺寸
                base_w = self.paper_settings["width_mm"] * self.DISPLAY_SCALE
                base_h = self.paper_settings["height_mm"] * self.DISPLAY_SCALE
                
                if base_w > 0 and base_h > 0:
                    # 计算宽和高的适配比例
                    ratio_w = vp_w / base_w
                    ratio_h = vp_h / base_h
                    # 取较小值，确保纸张完全显示在窗口内（顶住两边）
                    min_scale = min(ratio_w, ratio_h)

            # 2. 记录旧状态
            old_factor = self.scale_factor
            
            # 3. 计算新比例并应用限制
            new_factor = self.scale_factor * factor
            
            # 【关键修改2】将下限设置为动态计算出的 min_scale
            # 上限保持 5.0 或更高都可以
            self.scale_factor = max(min_scale, min(5.0, new_factor))
            
            # 4. 计算实际生效的倍率 (用于修正鼠标位置)
            if old_factor == 0: return
            real_factor = self.scale_factor / old_factor

            # 5. 执行以鼠标为中心的缩放逻辑
            if scroll_area and mouse_pos:
                hbar = scroll_area.horizontalScrollBar()
                vbar = scroll_area.verticalScrollBar()
                
                new_h_val = hbar.value() + mouse_pos.x() * (real_factor - 1)
                new_v_val = vbar.value() + mouse_pos.y() * (real_factor - 1)
                
                self._update_paper_display()
                self.update()
                
                hbar.setValue(int(new_h_val))
                vbar.setValue(int(new_v_val))
            else:
                # 无鼠标位置时的 Fallback 逻辑
                old_paper_w = int(self.paper_settings["width_mm"] * self.DISPLAY_SCALE * old_factor)
                old_paper_h = int(self.paper_settings["height_mm"] * self.DISPLAY_SCALE * old_factor)
                
                h_ratio = 0
                v_ratio = 0
                if scroll_area:
                    h_ratio = scroll_area.horizontalScrollBar().value() / old_paper_w if old_paper_w > 0 else 0
                    v_ratio = scroll_area.verticalScrollBar().value() / old_paper_h if old_paper_h > 0 else 0

                self._update_paper_display()
                self.update()

                if scroll_area:
                    new_paper_w = int(self.paper_settings["width_mm"] * self.DISPLAY_SCALE * self.scale_factor)
                    new_paper_h = int(self.paper_settings["height_mm"] * self.DISPLAY_SCALE * self.scale_factor)
                    scroll_area.horizontalScrollBar().setValue(int(h_ratio * new_paper_w))
                    scroll_area.verticalScrollBar().setValue(int(v_ratio * new_paper_h))

            self.scale_changed.emit(self.scale_factor)
    def wheelEvent(self, event):
            if not self.pixmap():
                return
            
            # 【关键修改1】显式接受事件，阻止事件传递给 QScrollArea 导致滚动
            event.accept()
            
            pos = event.position().toPoint()
            if event.angleDelta().y() > 0:
                self.apply_zoom(1.1, pos)
            else:
                self.apply_zoom(0.9, pos)

    def reset_zoom(self):
        if not self.images:
            return
        self.scale_factor = 1.0
        self._update_paper_display()
        self.update()
        self.scale_changed.emit(1.0)

    def set_drawing_enabled(self, enabled: bool, mode=None, clear_previous=False):
        self.allow_drawing = enabled
        if mode:
            self.draw_mode = mode
        if clear_previous and self.selected_image_index >= 0:
            image_item = self.images[self.selected_image_index]
            image_item.lines.clear()
            image_item.gradients.clear()
            
        self.temp_start = None
        self.temp_end = None
        self.drawing_active = False
        
        if enabled:
            self.setCursor(Qt.CrossCursor)
        elif not self.image_move_mode:
            self.setCursor(Qt.ArrowCursor)
        
        self.update()

    def set_image_move_mode(self, enabled: bool):
        self.image_move_mode = enabled
        if enabled:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self.image_dragging = False
        self._update_paper_display()
        self.update()

    def _get_scale_ratio(self, image_index):
        """获取 图像像素 -> 屏幕像素 的比例"""
        if not (0 <= image_index < len(self.images)):
            return 1.0
        image_item = self.images[image_index]
        return image_item.image_scale_factor * self.DISPLAY_SCALE * self.scale_factor

    def _screen_to_image_coords(self, screen_x, screen_y, image_index):
        """将屏幕坐标转换为指定图片的坐标（原始像素单位）"""
        if not (0 <= image_index < len(self.images)):
            return (0, 0)
            
        image_item = self.images[image_index]
        scale_ratio = self._get_scale_ratio(image_index)
        
        if scale_ratio == 0: return (0, 0)

        img_x = (screen_x - image_item.image_offset.x()) / scale_ratio
        img_y = (screen_y - image_item.image_offset.y()) / scale_ratio
        return (img_x, img_y)

    def _image_to_screen_coords(self, img_x, img_y, image_index):
        """将指定图片的坐标（原始像素单位）转换为屏幕坐标"""
        if not (0 <= image_index < len(self.images)):
            return (0, 0)
            
        image_item = self.images[image_index]
        scale_ratio = self._get_scale_ratio(image_index)
        
        screen_x = img_x * scale_ratio + image_item.image_offset.x()
        screen_y = img_y * scale_ratio + image_item.image_offset.y()
        return (screen_x, screen_y)

    def _get_snapped_image_coords(self, pos, image_index, threshold=None):
        """
        坐标吸附逻辑
        返回: (snapped_img_x, snapped_img_y, hovered_edge_x, hovered_edge_y)
        """
        if not (0 <= image_index < len(self.images)):
            return (0, 0, None, None)
        
        if threshold is None:
            threshold = self.edge_snap_threshold_drag
            
        image_item = self.images[image_index]
        if not image_item.pixmap:
            raw_x, raw_y = self._screen_to_image_coords(pos.x(), pos.y(), image_index)
            return (raw_x, raw_y, None, None)
            
        img_x, img_y = self._screen_to_image_coords(pos.x(), pos.y(), image_index)
        
        offset = image_item.image_offset
        w = image_item.display_width_on_widget
        h = image_item.display_height_on_widget
        x, y = pos.x(), pos.y()
        
        snapped_img_x = img_x
        snapped_img_y = img_y
        hovered_edge_x = None
        hovered_edge_y = None
        
        pixmap_w = image_item.pixmap.width()
        pixmap_h = image_item.pixmap.height()
        
        # 检查 X 边缘
        if abs(x - offset.x()) < threshold:
            snapped_img_x = 0
            hovered_edge_x = 'left'
        elif abs(x - (offset.x() + w)) < threshold:
            snapped_img_x = pixmap_w
            hovered_edge_x = 'right'
            
        # 检查 Y 边缘
        if abs(y - offset.y()) < threshold:
            snapped_img_y = 0
            hovered_edge_y = 'top'
        elif abs(y - (offset.y() + h)) < threshold:
            snapped_img_y = pixmap_h
            hovered_edge_y = 'bottom'
            
        return (snapped_img_x, snapped_img_y, hovered_edge_x, hovered_edge_y)

    def leaveEvent(self, event):
        if self.allow_drawing:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def _is_point_on_image(self, point, image_index):
        if not (0 <= image_index < len(self.images)):
            return False
            
        image_item = self.images[image_index]
        if not image_item.pixmap:
            return False
        
        rect = QRectF(
            image_item.image_offset.x(),
            image_item.image_offset.y(),
            image_item.display_width_on_widget,
            image_item.display_height_on_widget
        )
        return rect.contains(point.x(), point.y())

    def _get_image_at_point(self, point):
        # 从上到下查找（后添加的在上层）
        for i in range(len(self.images) - 1, -1, -1):
            if self._is_point_on_image(point, i):
                return i
        return -1

    def _apply_warp_cursor(self, pos, active_image_index, threshold):
            """
            核心修复：独立计算X和Y轴的最近边缘，防止互相干扰。
            """
            # 1. 初始化目标坐标为鼠标原始坐标
            target_x = pos.x()
            target_y = pos.y()
            warped = False
            
            # 记录找到的最近边缘距离
            min_dist_x = threshold
            min_dist_y = threshold
            
            # 2. 遍历所有图片检查边缘 (全局吸附)
            for i, img in enumerate(self.images):
                if not img.pixmap: continue
                
                # 获取该图片的屏幕显示区域
                left = img.image_offset.x()
                top = img.image_offset.y()
                right = left + img.display_width_on_widget
                bottom = top + img.display_height_on_widget
                
                # --- 检查 X 轴 (左/右) ---
                dist_left = abs(pos.x() - left)
                if dist_left < min_dist_x:
                    target_x = left
                    min_dist_x = dist_left
                    warped = True
                
                dist_right = abs(pos.x() - right)
                if dist_right < min_dist_x:
                    target_x = right
                    min_dist_x = dist_right
                    warped = True
                    
                # --- 检查 Y 轴 (上/下) ---
                dist_top = abs(pos.y() - top)
                if dist_top < min_dist_y:
                    target_y = top
                    min_dist_y = dist_top
                    warped = True
                    
                dist_bottom = abs(pos.y() - bottom)
                if dist_bottom < min_dist_y:
                    target_y = bottom
                    min_dist_y = dist_bottom
                    warped = True
            
            # 3. 构造最终屏幕坐标
            final_screen_pos = QPoint(int(target_x), int(target_y))
            
            # 4. 转换为当前选中图片的局部坐标 (用于画线计算)
            # 注意：如果 active_image_index 无效，这会返回(0,0)，导致画不出线，所以在 mousePress 中必须确保选中
            final_img_x, final_img_y = self._screen_to_image_coords(
                final_screen_pos.x(), final_screen_pos.y(), active_image_index
            )
                
            return final_screen_pos, final_img_x, final_img_y, warped

    def mousePressEvent(self, event: QMouseEvent):
        if not self.pixmap():
            return
            
        pos = event.position().toPoint()
        
        if event.button() == Qt.LeftButton:
            # 1. 图片移动模式逻辑
            if self.image_move_mode:
                clicked_idx = self._get_image_at_point(pos)
                if clicked_idx >= 0:
                    self.selected_image_index = clicked_idx
                    self.image_dragging = True
                    self.image_drag_start_pos = pos
                    
                    image_item = self.images[self.selected_image_index]
                    self.original_offset_ratios = image_item.offset_ratios
                    self.original_image_offset = QPoint(image_item.image_offset)
                    
                    self.setCursor(Qt.ClosedHandCursor)
                    self._update_paper_display()
                    self.update()
                return
                
            # 2. 图片选择逻辑 (增强版：防止点击边缘时选不中)
            clicked_idx = self._get_image_at_point(pos)
            
            # 如果没点中任何图片内部，尝试检测是不是点在了边缘附近
            if clicked_idx < 0:
                best_dist = self.edge_snap_threshold_press * 2 # 稍微放宽一点选择范围
                for i, img in enumerate(self.images):
                    if not img.pixmap: continue
                    rect = QRectF(img.image_offset.x(), img.image_offset.y(), 
                                img.display_width_on_widget, img.display_height_on_widget)
                    # 扩大矩形检测
                    if rect.adjusted(-best_dist, -best_dist, best_dist, best_dist).contains(pos.x(), pos.y()):
                        clicked_idx = i
                        break
            
            if clicked_idx >= 0:
                self.selected_image_index = clicked_idx
                self.update()
            
            # 3. 画布拖动逻辑 (如果不允许画图)
            if not self.allow_drawing:
                self.dragging = True
                self.last_mouse_pos = event.globalPosition().toPoint()
                return
                
            # 4. 画图初始化逻辑
            if self.selected_image_index >= 0:
                self.last_warped_pos = None 
                
                # 计算起点 (带吸附)
                new_pos, fx, fy, warped = self._apply_warp_cursor(pos, self.selected_image_index, self.edge_snap_threshold_press)
                
                if warped:
                    self.last_warped_pos = new_pos
                    QCursor.setPos(self.mapToGlobal(new_pos))
                
                # [关键] 同时初始化 temp_start 和 temp_end，确保一开始 paintEvent 就能画出一个点
                self.temp_start = (fx, fy)
                self.temp_end = (fx, fy) 
                self.drawing_active = True
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        
        # 0. 防抖动逻辑：如果是代码 setPos 触发的事件，直接忽略
        if self.last_warped_pos and pos == self.last_warped_pos:
            self.last_warped_pos = None
            return
        
        # 1. 图片拖动
        if self.image_dragging and self.image_move_mode and self.selected_image_index >= 0:
            image_item = self.images[self.selected_image_index]
            if image_item.pixmap:
                paper_width, paper_height = self._get_display_metrics()
                display_width = image_item.display_width_on_widget
                display_height = image_item.display_height_on_widget
                
                free_w = paper_width - display_width
                free_h = paper_height - display_height
                
                delta = pos - self.image_drag_start_pos
                new_x = self.original_image_offset.x() + delta.x()
                new_y = self.original_image_offset.y() + delta.y()
                
                if free_w > 0:
                    new_x = max(0, min(new_x, free_w))
                    x_ratio = new_x / free_w
                else:
                    x_ratio = 0.0
                
                if free_h > 0:
                    new_y = max(0, min(new_y, free_h))
                    y_ratio = new_y / free_h
                else:
                    y_ratio = 0.0
                
                image_item.offset_ratios = (x_ratio, y_ratio)
                self._update_paper_display() 
                self.update()
            return
            
        # 2. 绘图过程
        if self.temp_start and self.allow_drawing and self.drawing_active and self.selected_image_index >= 0:
            new_pos, fx, fy, warped = self._apply_warp_cursor(pos, self.selected_image_index, self.edge_snap_threshold_drag)
            
            if warped:
                # [关键] 只有位置真的变了才 setPos，彻底解决抖动
                if new_pos != pos:
                    self.last_warped_pos = new_pos
                    QCursor.setPos(self.mapToGlobal(new_pos))
            else:
                self.last_warped_pos = None
            
            # 计算终点
            dx = fx - self.temp_start[0]
            dy = fy - self.temp_start[1]
            dx, dy = snap_angle(dx, dy, threshold_deg=1)
            
            # [关键] 更新 temp_end 并请求重绘
            self.temp_end = (self.temp_start[0] + dx, self.temp_start[1] + dy)
            self.update()

        # 3. 画布平移
        elif self.dragging and self.last_mouse_pos:
            delta = event.globalPosition().toPoint() - self.last_mouse_pos
            scroll_area = self.get_scroll_area()
            if scroll_area:
                scroll_area.horizontalScrollBar().setValue(scroll_area.horizontalScrollBar().value() - delta.x())
                scroll_area.verticalScrollBar().setValue(scroll_area.verticalScrollBar().value() - delta.y())
            self.last_mouse_pos = event.globalPosition().toPoint()
            
        # 4. 悬停预览
        elif self.allow_drawing and self.selected_image_index >= 0 and not self.image_dragging:
            new_pos, _, _, warped = self._apply_warp_cursor(pos, self.selected_image_index, self.edge_snap_threshold_drag)
            
            if warped:
                if new_pos != pos:
                    self.last_warped_pos = new_pos
                    QCursor.setPos(self.mapToGlobal(new_pos))
            else:
                self.last_warped_pos = None
                
            if not self.image_move_mode:
                self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.image_dragging:
                self.image_dragging = False
                self.setCursor(Qt.OpenHandCursor)
                return
                
            # 绘图结束逻辑
            if self.allow_drawing and self.temp_start and self.drawing_active and self.selected_image_index >= 0:
                pos = event.position().toPoint()
                self.last_warped_pos = None
                
                # 获取最终坐标 (使用 drag 阈值，保证释放时也能吸附)
                _, fx, fy, _ = self._apply_warp_cursor(pos, self.selected_image_index, self.edge_snap_threshold_drag) 
                
                dx = fx - self.temp_start[0]
                dy = fy - self.temp_start[1]
                dx, dy = snap_angle(dx, dy, threshold_deg=1)
                
                self.temp_end = (self.temp_start[0] + dx, self.temp_start[1] + dy)
                self.drawing_active = False # 停止动态更新，但 temp_start/end 保留，等待确认
                
                if not self.image_move_mode:
                    self.setCursor(Qt.CrossCursor) 
                
                self.update()
                
            self.dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if not self.pixmap() or not self.images:
            return
            
        click_pos = event.position().toPoint()
        image_index = self._get_image_at_point(click_pos)
        if image_index < 0:
            return
            
        self.selected_image_index = image_index
        self._update_paper_display()
        self.update()
        
        image_item = self.images[image_index]
        
        for i, line in enumerate(image_item.lines):
            if self._is_point_near_line(click_pos, line, image_index, tolerance=15):
                self._open_length_dialog(i, "line", line, image_index)
                return
                
        for i, gradient in enumerate(image_item.gradients):
            if self._is_point_near_line(click_pos, gradient, image_index, tolerance=15):
                self._open_length_dialog(i, "gradient", gradient, image_index)
                return

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.temp_start and self.temp_end and self.allow_drawing:
                self.confirm_line()
                return
        super().keyPressEvent(event)

    def show_context_menu(self, position):
        if not self.images:
            return
        
        local_point = QPoint(position)
        clicked_image_index = self._get_image_at_point(local_point)
        if clicked_image_index >= 0:
            self.selected_image_index = clicked_image_index
            self._update_paper_display()
            self.update()
            self.context_menu.exec(self.mapToGlobal(position))

    def delete_selected_image(self):
        if 0 <= self.selected_image_index < len(self.images):
            reply = QMessageBox.question(
                self, "确认删除", "确定要删除这张图片吗？", 
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self._delete_image(self.selected_image_index)

    def _is_point_near_line(self, point, line, image_index, tolerance=15):
        start = line["start"]
        end = line["end"]
        
        sp_x, sp_y = self._image_to_screen_coords(start[0], start[1], image_index)
        ep_x, ep_y = self._image_to_screen_coords(end[0], end[1], image_index)
        
        sp = QPoint(int(sp_x), int(sp_y))
        ep = QPoint(int(ep_x), int(ep_y))
        
        distance = point_to_line_distance(point, sp, ep)
        return distance <= tolerance

    def _open_length_dialog(self, index, line_type, line, image_index):
        dialog = LengthInputDialog(self)
        if "real_length" in line:
            original_value = line.get("original_value", line["real_length"])
            original_unit = line.get("original_unit", "mm")
            dialog.set_length(str(original_value))
            dialog.set_unit(original_unit)
            
        if dialog.exec() == QDialog.Accepted:
            try:
                length_value = float(dialog.get_length())
                unit = dialog.get_unit()
                
                real_length_mm = length_value
                if unit == "cm":
                    real_length_mm = length_value * 10
                elif unit == "inch":
                    real_length_mm = length_value * 25.4
                
                image_item = self.images[image_index]
                target_list = image_item.lines if line_type == "line" else image_item.gradients
                
                target_list[index]["real_length"] = real_length_mm
                target_list[index]["original_value"] = length_value
                target_list[index]["original_unit"] = unit
                
                self._adjust_image_scale(line, real_length_mm, image_index)
                self.update()
            except ValueError:
                QMessageBox.warning(self, "输入错误", "请输入有效的数字")

    def _adjust_image_scale(self, line, real_length_mm, image_index):
        pixel_length = math.dist(line["start"], line["end"])
        if pixel_length <= 0:
            return
            
        new_scale = real_length_mm / pixel_length
        
        if image_index >= 0:
            image_item = self.images[image_index]
            image_item.image_scale_factor = new_scale
            self._update_paper_display()
            self.window().statusBar().showMessage(f"图片已根据参考长度调整缩放: 1像素 = {new_scale:.4f}毫米")

    def confirm_line(self):
        if self.temp_start and self.temp_end and self.selected_image_index >= 0:
            new_line = {"start": self.temp_start, "end": self.temp_end, "scale_ratio": None}
            image_item = self.images[self.selected_image_index]
            
            target_list = image_item.lines if self.draw_mode == "single" else image_item.gradients
            target_list.append(new_line)
            
            self._open_length_dialog_for_new_line(len(target_list) - 1, self.draw_mode, new_line, self.selected_image_index)
            
        self.temp_start = None
        self.temp_end = None
        self.allow_drawing = False
        self.drawing_active = False
        self.update()
        if self.btn_confirm: 
            self.btn_confirm.hide()

    def _open_length_dialog_for_new_line(self, index, line_type, line, image_index):
        type_str = "line" if line_type == "single" or line_type == "line" else "gradient"
        self._open_length_dialog(index, type_str, line, image_index)

    def _delete_image(self, image_index):
        if 0 <= image_index < len(self.images):
            del self.images[image_index]
            if self.selected_image_index == image_index:
                self.selected_image_index = -1
            elif self.selected_image_index > image_index:
                self.selected_image_index -= 1
            self._update_paper_display()
            self.update()
            
            if not self.images:
                if self.btn_confirm_move: self.btn_confirm_move.hide()
                if self.btn_confirm: self.btn_confirm.hide()

    def paintEvent(self, event):
        if not self.pixmap():
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # 绘制底图（包含白纸和已经定位的图片）
        painter.drawPixmap(0, 0, self.pixmap())
        
        pen = QPen(self.line_color, 2)
        painter.setPen(pen)
        
        # 绘制线条
        for image_index, image_item in enumerate(self.images):
            for line in image_item.lines:
                self._draw_line_with_arrows(painter, line["start"], line["end"], image_index)
                if "real_length" in line:
                    self._draw_length_text(painter, line, image_index)
                    
            for g in image_item.gradients:
                self._draw_line_with_arrows(painter, g["start"], g["end"], image_index)
                self._draw_gradient_like(painter, g["start"], g["end"], image_index)
                if "real_length" in g:
                    self._draw_length_text(painter, g, image_index)
                
        if self.temp_start and self.temp_end and self.selected_image_index >= 0:
            self._draw_line_with_arrows(painter, self.temp_start, self.temp_end, self.selected_image_index)
            if self.draw_mode == "gradient":
                self._draw_gradient_like(painter, self.temp_start, self.temp_end, self.selected_image_index)

        painter.end()

    def _draw_line_with_arrows(self, painter, start, end, image_index, arrow_size=10):
        sp_x, sp_y = self._image_to_screen_coords(start[0], start[1], image_index)
        ep_x, ep_y = self._image_to_screen_coords(end[0], end[1], image_index)
        
        sp = QPoint(int(sp_x), int(sp_y))
        ep = QPoint(int(ep_x), int(ep_y))
        
        painter.drawLine(sp, ep)
        
        dx, dy = ep.x()-sp.x(), ep.y()-sp.y()
        length = math.hypot(dx, dy) or 1
        ux, uy = dx/length, dy/length
        
        perp1_x, perp1_y = -uy, ux
        perp2_x, perp2_y = uy, -ux
        
        def draw_tip(point, is_start):
            direction = 1 if is_start else -1
            
            tip_x = point.x() - ux * arrow_size * direction
            tip_y = point.y() - uy * arrow_size * direction
            
            wing1_x = tip_x + perp1_x * arrow_size * 0.5
            wing1_y = tip_y + perp1_y * arrow_size * 0.5
            wing2_x = tip_x + perp2_x * arrow_size * 0.5
            wing2_y = tip_y + perp2_y * arrow_size * 0.5
            
            painter.drawLine(point, QPoint(int(wing1_x), int(wing1_y)))
            painter.drawLine(point, QPoint(int(wing2_x), int(wing2_y)))
            
        draw_tip(sp, True)   
        draw_tip(ep, False) 

    def _draw_gradient_like(self, painter, start, end, image_index, extend=2000):
        sp_x, sp_y = self._image_to_screen_coords(start[0], start[1], image_index)
        ep_x, ep_y = self._image_to_screen_coords(end[0], end[1], image_index)
        
        sp = QPoint(int(sp_x), int(sp_y))
        ep = QPoint(int(ep_x), int(ep_y))
        
        dx, dy = ep.x()-sp.x(), ep.y()-sp.y()
        length = math.hypot(dx, dy) or 1
        
        # Normal vector
        nx, ny = -dy/length, dx/length
        
        ext_vec = QPoint(int(nx*extend), int(ny*extend))
        
        painter.drawLine(sp + ext_vec, sp - ext_vec)
        painter.drawLine(ep + ext_vec, ep - ext_vec)

    def _draw_length_text(self, painter, line, image_index):
        if "real_length" not in line:
            return
            
        if "original_value" in line and "original_unit" in line:
            txt = f"{line['original_value']:.2f} {line['original_unit']}"
        else:
            txt = f"{line['real_length']:.2f} mm"
            
        p1, p2 = line["start"], line["end"]
        sp_x, sp_y = self._image_to_screen_coords(p1[0], p1[1], image_index)
        ep_x, ep_y = self._image_to_screen_coords(p2[0], p2[1], image_index)
        
        midx = (sp_x + ep_x) / 2
        midy = (sp_y + ep_y) / 2
        
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(txt)
        text_height = font_metrics.height()
        
        painter.drawText(int(midx - text_width/2), int(midy + text_height/4), txt) 

    def export_to_pdf(self, file_path, paper_settings):
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setResolution(600)  # 设置分辨率为600dpi
            
            size_map = {
                "A4": QPageSize.A4, "A3": QPageSize.A3, "A5": QPageSize.A5,
                "Letter": QPageSize.Letter, "Legal": QPageSize.Legal
            }
            page_size_id = size_map.get(paper_settings["size_name"], QPageSize.A4)
            page_size = QPageSize(page_size_id)
            
            printer.setPageSize(page_size)
            printer.setPageOrientation(QPageLayout.Portrait if paper_settings["is_portrait"] else QPageLayout.Landscape)
            
            painter = QPainter()
            if not painter.begin(printer):
                return False
                
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            
            dpi = printer.resolution()  # 现在应该是600
            page_rect = printer.pageRect(QPrinter.DevicePixel)
            page_width_px = page_rect.width()
            page_height_px = page_rect.height()
            
            for image_item in self.images:
                if image_item.pixmap:
                    img_width_mm = image_item.pixmap.width() * image_item.image_scale_factor
                    img_height_mm = image_item.pixmap.height() * image_item.image_scale_factor
                    
                    display_width = int(img_width_mm * dpi / 25.4)
                    display_height = int(img_height_mm * dpi / 25.4)
                    
                    # 导出时使用高质量缩放
                    scaled_image = image_item.pixmap.scaled(
                        display_width, display_height, 
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    
                    # 剩余空间 = page - display
                    free_w = page_width_px - display_width
                    free_h = page_height_px - display_height
                    
                    # 使用保存的 ratio 计算 offset
                    # x_offset = free_w * ratio
                    x_offset = int(free_w * image_item.offset_ratios[0])
                    y_offset = int(free_h * image_item.offset_ratios[1])
                    
                    # 确保 offset 不会太离谱 (虽然理论上 ratio 0-1 没问题)
                    x_offset = max(0, min(x_offset, page_width_px))
                    y_offset = max(0, min(y_offset, page_height_px))
                    
                    painter.drawPixmap(x_offset, y_offset, scaled_image)
            
            painter.end()
            return True
        except Exception as e:
            print(f"导出PDF时出错: {e}")
            return False