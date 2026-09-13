#!/usr/bin/env python3
"""原型 —— 不是产品代码，不进 0.3.0 的发布路径（#130，wayfinder prototype 规矩）。

答的只有一问：真实的 图视图.json 到「看得见一张图」，第一档（回复里的 Mermaid + 表格）
与第二档（随包零依赖 tkinter 窗口）两条链跑不跑得通，接口缺哪几样。
不答界面长什么样（#130 明说不答；界面设计另行单独进行）。

位置照 #129 定的：CLI 住 loo0ng-note/scripts/，不住 loo0ng-graph 旁边。
硬约束照 #129：只读 图视图.json 里已经算好的字段，不复制任何推算规则，不写图。

    第一档：cd <工作区> && python note.py mermaid [--shape full|overview]
    第二档：python note.py window [--root <案件根>]

第一档照 #128 的闸门：不接受任何指定工作区的参数，只认 cwd。
第二档照 #128：接一个案件根、现扫 */图视图.json、根记在 ~/.loo0ng/ 一行。
原型把那一行记在 ~/.loo0ng/原型-案件根（PROTOTYPE，可随手删），不碰真配置。
"""
import argparse
import json
import os
import pathlib
import sys

VIEW = "图视图.json"
SOURCE = "图.json"
HOME_LINE = pathlib.Path.home() / ".loo0ng" / "原型-案件根"  # PROTOTYPE, wipe me

# 状态 -> (ascii class 名, 填色, 一个字的记号)。classDef 名不敢用中文，Mermaid 那边没验过。
STATUS = {
    "未生成": ("s0", "#f4f4f5", "·"),
    "已生成": ("s1", "#fde68a", "○"),
    "已确认": ("s2", "#86efac", "●"),
    "不适用": ("s3", "#e4e4e7", "×"),
    "尚未进图": ("s4", "#ffffff", "…"),
}
MODULE_STATUS = {"进行中": "s1", "已完成": "s2", "不适用": "s3", "尚未进图": "s4", "已进图": "s0"}


# ---------- 读 ----------

def load_view(path):
    """只读，不重算。版本不认识就明说，不猜。"""
    with open(path, encoding="utf-8") as f:
        v = json.load(f)
    if v.get("格式版本") != 1:
        sys.exit("不认识的格式版本 %r：%s" % (v.get("格式版本"), path))
    return v


def staleness(ws):
    """#128：只报不修。源图比视图新 = 视图旧了。"""
    src, view = ws / SOURCE, ws / VIEW
    if not src.exists() or not view.exists():
        return None
    return "视图比源图旧（图.json 更新于其后），重算一次再看" if src.stat().st_mtime > view.stat().st_mtime else None


def latest_doc(node):
    vs = node.get("文书版本") or []
    return vs[-1] if vs else None


# ---------- 第一档：Mermaid + 表格 ----------

def mm_id(raw):
    return "".join(c if (c.isalnum() and ord(c) < 128) else "_" for c in raw)


def mm_text(s):
    return str(s).replace('"', "#quot;").replace("\n", " ")


def mermaid_full(view):
    """整图：一模块一 subgraph，一节点一格。

    版式是量出来的，不是挑的（#130）。同样 72 节点，三种写法的自然尺寸：
      flowchart LR + subgraph direction TB           19854 x 193   （103:1 的带子，废）
      flowchart TB + 不连模块 + 内部 TB               346 x 10334   （0.03:1 的柱子，废）
      flowchart TB + 模块间 ~~~ 连 + 内部 LR          3182 x 2294   （1.4:1，能看）
    没有边的节点 Mermaid 一律排成一行，`direction` 管不住它，得靠 `~~~` 隐形边掰。
    """
    out = ["flowchart TB"]
    mids = []
    for m in view["模块"]:
        mi = mm_id(m["id"])
        mids.append(mi)
        out.append('  subgraph %s["%s"]' % (mi, mm_text(m["标题"])))
        out.append("    direction LR")
        if not m["节点"]:
            out.append('    %s_empty["（空模块）"]:::s0' % mi)
        ids = []
        for n in m["节点"]:
            nid = mm_id(n["id"])
            ids.append(nid)
            out.append('    %s["%s"]:::%s' % (nid, mm_text(n["标题"]), STATUS.get(n["状态"], ("s0",))[0]))
        for a, b in zip(ids, ids[1:]):
            out.append("    %s ~~~ %s" % (a, b))     # 隐形边，只为把节点掰成一行一行
        out.append("  end")
    for a, b in zip(mids, mids[1:]):
        out.append("  %s ~~~ %s" % (a, b))           # 隐形边，只为把模块摞起来
    out += classdefs()
    return "\n".join(out)


