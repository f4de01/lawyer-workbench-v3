"""冒烟用例的断言：文件内容与回复形状。签名 (workspace: Path, reply: str)。"""


def check_文件存在(workspace, reply):
    assert (workspace / "冒烟.txt").is_file(), "工作区里没有 冒烟.txt"


def check_文件内容(workspace, reply):
    text = (workspace / "冒烟.txt").read_text(encoding="utf-8").strip()
    assert text == "冒烟通过", "冒烟.txt 内容应为「冒烟通过」，实际为 %r" % text


def check_没写别的文件(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir())
    assert names == ["冒烟.txt"], "工作区里多出了文件：%s" % names
