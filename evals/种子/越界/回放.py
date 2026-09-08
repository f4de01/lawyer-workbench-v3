"""种子「越界」：种子「带内」的反向孪生，同一个手术只换一个数，行高钉在阈值之外。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
借「带内」的 起手并钉：先跑「在办中」的回放（真的起手 CLI 加图引擎、陈述落档），再对
模板/官方/ 里挂在待办节点「管理人银行账户备案报告」上的那件官方模板做一次 XML 手术，
第一张表第一行加 `<w:trHeight w:hRule="exact" w:val="5000"/>`（= 250 磅）。

「带内」钉的是 4000（200 磅，正好是默认阈值，推算区间把阈值夹在中间，结论是需人眼）；
这里钉 5000，推算区间恒为 `[245.0, 257.0]` 磅，**整个区间都在默认阈值 200 磅之外**，
所以是干净的不通过，不掺需人眼。带渲染跑同样不通过（实测点值 250.1 磅），两条跑道同一个结论。

这一档要的是**改不好的**失败：行高来自模板、与正文内容无关，模型无论怎么改稿都改不动它，
于是「按不通过项改稿重转至多 2 次、仍不过就生成失败」那条路必然走到底。转换器照常出件
（退出码 0），所以一定走得到门禁：这正是它躲开原先想到的两条别扭造法的地方（#74）。

不往仓库塞二进制：合成模板由「带内」的手术从工作区里那件官方模板原件现做，原地换掉。
工作区里没有任何案件内容：当事人与法院一律写甲乙丙。
"""
import importlib.util
import pathlib
import sys

SEED_DIR = pathlib.Path(__file__).resolve().parent
带内 = SEED_DIR.parent / "带内"
越界twips = 5000  # = 250 磅，整个推算区间都高过默认阈值 200 磅


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True  # 别在仓库的种子目录里留 __pycache__
    spec = importlib.util.spec_from_file_location("seed_in_band_replay", 带内 / "回放.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.起手并钉(workspace, 越界twips)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
