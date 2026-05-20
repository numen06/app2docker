# MiSans 自托管字体

本目录用于放置 [MiSans](https://hyperos.mi.com/font/zh/) 可变字体（WOFF2），供前端全局 UI 使用。

## 获取字体

1. 打开官方下载页：<https://hyperos.mi.com/font/download>
2. 下载 **MiSans**（简体中文，含可变字体）
3. 在压缩包中找到 **WOFF2 可变字体（VF）** 文件
4. 复制并重命名为：

   ```
   MiSans-VF.woff2
   ```

5. 将文件放到本目录：`frontend/public/fonts/misans/MiSans-VF.woff2`

## 许可说明

MiSans 可免费商用。若将本软件对外分发，请在说明中注明使用了 MiSans 字体。详见官方[许可协议](https://hyperos.mi.com/font/download)。

## 注意

- 字体文件体积较大，默认不提交到 Git；构建/运行前请确保本地已放置 `MiSans-VF.woff2`
- 若文件缺失，界面将回退到系统字体（`system-ui` / 微软雅黑等），功能不受影响
