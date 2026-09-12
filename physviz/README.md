# PhysViz

PhysViz 是一个用 pygame 编写的桌面物理实验台。拖动底部字母/符号到画布上，
把它们首尾相接即可组合公式，公式会在短暂发光后变成可交互的物理对象。

## 运行

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## 控制

* 鼠标左键拖动 token、公式链或物理球；右键删除 token，右键清除力。
* 将 token 放到另一个 token/链的左右 50 像素内以连接。
* `Space` 暂停，`R` 重置，`Delete` 删除选中对象。
* `F=ma` 物体可右键拖出恒力；`G=mv²/r` 中心会捕获附近物体。

## 已注册公式

`mg`、`E=mc²`、`G=mv²/r`、`F=ma`、`p=mv`、`E=½mv²`。
