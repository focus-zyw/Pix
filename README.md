# Pix

游戏内叠加层：读本机 Live Client 的英雄和攻速，按你设的攻击键 / 移动键提示前摇、后摇。

只读本机 `https://127.0.0.1:2999`。必须 Windows，和英雄联盟开在同一台电脑。别人拿到程序，看到的是**他自己正在打的那局**。

## 使用说明

打包好的 exe 在 [Releases](https://github.com/focus-zyw/Pix/releases)。打开 `Pix.exe` 即可，没有账号、没有授权。杀毒软件有时会拦 PyInstaller 打包的 exe，放行即可。大厅连不上 Live Client，进对局后才有数据。

### 未进对局

屏幕上会出现 Pix 图标（默认在左上附近）。空白处点得穿，不影响点游戏。


| 操作             | 作用                     |
| -------------- | ---------------------- |
| **按住左键拖动**图标   | 挪位置，下次启动还在这儿           |
| **左键点**图标      | 打开 / 关掉设置              |
| 鼠标**悬停**图标     | 旁侧显示攻速、前摇、后摇（没进对局时是 —） |
| 关掉设置后，**右键**图标 | 退出程序                   |


设置里有「攻击键」「移动键」（默认左键攻击、右键移动，需和游戏里一致）：

1. 点「攻击键」或「移动键」，该项变成「按下…」。
2. 按你要监听的键或鼠标键（左键 / 右键 / 中键 / 侧键，或键盘上的键）。
3. 再点一次图标关掉设置。设置开着时右键不会退出，避免误关。

进对局后设置会自动关掉；对局里点图标打不开设置，出对局后再改。

### 对局里

进峡谷或训练模式后，自动读你的英雄和当前攻速。按你设的**攻击键**后，图标按这一刀的阶段变色：


| 颜色  | 含义  |
| --- | --- |
| 绿   | 可攻击 |
| 黄   | 前摇中 |
| 红   | 后摇中 |


前摇中按**移动键**会取消这一刀（和走砍取消前摇一样）。悬停仍可看当前攻速和前摇 / 后摇时长。

键位和窗口位置写在 `%LOCALAPPDATA%\Pix\prefs.json`（打包后）或本目录 `data/prefs.json`（跑源码时）。

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

打包 exe（产物 `dist\Pix.exe`，不要提交进 git，可挂到 Releases）：

```bat
.\.venv\Scripts\pip install pyinstaller
.\.venv\Scripts\python build_pix.py
```



## 目录


| p路径                          | 说明                     |
| ---------------------------- | ---------------------- |
| `app.py`                     | 轮询 Live Client、按键监听、设置 |
| `overlay.py`                 | 游戏内精灵窗                 |
| `input_win.py`               | Windows 只读按键           |
| `live_client.py`             | 本机 2999                |
| `data/stat_growth.json`      | 前摇比例                   |
| `data/champion_aliases.json` | 中文名 / 俗称 → 英文          |
| `assets/`                    | 精灵图                    |
| `build_pix.py`               | 打成 `Pix.exe`           |
| `pack/`                      | PyInstaller spec、图标脚本  |




## License

MIT — 见 [LICENSE](LICENSE)。