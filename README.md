# 

一个单文件 Flask 绘图应用：前端用于对称笔画创作，后端根据诗句意象生成图案。东晋才女苏蕙以841字织就璇玑图，纵横回环，可读出数千首诗。她将线性文字编织为二维网络，让意象在空间中生长出无穷路径。“璇玑诗绘”以此为灵感，将诗文意象转化为纹样基因，以交互对称结构为骨架，在数字空间中延续织锦与回文的古老智慧。每一次手绘，都是对璇玑图的一次当代阅读。




## 本地运行

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动应用

```bash
python app.py
```

3. 打开浏览器访问

```text
http://127.0.0.1:5000
```

应用会监听 `0.0.0.0`，端口优先读取环境变量 `PORT`，默认 `5000`。

## 部署到 Hugging Face Spaces

1. 在 Hugging Face 创建一个新的 Space。
2. SDK 选择 `Docker` 以外的 Python 环境（例如 Gradio/Streamlit 的普通 Python Space 运行方式也可），Python 版本使用 `3.10`。
3. 将以下文件上传到 Space 仓库根目录：
	- `app.py`
	- `requirements.txt`
4. 在 Space 的启动命令中设置：

```bash
python app.py
```

5. 提交后等待构建完成，Space 会自动安装 `requirements.txt` 中的依赖并启动服务。

## 本地保存生成图（小程序）

新增脚本：`save_generated_local.py`

作用：调用本地运行中的 `/generate` 接口并把返回 PNG 保存到本地。

示例：

```bash
python save_generated_local.py --poem "云想衣裳花想容" --axes 6
```

自定义输出文件名：

```bash
python save_generated_local.py --poem "明月松间照" --output output/my_result.png
```

使用已有笔画 JSON（格式同前端发送的 `strokes` 字段）：

```bash
python save_generated_local.py --strokes-file strokes.json --poem "山色空蒙雨亦奇"
```

## 依赖版本

- Flask==3.0.0
- Pillow==10.1.0
