"""故意失败：第一条断言应过，第二条必红，报红时应给出函数名 check_内容故意写反。"""


def check_文件存在(workspace, reply):
    assert (workspace / "冒烟.txt").is_file(), "工作区里没有 冒烟.txt"


def check_内容故意写反(workspace, reply):
    text = (workspace / "冒烟.txt").read_text(encoding="utf-8").strip()
    assert text == "冒烟失败", "这条断言故意写反：期望「冒烟失败」，实际为 %r" % text