def mermaid_overview(view):
    """概览：一模块一格，节点只报计数。表格补细节。"""
    out = ["flowchart LR"]
    prev = None
    for m in view["模块"]:
        tally = {}
        for n in m["节点"]:
            tally[n["状态"]] = tally.get(n["状态"], 0) + 1
        detail = " ".join("%s%d" % (STATUS.get(k, ("", "", "?"))[2], v) for k, v in sorted(tally.items()))
        label = "%s<br/>%s %d 节点%s" % (mm_text(m["标题"]), m["状态"], len(m["节点"]),
                                       ("<br/>" + detail) if detail else "")
        nid = mm_id(m["id"])
        out.append('  %s["%s"]:::%s' % (nid, label, MODULE_STATUS.get(m["状态"], "s0")))
        if prev:
            out.append("  %s --> %s" % (prev, nid))
        prev = nid
    ahead = [m for m in view["前方"] if m["状态"] == "尚未进图"]
    if ahead:
        out.append('  ahead["前方：%d 个模块尚未进图<br/>%s"]:::s4'
                   % (len(ahead), mm_text("、".join(m["标题"] for m in ahead[:4])
                                          + ("…" if len(ahead) > 4 else ""))))
        if prev:
            out.append("  %s -.-> ahead" % prev)
    out += classdefs()
    return "\n".join(out)


def classdefs():
    return ["  classDef %s fill:%s,stroke:#71717a,color:#18181b" % (c, fill)
            for c, fill, _ in STATUS.values()]


