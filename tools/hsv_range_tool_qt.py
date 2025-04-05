from PyQt6.QtWidgets import (QApplication, QWidget, QMainWindow, QLabel, 
                           QHBoxLayout, QVBoxLayout, QPushButton, QSlider, QFileDialog, QSizePolicy, QFrame,
                           QLineEdit, QMessageBox)
from PyQt6.QtGui import QImage, QPixmap, QColor, QMouseEvent
from PyQt6.QtCore import Qt
import sys
import cv2
import numpy as np

class HSVRangeTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('HSV Range Tool')
        self.setMinimumSize(1200, 600)
        
        self.image = None
        self.hsv_image = None
        self.color_picker_mode = None  # 'min' 或 'max' 或 None
        
        self.init_ui()
        self.center_window()
        
    def init_ui(self):
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建控制面板
        control_panel = QWidget()
        control_panel.setFixedWidth(300)
        control_layout = QVBoxLayout(control_panel)
        
        # 添加载入图片按钮
        load_btn = QPushButton('载入图片')
        load_btn.clicked.connect(self.on_load_image)
        control_layout.addWidget(load_btn)
        
        # 在控制面板添加取色器按钮
        picker_layout = QHBoxLayout()
        self.picker_min_btn = QPushButton('取色器(MIN)')
        self.picker_max_btn = QPushButton('取色器(MAX)')
        self.picker_min_btn.clicked.connect(lambda: self.enable_color_picker('min'))
        self.picker_max_btn.clicked.connect(lambda: self.enable_color_picker('max'))
        picker_layout.addWidget(self.picker_min_btn)
        picker_layout.addWidget(self.picker_max_btn)
        control_layout.addLayout(picker_layout)
        
        # 添加模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式："))
        self.remove_color_btn = QPushButton("移除颜色")
        self.keep_color_btn = QPushButton("保留颜色")
        self.remove_color_btn.setCheckable(True)
        self.keep_color_btn.setCheckable(True)
        self.remove_color_btn.setChecked(True)  # 默认选中移除颜色
        self.keep_color_btn.setChecked(False)
        
        # 按钮互斥
        self.remove_color_btn.clicked.connect(self.on_mode_change)
        self.keep_color_btn.clicked.connect(self.on_mode_change)
        
        mode_layout.addWidget(self.remove_color_btn)
        mode_layout.addWidget(self.keep_color_btn)
        control_layout.addLayout(mode_layout)
        
        # 添加颜色预览框
        preview_layout = QHBoxLayout()
        self.min_color_preview = QFrame()
        self.max_color_preview = QFrame()
        for preview in (self.min_color_preview, self.max_color_preview):
            preview.setFixedSize(50, 50)
            preview.setFrameShape(QFrame.Shape.Box)
            preview.setStyleSheet("background-color: black;")
        preview_layout.addWidget(QLabel("Min Color:"))
        preview_layout.addWidget(self.min_color_preview)
        preview_layout.addWidget(QLabel("Max Color:"))
        preview_layout.addWidget(self.max_color_preview)
        control_layout.addLayout(preview_layout)
        
        # HSV 滑块标签
        hsv_labels = ['H min', 'S min', 'V min', 'H max', 'S max', 'V max']
        self.sliders = []
        self.value_edits = []
        
        # 创建 HSV 滑块
        for i, label in enumerate(hsv_labels):
            # 创建水平布局来放置标签、滑块和值编辑框
            slider_layout = QHBoxLayout()
            
            # 添加标签
            slider_label = QLabel(label)
            slider_label.setFixedWidth(50)
            slider_layout.addWidget(slider_label)
            
            # 创建滑块
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(255)  # 所有滑块最大值设为255
            if i % 3 == 0:  # H通道
                slider.setMaximum(179)
            if i == 3:  # H max 默认值设为179
                slider.setValue(179)
            elif i > 3:  # S max和V max默认值设为255
                slider.setValue(255)
            slider.valueChanged.connect(self.on_slider)
            slider_layout.addWidget(slider)
            
            # 添加值编辑框
            value_edit = QLineEdit(str(slider.value()))
            value_edit.setFixedWidth(40)
            value_edit.textChanged.connect(lambda text, s=slider: self.on_edit_change(text, s))
            slider_layout.addWidget(value_edit)
            
            self.sliders.append(slider)
            self.value_edits.append(value_edit)
            control_layout.addLayout(slider_layout)
        
        # 添加复制按钮
        copy_btn = QPushButton('复制HSV范围')
        copy_btn.clicked.connect(self.copy_hsv_range)
        control_layout.addWidget(copy_btn)
        
        # 创建图像显示标签
        self.image_label = QLabel()
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.image_label.mousePressEvent = self.on_image_click
        
        # 创建图片容器并设置布局
        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)
        image_layout.addWidget(self.image_label)
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(image_container, stretch=1)
        
        # 设置主布局的边距和间距
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
    def center_window(self):
        # 将窗口移到屏幕中央
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        screen_geometry = screen.geometry()
        size = self.geometry()
        self.move(
            (screen_geometry.width() - size.width()) // 2,
            (screen_geometry.height() - size.height()) // 2
        )
        
    def on_load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.jpg *.png)"
        )
        
        if file_name:
            self.image = cv2.imread(file_name)
            if self.image is not None:
                self.hsv_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV)
                self.update_image()
    
    def opencv_hsv_to_qt_hsv(self, h, s, v):
        # OpenCV 的 H 范围是 0-179，需要转换到 Qt 的 0-359
        h = int(h * 2)
        return h, s, v
    
    def qt_hsv_to_opencv_hsv(self, h, s, v):
        # Qt 的 H 范围是 0-359，需要转换到 OpenCV 的 0-179
        h = int(h / 2)
        return h, s, v
    
    def on_slider(self):
        # 更新值编辑框
        for i, (slider, edit) in enumerate(zip(self.sliders, self.value_edits)):
            edit.setText(str(slider.value()))
        
        # 更新颜色预览框
        h_min, s_min, v_min = [self.sliders[i].value() for i in range(3)]
        h_max, s_max, v_max = [self.sliders[i].value() for i in range(3, 6)]
        
        # 转换 OpenCV HSV 到 Qt HSV
        qt_h_min, qt_s_min, qt_v_min = self.opencv_hsv_to_qt_hsv(h_min, s_min, v_min)
        qt_h_max, qt_s_max, qt_v_max = self.opencv_hsv_to_qt_hsv(h_max, s_max, v_max)
        
        # 更新最小值颜色预览
        min_color = QColor()
        min_color.setHsv(qt_h_min, qt_s_min, qt_v_min)
        self.min_color_preview.setStyleSheet(f"background-color: {min_color.name()};")
        
        # 更新最大值颜色预览
        max_color = QColor()
        max_color.setHsv(qt_h_max, qt_s_max, qt_v_max)
        self.max_color_preview.setStyleSheet(f"background-color: {max_color.name()};")
        
        if self.image is not None:
            self.update_image()
    
    def enable_color_picker(self, mode):
        self.color_picker_mode = mode
        if mode == 'min':
            self.picker_min_btn.setStyleSheet('background-color: yellow')
            self.picker_max_btn.setStyleSheet('')
        else:
            self.picker_min_btn.setStyleSheet('')
            self.picker_max_btn.setStyleSheet('background-color: yellow')
    
    def on_image_click(self, ev: QMouseEvent | None) -> None:
        if ev is None or not self.color_picker_mode or self.hsv_image is None:
            return
            
        # 获取点击位置
        pixmap = self.image_label.pixmap()
        if pixmap:
            # 计算图像的实际显示位置和缩放比例
            label_size = self.image_label.size()
            pixmap_size = pixmap.size()
            
            # 计算缩放后的图像位置
            scale = min(label_size.width() / pixmap_size.width(),
                      label_size.height() / pixmap_size.height())
            scaled_width = int(pixmap_size.width() * scale)
            scaled_height = int(pixmap_size.height() * scale)
            
            # 计算图像在Label中的偏移量
            x_offset = (label_size.width() - scaled_width) // 2
            y_offset = (label_size.height() - scaled_height) // 2
            
            # 将点击位置转换为图像坐标
            x = int((ev.position().x() - x_offset) / scale)
            y = int((ev.position().y() - y_offset) / scale)
            
            if 0 <= x < self.hsv_image.shape[1] and 0 <= y < self.hsv_image.shape[0]:
                # 获取HSV值
                hsv = self.hsv_image[y, x]
                
                # 更新对应的滑块
                if self.color_picker_mode == 'min':
                    self.sliders[0].setValue(int(hsv[0]))
                    self.sliders[1].setValue(int(hsv[1]))
                    self.sliders[2].setValue(int(hsv[2]))
                else:
                    self.sliders[3].setValue(int(hsv[0]))
                    self.sliders[4].setValue(int(hsv[1]))
                    self.sliders[5].setValue(int(hsv[2]))
                
                # 关闭取色器模式
                self.color_picker_mode = None
                self.picker_min_btn.setStyleSheet('')
                self.picker_max_btn.setStyleSheet('')
    
    def update_image(self):
        if self.image is None or self.hsv_image is None:
            return
            
        # 获取 HSV 范围
        h_min = self.sliders[0].value()
        s_min = self.sliders[1].value()
        v_min = self.sliders[2].value()
        h_max = self.sliders[3].value()
        s_max = self.sliders[4].value()
        v_max = self.sliders[5].value()
        
        # 创建掩码
        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])
        mask = cv2.inRange(self.hsv_image, lower, upper)
        
        # 根据模式选择是保留还是移除颜色
        if self.keep_color_btn.isChecked():
            result = cv2.bitwise_and(self.image, self.image, mask=mask)
        else:  # 移除颜色模式
            result = cv2.bitwise_and(self.image, self.image, mask=cv2.bitwise_not(mask))
        
        # 转换为 QImage 并显示
        height, width = result.shape[:2]
        bytes_per_line = 3 * width
        qt_image = QImage(
            result.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_BGR888
        )
        
        # 创建适应label大小的pixmap
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'image_label') and self.image is not None:
            self.update_image()

    def on_edit_change(self, text, slider):
        try:
            value = int(text)
            max_value = slider.maximum()
            if 0 <= value <= max_value:
                slider.setValue(value)
        except ValueError:
            pass

    def copy_hsv_range(self):
        h_min = self.sliders[0].value()
        s_min = self.sliders[1].value()
        v_min = self.sliders[2].value()
        h_max = self.sliders[3].value()
        s_max = self.sliders[4].value()
        v_max = self.sliders[5].value()
        
        hsv_range = f"(({h_min}, {s_min}, {v_min}), ({h_max}, {s_max}, {v_max}))"
        clip = QApplication.clipboard()
        if clip:
            clip.setText(hsv_range)
            QMessageBox.information(self, "提示", "HSV范围已复制到剪贴板")
        else:
            QMessageBox.warning(self, "提示", "无法访问剪贴板")

    def on_mode_change(self):
        # 设置按钮互斥
        sender = self.sender()
        if sender == self.remove_color_btn:
            self.keep_color_btn.setChecked(not self.remove_color_btn.isChecked())
        else:
            self.remove_color_btn.setChecked(not self.keep_color_btn.isChecked())
        
        # 更新图片
        self.update_image()

def main():
    app = QApplication(sys.argv)
    window = HSVRangeTool()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 