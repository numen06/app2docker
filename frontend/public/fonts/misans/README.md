# MiSans 自托管字体

本目录字体由 `npm install` 时自动从 [misans-vf](https://www.npmjs.com/package/misans-vf)（小米 MiSans 可变字体子集，免费商用）复制生成。

## 自动安装

```bash
cd frontend
npm install
```

`postinstall` 会执行 `scripts/copy-misans-fonts.mjs`，将 `MiSans.min.css` 与 `MiSans.*.woff2` 复制到本目录。

也可手动执行：

```bash
npm run setup:fonts
```

## 许可说明

MiSans 可免费商用。若将本软件对外分发，请在说明中注明使用了 MiSans 字体。详见官方[许可协议](https://hyperos.mi.com/font/download)。

## 注意

- `*.woff2` 与 `MiSans.min.css` 由脚本生成，通常不提交到 Git
- 若文件缺失，运行 `npm run setup:fonts` 后重启 dev server