def table(view):
    rows = ["| 模块 | 节点 | 状态 | 来源 | 空白模板 | 时限 | 最新文书 |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for m in view["模块"]:
        for i, n in enumerate(m["节点"]):
            tpl = n["空白模板"]
            tpl = "无" if tpl == "无" else "%s %s" % (tpl["来源"], tpl["文件"])
            d = latest_doc(n)
            rows.append("| %s | %s | %s%s | %s | %s | %s | %s |" % (
                m["标题"] if i == 0 else "",
                n["标题"], STATUS.get(n["状态"], ("", "", "?"))[2], n["状态"], n["来源"], tpl,
                (n.get("时限") or "—").replace("|", "／"),
                ("v%d %s" % (d["版本"], d["文书"])) if d else "—"))
    return "\n".join(rows)


def ahead_table(view):
    if not view["前方"]:
        return "前方：无（领域图里的模块与节点都已进图）"
    rows = ["| 前方模块 | 状态 | 尚未进图的节点 |", "| --- | --- | --- |"]
    for m in view["前方"]:
        rows.append("| %s | %s | %s |" % (m["标题"], m["状态"], "、".join(n["标题"] for n in m["节点"])))
    return "\n".join(rows)


def cmd_mermaid(args):
    ws = pathlib.Path.cwd()          # #128 的闸门：只认 cwd，没有 --workspace
    path = ws / VIEW
    if not path.exists():
        sys.exit("当前目录下没有 %s（在案件工作区根目录里跑）：%s" % (VIEW, ws))
    view = load_view(path)
    warn = staleness(ws)
    body = mermaid_full(view) if args.shape == "full" else mermaid_overview(view)
    print("# %s · %s" % (ws.name, view["领域"] or "（无领域）"))     # #128：案件名 = 工作区目录名
    if warn:
        print("\n> ⚠ %s" % warn)
    print("\n```mermaid\n%s\n```\n" % body)
    print(table(view))
    print("\n" + ahead_table(view))


# ---------- 第二档：tkinter 窗口 ----------

def read_root(explicit):
    if explicit:
        return pathlib.Path(explicit)
    if HOME_LINE.exists():
        return pathlib.Path(HOME_LINE.read_text(encoding="utf-8").strip())
    return None


def write_root(root):
    HOME_LINE.parent.mkdir(parents=True, exist_ok=True)
    HOME_LINE.write_text(str(root), encoding="utf-8")


def scan_cases(root):
    """现扫，不登记：文件系统就是登记（#128）。"""
    if not root or not root.is_dir():
        return None
    return sorted([p for p in root.iterdir() if (p / VIEW).is_file()], key=lambda p: p.name)


def cmd_window(args):
    import tkinter as tk
    from tkinter import ttk

    root_dir = read_root(args.root)
    if args.root:
        write_root(pathlib.Path(args.root))
    cases = scan_cases(root_dir)
    if cases is None:
        sys.exit("案件根不存在或没记下：%s（跑一次 --root <案件根>）" % root_dir)
    if not cases:
        sys.exit("案件根底下一个 %s 都没扫到，不猜：%s" % (VIEW, root_dir))

    # #127(a)：窗口 cwd 不落 skill 目录、不落工作区，免得 Windows 锁住目录让整目录替换式升级失败。
    os.chdir(pathlib.Path.home())

    win = tk.Tk()
    win.title("案件便签（原型）")
    win.geometry("1180x720")
    bar = ttk.Frame(win, padding=6)
    bar.pack(fill="x")
    ttk.Label(bar, text="案件根 %s ·" % root_dir).pack(side="left")
    picker = ttk.Combobox(bar, state="readonly", width=28, values=[p.name for p in cases])
    picker.current([p.name for p in cases].index(args.case) if args.case else 0)
    picker.pack(side="left", padx=6)
    banner = ttk.Label(bar, text="", foreground="#b45309")
    banner.pack(side="left", padx=10)

    pane = ttk.Panedwindow(win, orient="horizontal")
    pane.pack(fill="both", expand=True)
    left = ttk.Frame(pane)
    right = ttk.Frame(pane, padding=8)
    pane.add(left, weight=3)
    pane.add(right, weight=2)

    cols = ("状态", "来源", "时限", "文书")
    tree = ttk.Treeview(left, columns=cols, show="tree headings")
    tree.heading("#0", text="模块 / 节点")
    tree.column("#0", width=320)
    for c, w in zip(cols, (70, 60, 240, 90)):
        tree.heading(c, text=c)
        tree.column(c, width=w)
    sb = ttk.Scrollbar(left, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="left", fill="y")
    for st, (_, fill, _) in STATUS.items():
        tree.tag_configure(st, background=fill)

    detail = tk.Text(right, wrap="word", height=20)
    detail.pack(fill="both", expand=True)
    openbtn = ttk.Button(right, text="打开最新文书", state="disabled")
    openbtn.pack(anchor="w", pady=6)
    state = {"ws": None, "nodes": {}}

    def open_doc(dry=False):
        rel = state.get("open_rel")
        if not rel:
            return "无文书"
        # #128：只许打开视图里列出的相对路径解析出、且解析后仍在工作区内的文件。
        ws = state["ws"]
        target = (ws / rel).resolve()
        try:
            target.relative_to(ws.resolve())
        except ValueError:
            return "拒：解析后跑出工作区 %s" % target
        if not target.exists():
            return "拒：文件不在 %s" % target
        if dry:
            return "放行 %s" % target
        os.startfile(str(target)) if hasattr(os, "startfile") else os.system('open "%s"' % target)
        return "已交给系统打开 %s" % target

    openbtn.configure(command=open_doc)

    def show(_evt=None):
        sel = tree.selection()
        detail.delete("1.0", "end")
        state["open_rel"] = None
        openbtn.configure(state="disabled")
        if not sel:
            return
        n = state["nodes"].get(sel[0])
        if not n:
            detail.insert("end", "（模块行）")
            return
        tpl = n["空白模板"]
        detail.insert("end", "%s\n\n状态：%s\n来源：%s\n空白模板：%s\n时限：%s\n" % (
            n["标题"], n["状态"], n["来源"],
            "无" if tpl == "无" else "%s %s" % (tpl["来源"], tpl["文件"]), n.get("时限") or "—"))
        vs = n.get("文书版本") or []
        detail.insert("end", "\n文书版本 %d 版\n" % len(vs))
        for d in vs:
            detail.insert("end", "  v%d  %s  %s\n" % (d["版本"], d["时间"], d["文书"]))
        detail.insert("end", "\n条目 %d 条\n" % len(n["条目"]))
        for e in n["条目"]:
            detail.insert("end", "  %s  %s  %s\n" % (e["动作"], e["时间"], e.get("原话") or e.get("文书") or ""))
        if vs:
            state["open_rel"] = vs[-1]["文书"]
            openbtn.configure(state="normal")

    tree.bind("<<TreeviewSelect>>", show)

    def load(_evt=None):
        # 切换整份替换，不留缓存（#128 防串第二条）。
        ws = cases[picker.current()]
        view = load_view(ws / VIEW)
        state["ws"] = ws
        state["nodes"] = {}
        tree.delete(*tree.get_children())
        win.title("案件便签（原型） — %s" % ws.name)     # 案件名 = 工作区目录名
        banner.configure(text=staleness(ws) or "")
        for m in view["模块"]:
            mid = tree.insert("", "end", text="%s（%s·%s）" % (m["标题"], m["状态"], m["来源"]), open=True)
            for n in m["节点"]:
                d = latest_doc(n)
                iid = tree.insert(mid, "end", text="  " + n["标题"], tags=(n["状态"],), values=(
                    "%s%s" % (STATUS.get(n["状态"], ("", "", "?"))[2], n["状态"]), n["来源"],
                    (n.get("时限") or "—")[:40], ("v%d" % d["版本"]) if d else "—"))
                state["nodes"][iid] = n
        if view["前方"]:
            fid = tree.insert("", "end", text="前方（领域图里还没进图的）", open=False)
            for m in view["前方"]:
                mid = tree.insert(fid, "end", text="%s（%s）" % (m["标题"], m["状态"]))
                for n in m["节点"]:
                    iid = tree.insert(mid, "end", text="  " + n["标题"], tags=("尚未进图",),
                                      values=("…尚未进图", n["来源"], (n.get("时限") or "—")[:40], "—"))
                    state["nodes"][iid] = dict(n, 文书版本=[], 条目=[])
        detail.delete("1.0", "end")

    picker.bind("<<ComboboxSelected>>", load)
    load()

    if args.selftest:
        # AFK 自检：每个案件都切一遍、每个节点都点一遍、开文书那道闸门干跑一遍。
        bad = 0
        for i, ws in enumerate(cases):
            picker.current(i)
            load()
            iids = list(state["nodes"])
            opened = []
            for iid in iids:
                tree.selection_set(iid)
                win.update_idletasks()
                show()
                if state.get("open_rel"):
                    opened.append(open_doc(dry=True))
            bad += sum(1 for o in opened if o.startswith("拒"))
            print("%-8s 节点 %3d  可开文书 %2d  被拒 %d  陈旧提示=%r"
                  % (ws.name, len(iids), len(opened),
                     sum(1 for o in opened if o.startswith("拒")), banner.cget("text")))
        print("自检完：被拒合计 %d" % bad)
        win.destroy()
        return
    if args.screenshot_after:
        win.after(int(args.screenshot_after * 1000), win.destroy)
    win.mainloop()


def main():
    p = argparse.ArgumentParser(description="案件便签原型（PROTOTYPE，#130）")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("mermaid", help="第一档：把 cwd 下的 图视图.json 打成 Mermaid + 表格")
    a.add_argument("--shape", choices=("full", "overview"), default="overview")
    a.set_defaults(func=cmd_mermaid)
    b = sub.add_parser("window", help="第二档：tkinter 窗口")
    b.add_argument("--root", help="案件根；给了就记进 ~/.loo0ng/原型-案件根")
    b.add_argument("--case", help="原型专用：开窗就选中这个案件，供 AFK 截图")
    b.add_argument("--selftest", action="store_true", help="原型专用：AFK 自检，每案每节点跑一遍")
    b.add_argument("--screenshot-after", type=float, default=0, help="原型专用：N 秒后自动关窗，供 AFK 截图")
    b.set_defaults(func=cmd_window)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
