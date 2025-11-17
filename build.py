# build.py
import os
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

# 检查系统是否支持 strip 命令
def has_strip_command():
    try:
        import subprocess
        subprocess.run(['strip', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (FileNotFoundError, OSError):
        return False

# 设置优化参数
opts = [
    'OpenScaler.py',  # 主程序入口
    '--windowed',     # 隐藏控制台窗口（GUI应用）
    '--onefile',      # 打包成单个文件
    '--name=OpenScaler',  # 可执行文件名称
    *icon_option,     # 图标选项
    '--add-data=icons;icons',  # 添加整个icons文件夹
    '--hidden-import=PySide6',
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets',
    '--hidden-import=PySide6.QtPrintSupport',
    # 排除不必要的模块
    '--exclude-module=tkinter',
    '--exclude-module=unittest',
    '--exclude-module=email',
    '--exclude-module=xml',
    '--exclude-module=html',
    '--exclude-module=http',
    '--exclude-module=PIL',
    '--exclude-module=matplotlib',
    '--exclude-module=numpy',
    '--exclude-module=scipy',
    '--clean'  # 清理临时文件
]

# 只有在支持 strip 的系统上才添加 --strip 选项
if has_strip_command():
    opts.append('--strip')  # 移除符号表和调试信息

# 如果安装了 UPX，启用压缩
try:
    import subprocess
    result = subprocess.run(['upx', '--version'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        opts.extend(['--upx-exclude=vcruntime140.dll'])
except (FileNotFoundError, OSError):
    print("未检测到 UPX，将不使用压缩")

# 执行打包
run(opts)