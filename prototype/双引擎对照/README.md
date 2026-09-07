# 【一次性原型】Word vs WPS 两个真渲染器，三列对照

回答 issue #60（地图 #54）：**同一件样例分别用 Word 与 WPS 出 PDF，`pdf_checks` 那三项差多少？两套排版引擎会不会在阈值上给出相反的结论？**

**不要合进 main。** `gate.py` 一个字没改；结论进 ADR。

## 跑

```
python prototype/双引擎对照/对照.py --json 对照结果.json
```

要 Word COM 与 WPS COM 都在。串行起两个引擎（本机两个 Office 进程同时起会互相关掉），25 件约十分钟。

## 两个引擎怎么起

| | ProgID | 宿主 | 备注 |
| --- | --- | --- | --- |
| Word | `Word.Application` | 64 位 `powershell.exe` | 与 `gate.py` 现行通道一致 |
| WPS | `KWPS.Application` | **32 位** `C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe` | `KWPS` 只注册在 `WOW6432Node`，64 位进程解不出来 |

脚本体（`Documents.Open` / `ComputeStatistics(2)` / `ExportAsFixedFormat(路径, 17)` / `Close(0)` / `Quit()`）**逐字相同**，只换 ProgID 与宿主。

## 引擎身份怎么分辨

`Application.Name` 两边都回 `Microsoft Word`（坐实 #56 的怀疑，**不能**用它分辨）。能分辨的是：

- `Application.Path`：`C:\Program Files\Microsoft Office\Root\Office16` vs `D:\wps\WPS Office\12.1.0.23542\office6`
- `Application.Version`：`16.0` vs `12.0`
- `Application.Build`：`16.0.20326` vs `12.1.0.23542`

## 结论

详见 #60 的 resolution 评论与本目录的 `对照报告.txt` / `对照结果.json`。
