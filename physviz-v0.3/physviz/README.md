# PhysViz

PhysViz 是一个 pygame 物理公式实验台。右上角可以创建小球、桌子、隔板和双星/三星预设，
也可以从 token 区组合公式。公式识别后会变成金色 chip；把 chip 拖到小球上可叠加效果，
双击 chip 则在 chip 位置生成对应的物理对象。

## 运行

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## 控制

* 点击右上角“**小球**”“**桌子**”“**隔板**”“**双星**”“**三星**”按钮生成对象。
* 点击或拖动 token 到画布组合：`mg`、`F=ma`、`p=mv`、`E=½mv²`、`E=mc²`、`G=mv²/r`、
  `f=μN`、`E_p=mgh`、`v=v_0+at`、`F=GMm/r²`、`W=Fs`。
* 公式识别后会变成金色 chip；将 chip 拖到小球上应用效果，双击 chip 生成对应小球、恒星或黑洞。
* 左键拖动物体或 chip；右键删除 token/chip，右键拖动带 `F=ma` 的小球设置外力。
* 右侧“属性”面板会随选中对象显示质量、速度、桌面/隔板参数和“删除”按钮；
  “环境”面板可编辑重力、空气阻力、地面摩擦、反弹系数、模拟引力常数及全局重力。
* 顶部“模拟1、模拟2、+”标签可切换或关闭相互独立的模拟场景。
* `Space` 暂停，`R` 重置，`Delete` 删除选中对象。

## 字体

UI 会按 Windows、macOS、Linux 的常见路径自动寻找中文字体，也会递归查找文件名包含
`FZS10`、`方正S10`、`FZShuSong`、`方正书宋` 或 `FZSSJW` 的方正字体。
公式中的拉丁字母使用 Times/Liberation Serif 斜体，数字、单位和运算符使用直立中文字体。
如果中文仍然乱码，可在项目中创建 `assets/fonts/`，放入任意 CJK 字体并命名为
`cjk.ttf`、`cjk.ttc` 或 `cjk.otf`，程序会优先使用它。

## 已注册公式

`mg`（重力）、`F=ma`（外力）、`p=mv`（动量）、`E=½mv²`（动能）、
`E=mc²`（黑洞）、`G=mv²/r`（恒星）、`f=μN`（摩擦力）、
`E_p=mgh`（势能）、`v=v_0+at`（速度变化）、`F=GMm/r²`（引力）、
`W=Fs`（功）。
