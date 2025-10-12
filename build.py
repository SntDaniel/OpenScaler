import os
import sys
from PyInstaller.__main__ import run

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 构建图标文件路径
icon_path = os.path.join(current_dir, 'icons', 'icon.ico')

# 检查图标文件是否存在
if not os.path.exists(icon_path):
    print(f"警告: 图标文件 {icon_path} 不存在")
    icon_option = []  # 不使用图标
else:
    icon_option = [f'--icon={icon_path}']  # 使用图标

# 设置参数
opts = [
    'OpenScaler.py',  # 主程序入口
    '--windowed',     # 隐藏控制台窗口（GUI应用）
    '--onefile',      # 打包成单个文件
    '--name=OpenScaler',  # 可执行文件名称
    *icon_option,     # 图标选项
    '--add-data=main_window.py;.',  # 添加依赖文件
    '--add-data=image_label.py;.',
    '--add-data=dialogs.py;.',
    '--add-data=utils.py;.',
    '--add-data=icons;icons',  # 添加整个icons文件夹
    '--hidden-import=PySide6',
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets',
    '--hidden-import=PySide6.QtPrintSupport',
    '--clean'  # 清理临时文件
]

# 执行打包
run(opts)