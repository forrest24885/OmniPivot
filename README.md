
# 璇玑—万象

🎨 文化溯源

东晋才女苏蕙以841字织就璇玑图，纵横回环，可读出数千首诗。她将线性文字编织为二维网络，让意象在空间中生长出无穷路径。“璇玑诗绘”以此为灵感，将诗文意象转化为纹样基因，以交互对称结构为骨架，在数字空间中延续织锦与回文的古老智慧。每一次手绘，都是对璇玑图的一次当代阅读

 
用对称的笔触和一句诗词，生成独一无二的传统纹样。融合交互绘画、诗词意象与生成式艺术，数字时代的璇玑图。


功能/📖 使用指南

1.在画布上用鼠标/手指画出对称线条。

2.调节“对称轴数”滑块改变图案结构。

3.输入一句诗（如“云想衣裳花想容”）。

4.点击“生成图案”获得半动态纹样。
<img width="1869" height="1188" alt="f417bb749f05fbb220d2bb70fa6c5a23" src="https://github.com/user-attachments/assets/514c0c35-83a3-42eb-be76-3d9ac66531b4" />

5.可点击图片以保存本地



目录结构概览

symmetry-verse/
├── app.py                # Flask 主程序
├── templates/
│   └── index.html        # 主页面（绘画交互 + 诗句输入）
├── static/
│   ├── textures/         # 背景纹理、印章等静态图片
│   └── demo_static.png   # 预览图（可选）
├── requirements.txt
└── README.md

入口与核心逻辑: app.py
前端页面模板: index.html
部署进程配置: Procfile
Render 部署配置: render.yaml
Python 依赖: requirements.txt
项目说明: README.md
本地调用生成接口并保存图片的脚本: save_generated_local.py



技术栈

后端：Python, Flask, Pillow

前端：原生 HTML5 Canvas, JavaScript, CSS3

动画：前端 MediaRecorder / 后端 imageio+FFmpeg

后续改进方向🗺️ 未来计划

更多意象支持（人物、建筑、神话动物）

接入api加强对诗句的感知，尝试理解诗句中的比喻手法


接入 ControlNet 进行风格化增强（如工笔、景泰蓝）

生成剪纸风格轮廓，支持激光切割或 3D 打印

多人协作共绘一幅璇玑图

动画优化：前端 WebCodecs 实时编码：接入api加强对诗句的感知，尝试理解诗句中的比喻手法。

## 依赖版本

- Flask==3.0.0
- Pillow==10.1.0
