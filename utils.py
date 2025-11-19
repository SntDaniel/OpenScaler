# utils.py
# 包含通用的工具函数
import math
from PySide6.QtCore import QPointF

def snap_angle(dx, dy, threshold_deg=1):
    """
    将角度吸附到水平或垂直方向
    :param dx: x分量
    :param dy: y分量
    :param threshold_deg: 吸附阈值（度）
    """
    if dx == 0 and dy == 0:
        return (dx, dy)
    
    ang = math.degrees(math.atan2(dy, dx))
    abs_ang = abs(ang)
    
    # 吸附到水平 (0 或 180 度)
    if abs_ang < threshold_deg or abs(abs_ang - 180) < threshold_deg:
        return (dx, 0)
    
    # 吸附到垂直 (90 或 -90 度)
    if abs(abs_ang - 90) < threshold_deg:
        return (0, dy)
        
    return (dx, dy)


def point_to_line_distance(point, line_start, line_end):
    """
    计算点到线段的最短距离
    """
    x, y = point.x(), point.y()
    x1, y1 = line_start.x(), line_start.y()
    x2, y2 = line_end.x(), line_end.y()
    
    dx_line = x2 - x1
    dy_line = y2 - y1
    
    # 线段长度的平方
    len_sq = dx_line * dx_line + dy_line * dy_line
    
    if len_sq == 0:
        # 线段是一个点
        return math.hypot(x - x1, y - y1)

    # 投影参数 t
    # t = ((p - p1) . (p2 - p1)) / |p2 - p1|^2
    t = ((x - x1) * dx_line + (y - y1) * dy_line) / len_sq

    if t < 0:
        # 最近点是 start
        closest_x, closest_y = x1, y1
    elif t > 1:
        # 最近点是 end
        closest_x, closest_y = x2, y2
    else:
        # 最近点在线段上
        closest_x = x1 + t * dx_line
        closest_y = y1 + t * dy_line

    return math.hypot(x - closest_x, y - closest_y)