# 家族旅遊短劇：早知道就出門了

四人演出、約 7 分半的單一場景舞台劇，含角色動機、走位、服裝與道具。網頁版請開 index.html，或啟用 GitHub Pages 後直接用瀏覽器看。

## 改劇本

劇本的正本是 `劇本.md`，直接改這個檔，不要改 index.html 裡的劇本段落。格式：

- `## 第一段　補宣誓 0:00–1:00`：段落標題，最後是時間。
- `阿嬤：（揮手）不用扶。`：一句台詞一行，角色名加全形冒號。全形括號裡是動作，台詞本不會畫底線。
- `（燈暗。）`：整行用全形括號包起來，是舞台指示。
- `> 走位：…`、`> 演法：…`：走位與演法提示。
- `> 情緒：` 下一行起寫 `> - 阿嬤：…`，一個角色一行：這段的情緒建議。台詞本上，自己那一行會加粗。

改完後依序執行：

```sh
python3 tools/script_md.py build
python3 tools/make_sides.py
```

第一行把 `劇本.md` 寫回 index.html 的劇本段落，並更新下載區的台詞句數。第二行重新產生 `sides/` 裡四個角色的台詞本 PDF，需要 Google Chrome。

## 台詞本

每個角色的台詞本 PDF 在 sides/ 資料夾，自己的台詞加粗並畫底線，可直接列印：阿嬤 amah.pdf、阿明 aming.pdf、淑芬 shufen.pdf、小瑜 xiaoyu.pdf。

## 走位圖

`blocking/` 裡是每一段的走位圖：`scene-1.png` 到 `scene-6.png` 各一段，`overview.png` 是全劇軌跡與空白總覽，`blocking.pdf` 把七張合成 A4 橫式可列印。斜線區是那一段沒有人走到的地板。

走位座標寫在 `tools/make_blocking.py` 的 `SCENES`，不會跟著 `劇本.md` 自動更新。改了走位就同步改那裡，再執行：

```sh
python3 tools/make_blocking.py
```
