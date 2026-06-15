# picsort - Photo/Video Organizer v1.0.1 Source Code

## 功能
- 按拍摄时间自动分类归档照片/视频
- 支持三级目录配置（年/月/日/无）
- 路径实时预览
- EXIF 读取（照片）+ MP4/MOV 元数据读取（视频）
- 文件修改时间回退
- 不覆盖、不改名、不删除有效文件
- 自动清理空文件夹

## 依赖
- Python 3.8+
- PyQt5
- Pillow
- pillow-heif（HEIC 支持）

## 打包命令
```
pip install PyQt5 Pillow pillow-heif pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "手机照片视频整理工具" --hidden-import pillow_heif photo_organizer_v5.py
```

## 支持的格式
- 照片：JPG、JPEG、PNG、HEIC、WEBP
- 动态图：GIF
- 视频：MP4、MOV、M4V、AVI、FLV、WMV、3GP
