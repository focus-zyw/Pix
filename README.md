# Pix

游戏内叠加层：读本机 Live Client 的英雄和攻速，按你设的攻击键 / 移动键提示前摇、后摇。

只读本机 `https://127.0.0.1:2999`。必须 Windows，和英雄联盟开在同一台电脑。别人拿到程序，看到的是**他自己正在打的那局**。

## 给玩家：用打包好的 exe

1. 打开 `Pix.exe`。
2. 未进对局时，**左键点图标**打开设置，点「攻击键」或「移动键」后再按要监听的键。
3. **按住左键拖动**移动图标；关掉设置后，**右键图标**退出。
4. 进对局后自动读攻速，按你设的键提示前摇 / 后摇。

没有账号、没有授权。杀毒软件有时会拦 PyInstaller 打包的 exe，放行即可。

## 给开发者：从 GitHub 跑源码

需要 [Python](https://www.python.org/downloads/) 3.12+（安装时勾选 Add to PATH）。仓库目录名必须是 `pix`（内部按包名 `pix` 导入）。

```bat
git clone https://github.com/focus-zyw/Pix.git pix
cd pix
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python run_pix.py
```

也可以：`.\.venv\Scripts\python __main__.py`

不会 git 的话：仓库页 **Code → Download ZIP**，解压后把文件夹改名为 `pix`，同样建 `.venv` 再运行。

## 目录

| 路径 | 说明 |
|------|------|
| `app.py` | 轮询 Live Client、按键监听、设置 |
| `overlay.py` | 游戏内精灵窗 |
| `input_win.py` | Windows 只读按键 |
| `live_client.py` | 本机 2999 |
| `data/stat_growth.json` | 前摇比例 |
| `assets/` | 精灵图 |

键位写在 `%LOCALAPPDATA%\Pix\prefs.json`（打包后）或本目录 `data/prefs.json`（跑源码时）。

## License

MIT — 见 [LICENSE](LICENSE)。
