# 包含通用的工具函数
import math
from PySide6.QtCore import QPoint


def snap_angle(dx, dy, threshold_deg=1):
    """将角度吸附到水平或垂直方向"""
    if dx == 0 and dy == 0:
        return (dx, dy)
    ang = math.degrees(math.atan2(dy, dx))
    if abs(ang) < threshold_deg or abs(abs(ang)-180) < threshold_deg:
        return (dx, 0)
    if abs(abs(ang)-90) < threshold_deg:
        return (0, dy)
    return (dx, dy)


def point_to_line_distance(point, line_start, line_end):
    """计算点到线段的最短距离"""
    x, y = point.x(), point.y()
    x1, y1 = line_start.x(), line_start.y()
    x2, y2 = line_end.x(), line_end.y()
    
    # 线段长度的平方
    A = x - x1
    B = y - y1
    C = x2 - x1
    D = y2 - y1

    dot = A * C + B * D
    len_sq = C * C + D * D
    if len_sq == 0:
        # 线段是一个点
        dist = math.sqrt(A * A + B * B)
        return dist

    param = dot / len_sq

    if param < 0:
        xx, yy = x1, y1
    elif param > 1:
        xx, yy = x2, y2
    else:
        xx = x1 + param * C
        yy = y1 + param * D

    dx = x - xx
    dy = y - yy
    dist = math.sqrt(dx * dx + dy * dy)
    return dist