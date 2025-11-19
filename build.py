# build.py
import os
import sys
from PyInstaller.__main__ import run

def main():
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
    
    # 设置基础参数
    opts = [
        'OpenScaler.py',  # 主程序入口
        '--windowed',     # 隐藏控制台窗口（GUI应用）
        '--onefile',      # 打包成单个文件
        '--name=OpenScaler',  # 可执行文件名称
        *icon_option,     # 图标选项
    ]
    
    # 添加数据文件
    icons_dir = os.path.join(current_dir, 'icons')
    if os.path.exists(icons_dir):
        opts.append(f'--add-data={icons_dir}{os.pathsep}icons')
    
    # 添加隐藏导入
    hidden_imports = [
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtPrintSupport',
    ]
    
    for imp in hidden_imports:
        opts.append(f'--hidden-import={imp}')
    
    # 排除不必要的模块以减小文件大小
    excluded_modules = [
        'tkinter',
        'unittest',
        'email',
        'xml',
        'html',
        'http',
        'PIL',  # 如果未使用PIL/Pillow
        'matplotlib',
        'numpy',
        'scipy',
        'pytest',
        'setuptools',
        'pip',
        'distutils',
    ]
    
    for module in excluded_modules:
        opts.append(f'--exclude-module={module}')
    
    # 清理临时文件
    opts.append('--clean')
    
    # 检查系统是否支持 strip 命令（Unix/Linux/macOS）
    def has_strip_command():
        if sys.platform.startswith('win'):
            return False
        try:
            import subprocess
            subprocess.run(['strip', '--version'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL,
                          check=True)
            return True
        except (FileNotFoundError, OSError, subprocess.CalledProcessError):
            return False
    
    # 只有在支持 strip 的系统上才添加 --strip 选项
    if has_strip_command():
        opts.append('--strip')  # 移除符号表和调试信息
    
    # 检查是否安装了 UPX 并可用
    def has_upx():
        try:
            import subprocess
            result = subprocess.run(['upx', '--version'], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL,
                                  check=True)
            return result.returncode == 0
        except (FileNotFoundError, OSError, subprocess.CalledProcessError):
            return False
    
    # 如果安装了 UPX，启用压缩
    if has_upx():
        opts.extend(['--upx-exclude=vcruntime140.dll'])
    
    print("正在打包应用，请稍候...")
    print(f"参数: {' '.join(opts)}")
    
    try:
        # 执行打包
        run(opts)
        print("打包完成！")
    except Exception as e:
        print(f"打包过程中出现错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()