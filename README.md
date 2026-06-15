# picsort - Photo/Video Organizer

📷 **picsort** 是一款轻量级的照片视频整理工具，可以按拍摄时间自动分类归档到年/月/日目录结构。

![picsort Demo](docs/screenshot.png)

## ✨ 功能特性

- **智能时间识别**：自动读取照片 EXIF 信息和视频元数据获取拍摄时间
- **自定义目录结构**：支持三级目录配置（年/月/日），灵活组合
- **实时路径预览**：配置目录结构时即时预览最终路径
- **安全保障**：不覆盖已存在文件，不删除有效文件
- **自动清理**：整理完成后自动删除空文件夹
- **多格式支持**：支持常见的照片和视频格式

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows/Linux/macOS

### 安装依赖

```bash
pip install PyQt5 Pillow pillow-heif
```

### 运行程序

```bash
python photo_organizer_v5.py
```

### 打包为可执行文件

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "picsort" --hidden-import pillow_heif photo_organizer_v5.py
```

## 📖 使用说明

### 基本操作流程

1. **选择源文件夹**：点击「源文件夹」的「选择」按钮，选择存放照片/视频的目录
2. **选择目标文件夹**：点击「目标文件夹」的「选择」按钮，选择整理后文件的存放目录
3. **配置目录结构**：
   - 一级目录：通常选择「年」
   - 二级目录：通常选择「月」
   - 三级目录：可选择「日」或「无」
4. **开始整理**：点击「开始整理」按钮，确认后程序将自动整理文件

### 目录结构示例

**配置：年 / 月 / 无**

```
目标文件夹/
├── 2023/
│   ├── 01/
│   │   ├── IMG_0001.jpg
│   │   ├── IMG_0002.jpg
│   │   └── video_001.mp4
│   └── 12/
│       └── IMG_9999.jpg
└── 2024/
    └── 06/
        └── vacation_photo.jpg
```

**配置：年 / 月 / 日**

```
目标文件夹/
└── 2024/
    └── 06/
        ├── 15/
        │   └── dinner.jpg
        └── 20/
            ├── beach_01.jpg
            └── beach_02.jpg
```

## 📷 支持格式

| 类型 | 支持格式 |
|------|----------|
| 照片 | JPG, JPEG, PNG, HEIC, WEBP |
| 动态图 | GIF |
| 视频 | MP4, MOV, M4V, AVI, FLV, WMV, 3GP |

## 🔧 工作原理

1. **收集文件**：递归扫描源文件夹，收集所有支持的媒体文件
2. **提取时间**：
   - 照片：读取 EXIF 元数据获取拍摄时间
   - 视频：解析 MP4/MOV 文件结构获取创建时间
   - 回退方案：使用文件修改时间
3. **创建目录**：根据配置的目录结构创建目标文件夹
4. **移动文件**：将文件移动到对应目录，跳过已存在的文件
5. **清理空文件夹**：删除源文件夹中遗留的空文件夹

## 📁 项目结构

```
picsort/
├── photo_organizer_v5.py   # 主程序源代码
├── README.md               # 项目说明文档
└── docs/
    └── screenshot.png      # 界面截图
```

## 📸 截图

### 主界面

![Main Interface](docs/screenshot.png)

### 整理完成

![Completion](docs/completion.png)

## 📝 更新日志

### v1.0.1
- 项目重命名为 picsort
- 优化界面标题和描述
- 更新版本号

### v1.0.0
- 初始版本发布
- 支持照片和视频整理
- 支持三级目录配置
- 支持 EXIF 和视频元数据读取

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

*Made with ❤️ for photo organization*
