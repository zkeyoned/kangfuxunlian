// 运行时配置。仓库里这份是空的占位文件，不写任何真实域名或地址。
//
// 谁会覆盖它：
//   桌面安装包运行时由 desktop/launcher.py 生成一份同名文件，内容形如
//   window.REHAB_CONFIG = {"apiBase": "https://<你的域名>/api/v1"};
//   真实地址来自环境变量 REHAB_CLOUD_BASE 或安装目录旁的 config.json，不入库。
//
// 不设置时的行为：app.js 里 API_BASE 保持原值 http://127.0.0.1:8801/api/v1，
// 线上部署脚本仍按原来的方式把它替换成同源路径，三种视觉模式的行为都不变。
