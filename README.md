# 🧭 OpenScaler

> 🖼️ 让你的图片“按真实尺寸”打印的智能标尺工具

---

## 🌟 简介 | Introduction

你还在为无法快速打印出想要尺寸的图片、图标、证件照或贴纸而烦恼吗？  
**OpenScaler** 提供了一种极其简单的解决方案：

1. 导入图片  
2. 标记两个已知真实距离的关键点（如证件照的两脚），画出一条线段  
3. 输入想要在现实中呈现的尺寸  
4. OpenScaler 会自动校准比例、缩放图像  
5. 一键生成尺寸精确的 **PDF 打印文件**

最终，你可直接打印出符合现实尺寸的照片、贴纸或图标，无需反复调整！

---

Are you frustrated by not being able to quickly print images, icons, ID photos, or stickers in your desired real-world size?  
**OpenScaler** offers an extremely simple solution:

1. Import an image  
2. Mark two key points with a known real-world distance (e.g., the edges of an ID photo) and draw a line between them  
3. Enter the desired real-world size  
4. OpenScaler automatically calibrates scale and resizes the image accordingly  
5. With one click, generate a **PDF file** ready for printing with accurate dimensions  

You can directly print photos, stickers, or icons that match real-world measurements — no more tedious trial and error!

---

## 🧩 功能特性 | Features

✅ 简单直观的图形化界面  
✅ 精确的比例标定（双点标尺）  
✅ 支持多种单位（mm / cm / inch）  
✅ 自动生成可直接打印的 PDF 文件  
✅ 可标注距离、平行线距  
✅ 支持导出多种纸张尺寸（A4、A5、4x6 等） 

✅ Simple and intuitive graphical interface  
✅ Accurate scale calibration using two-point reference  
✅ Supports multiple units (mm / cm / inch)  
✅ Automatically generates print-ready PDF files  
✅ Allows annotation of distances and parallel spacing   
✅ Supports exporting to multiple paper sizes (A4, A5, 4x6, etc.)  

---

## 🚀 快速开始 | Quick Start

### 🧱 安装依赖 | Installation

确保您的系统已安装 **Python 3.7+**。  
Make sure your system has **Python 3.7 or higher** installed.  

```bash
# 克隆项目 | Clone the project
git clone https://github.com/yourusername/OpenScaler.git
cd OpenScaler

# 安装依赖 | Install dependencies
pip install PySide6
```

---

### ▶️ 运行程序 | Run the Application

安装完成后，通过以下命令启动程序：  
After installation, run the application with:  

```bash
python OpenScaler.py
```

---

## 📘 使用指南 | User Guide

### 🖼️ 1. 加载图片 | Load Images

- 点击 “添加照片” 按钮或菜单栏 “文件 > 打开图片”  
- 选择 PNG / JPG / BMP / JPEG 格式的文件  
- 图片加载后可拖拽调整位置  

- Click the **“Add Photo”** button or go to **File > Open Image**  
- Supports PNG, JPG, BMP, JPEG formats  
- After loading, drag to reposition the image  

---

### 📄 2. 页面设置 | Page Setup

- 通过菜单 “页面 > 页面设置” 调整纸张尺寸和方向  
- 支持 A4、A3、A5、Letter、Legal 等标准尺寸  
- 可选择纵向或横向布局  

- Use **Page > Page Setup** to adjust paper size and orientation  
- Supports A4, A3, A5, Letter, and Legal  
- Choose between portrait or landscape  

---

### 🔍 3. 图片调整 | Image Adjustment

- 图片加载后可自由拖拽移动  
- 点击 “确认移动” 固定图片位置  
- 使用菜单 “视图 > 放大 / 缩小” 或滚轮调整显示比例  
- 点击 “还原” 恢复默认缩放  

- Drag to reposition the image after loading  
- Click **“Confirm Move”** to fix its position  
- Use **View > Zoom In / Zoom Out** or scroll wheel to adjust zoom  
- Click **“Reset”** to restore the default scale  

---

### 📏 4. 测量功能 | Measurement Tools

#### ➖ 单线测量 | Single Line Measurement
- 选择 “添加测量 > 单线测量”  
- 点击并拖拽绘制测量线  
- 点击 “确认画线” 完成绘制  

- Select **Add Measurement > Single Line**  
- Click and drag to draw a measurement line  
- Click **Confirm Line** to finish drawing  

#### ⫷ 平行线测量 | Parallel Line Measurement
- 选择 “添加测量 > 平行线测量”  
- 拖拽绘制测量线，自动显示平行辅助线  
- 点击 “确认画线” 完成绘制  

- Select **Add Measurement > Parallel Lines**  
- Click and drag to draw; parallel guide lines appear automatically  
- Click **Confirm Line** to finish drawing  

---

### 📐 5. 设置实际长度 | Set Real Length

- 双击线条，在弹窗中输入实际长度  
- 支持单位：毫米(mm)、厘米(cm)、英寸(inch)  
- 程序自动根据输入校准比例  

- Double-click a line to input the real length  
- Supports mm, cm, and inch  
- The app recalibrates automatically based on your input  

---

### 🧾 6. 导出 PDF | Export to PDF

- 测量和校准完成后，选择 “文件 > 导出为 PDF”  
- 选择保存路径和文件名  
- 程序生成尺寸精确的 PDF，可直接打印  

- After finishing calibration, go to **File > Export as PDF**  
- Choose save location and filename  
- The generated PDF preserves accurate real-world dimensions  

---

## 🤝 贡献与反馈 | Contributing

欢迎开发者与设计师参与改进 **OpenScaler**！  
We welcome contributions and ideas from the community.  


## 🪪 许可证 | License

本项目采用 **MIT License** 开源协议。  
You are free to use, modify, and distribute the code under the **MIT License**.  