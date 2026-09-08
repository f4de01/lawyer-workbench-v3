"""种子「带内」：在种子「在办中」的工作区之上，把一件官方模板的第一行行高钉死。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
手术本身（起手并钉 / 钉住第一行行高）住在这里、带一个 twips 参数，孪生种子「越界」（#74）只传另一个数。
放在种子里而不是 evals/共用/：tests/python-floor 扫的是 evals/种子/*/回放.py，共用/ 下的模块不在它的
视野里，手术挪过去就没人守 3.9 底线了（#61）。跨种子借代照「兜底」借「在办中」的先例。
先跑「在办中」的回放（真的起手 CLI 加图引擎、陈述落档），再对 模板/官方/ 里挂在待办节点
「管理人银行账户备案报告」上的那件官方模板做一次 XML 手术：第一张表第一行加
`<w:trHeight w:hRule="exact" w:val="4000"/>`（= 200 磅）。

为什么这么钉：`hRule="exact"` 的行高与格里写什么无关，推算层直接取这个数（gate.py 的
`_table_bands_pt`），所以只要成品里有那张表，最大行高的推算区间就恒为 `[196.0, 206.0]` 磅
（`ROW_HEIGHT_TOLERANCE` 的 ×0.98 与 ×1.02 + 2），正好把默认阈值 200 磅夹在中间：一次由模型
自由写正文的生成于是落在带内，门禁给需人眼。**前提是模型照模板写出了那张表**：钉子钉在模板的
表格行上，稿子里没有表，转换器就不会把表落进成品，钉子也就不生效（用例里由断言「成品里有模板
那张表」把这种落空钉成一条看得懂的红）。只钉第一行、不钉整表：整表钉满会把文书顶到
两三页，页数与空白页两项跟着变量多；只钉一行，最大行高这一项独自制造需人眼，别的项都不动。

不往仓库塞二进制：合成模板由本脚本从工作区里那件官方模板原件（起手按图上挂到的模板拷进去的，
与领域资产同一份字节）现做，原地换掉。
「在办中」的 材料/ 由那个种子的目录带着，这里照种子接口自己拷一遍。
工作区里没有任何案件内容：当事人与法院一律写甲乙丙。
"""
import importlib.util
import pathlib
import re
import shutil
import sys
import zipfile

SEED_DIR = pathlib.Path(__file__).resolve().parent
在办中 = SEED_DIR.parent / "在办中"
模板名 = "1-3.关于管理人银行账户备案的报告.docx"
带内twips = 4000  # = 200 磅，正好是默认阈值，推算区间把它夹在中间
行高钉 = '<w:trPr><w:trHeight w:hRule="exact" w:val="%d"/></w:trPr>'


def 钉住第一行行高(path: pathlib.Path, twips: int) -> int:
    """把 path 那件 docx 的第一张表第一行行高钉成固定 twips（1 磅 = 20 twips），原地换掉，返回钉了几行。

    孪生种子「越界」只换 twips 这一个数（ADR-0017 的三档里另一档，#74），所以这一段与下面的
    起手并钉 都写成带参数的，两个种子共用同一份手术。
    """
    zin = zipfile.ZipFile(path)
    try:
        items = [(item, zin.read(item.filename)) for item in zin.infolist()]
    finally:
        zin.close()
    done = 0
    tmp = path.with_name(path.name + ".钉行高")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for item, data in items:
            if item.filename == "word/document.xml":
                xml = data.decode("utf-8")
                xml, done = re.subn(r"(<w:tr(?: [^>]*)?>)", r"\1" + (行高钉 % twips), xml, count=1)
                data = xml.encode("utf-8")
            zo.writestr(item, data)
    tmp.replace(path)
    return done


def 起手并钉(workspace: str, twips: int) -> int:
    """跑「在办中」的回放，再把待办节点那件官方模板的第一行行高钉成 twips 高。回退出码。"""
    sys.dont_write_bytecode = True  # 别在仓库的种子目录里留 __pycache__
    ws = pathlib.Path(workspace)

    # 跑器按种子接口把 <种子>/ 下的条目原样拷进工作区；用这个手术的两个种子都借「在办中」的材料，自己拷一遍。
    shutil.copytree(在办中 / "材料", ws / "材料", dirs_exist_ok=True)

    spec = importlib.util.spec_from_file_location("seed_working_replay", 在办中 / "回放.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = module.main(workspace)
    if code != 0:
        return code

    模板 = ws / "模板" / "官方" / 模板名
    if not 模板.is_file():
        sys.stderr.write("起手没把 %s 拷进 模板/官方/\n" % 模板名)
        return 1
    if 钉住第一行行高(模板, twips) != 1:
        sys.stderr.write("%s 里找不到表格行，钉不上行高\n" % 模板名)
        return 1
    return 0


def main(workspace: str) -> int:
    return 起手并钉(workspace, 带内twips)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
