"""路由用例共用：跑之前记下三份图文件的 sha256，跑完断言一个字节都没变。

路由只读（ADR-0005；#33 验收「跑完后 图.json 与两份视图的字节不变」）。比对字节而不是比对内容：
`图视图.json` 里有 `生成时间`，模型若只是多跑了一次 `graph.py views`，内容看着一样、字节会变，
那也是一次写入，该红。

基线落成工作区根的点开头文件 `.基线.json`：跑器只把种子目录里的东西拷进工作区，这一份由回放写，
用例的「没往工作区乱写」断言按惯例忽略点开头的项。
"""
import hashlib
import json
import pathlib

文件 = ("图.json", "图视图.md", "图视图.json")
基线名 = ".基线.json"


def 摘要(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def 写基线(workspace) -> None:
    ws = pathlib.Path(workspace)
    缺 = [名 for 名 in 文件 if not (ws / 名).is_file()]
    if 缺:
        raise SystemExit("写基线时工作区里缺：%s" % "、".join(缺))
    (ws / 基线名).write_text(
        json.dumps({名: 摘要(ws / 名) for 名 in 文件}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


def 校验基线(workspace) -> None:
    ws = pathlib.Path(workspace)
    基线 = ws / 基线名
    assert 基线.is_file(), "种子没写下 %s，这条断言无从比对" % 基线名
    期望 = json.loads(基线.read_text(encoding="utf-8"))
    变了 = []
    for 名, 摘 in 期望.items():
        p = ws / 名
        if not p.is_file():
            变了.append("%s 没了" % 名)
        elif 摘要(p) != 摘:
            变了.append("%s 的字节变了" % 名)
    assert not 变了, "路由只读，跑完这三份文件该一个字节都不变：%s" % "、".join(变了)
