"""論文の16節と付録Bの表、および付録B.1の各行の計算式を作る関数。"""
import re
from fractions import Fraction as F
import scenarios as S
import appendix_b as B

SC = S.all_scenarios()

def table(key, sysname, title):
    return S.table_text(title, SC[key][sysname].rows)

def detail(key, vname, cname, title):
    vat = SC[key][vname]; cdat = SC[key][cname]
    out = [title, "\t".join(["時点", "事象", "現行VAT：事業者ごとの未精算額", "CDAT：当該事象の額", "CDAT：事象後のCD等"])]
    vrows = {r[0]: r for r in vat.rows}; crows = {r[0]: r for r in cdat.rows}
    order = []
    for r in vat.rows + cdat.rows:
        if r[0] not in order: order.append(r[0])
    # 時点の並びを自然な順に（数字、数字+、期n末、期n末+、退出、退出+）
    def keyf(t):
        m = re.match(r"^(\d+)(\+?)$", t)
        if m: return (int(m.group(1)), 0, len(m.group(2)))
        m = re.match(r"^期(\d+)末(\+?)$", t)
        if m: return (int(m.group(1)), 1, len(m.group(2)))
        m = re.match(r"^退出(\+?)$", t)
        if m: return (10**6, 1, len(m.group(1)))
        return (10**7, 0, 0)
    # 取引の時点番号と期の対応：期末の行は、その期の取引の後に置く。scenarios の行の順序を基準にする
    seq = []
    for r in vat.rows:
        if r[0] not in seq: seq.append(r[0])
    for r in cdat.rows:
        if r[0] not in seq:
            # CDATにだけある行は、CDATの直前の行の後に挿入
            idx = [x[0] for x in cdat.rows].index(r[0])
            prev = cdat.rows[idx - 1][0] if idx > 0 else None
            pos = seq.index(prev) + 1 if prev in seq else len(seq)
            # 既に挿入した「+」行の後ろに続ける
            while pos < len(seq) and seq[pos] not in vrows and seq[pos] in crows:
                pos += 1
            seq.insert(pos, r[0])
    for t in seq:
        v = vrows.get(t); c = crows.get(t)
        if v and c and v[1] != c[1]:
            ev = f"現行VAT：{v[1]}／CDAT：{c[1]}"
        else:
            ev = (c or v)[1]
        out.append("\t".join([t, ev, v[7] if v else "—", (c[8] or "—") if c else "—", c[7] if c else "—"]))
    # 各行の計算（足し算、引き算、min）と、最終行の命題2の検算
    tid = title.split()[0]
    lines = [f"{tid}の各行の計算"]
    for t in seq:
        v = vrows.get(t); c = crows.get(t)
        segs = []
        if v: segs.append(f"現行VAT：{v[9]}。")
        if c: segs.append(f"CDAT：{c[9]}。")
        lines.append(f"・{t}　" + "".join(segs))
    lv = vat.rows[-1]; lc = cdat.rows[-1]
    f = S.fmt
    lines.append(f"・検算（最終行）　国庫の受領累計 = 発生税収 + 立替 − 預かり：現行VAT {f(lv[3])} = {f(lv[4])} + {f(lv[6])} − {f(lv[5])}、"
                 f"CDAT {f(lc[3])} = {f(lc[4])} + {f(lc[6])} − {f(lc[5])}。")
    return "\n".join(out) + "\n\n" + "\n".join(lines)

# ---------- 計算式の検算：「式 = 数」の形をすべて取り出して評価する ----------
import re as _re
from fractions import Fraction as _F
_NUM = r"[+−]?\d[\d,]*(?:\.\d+)?"
def _tofrac(tok):
    tok = tok.replace(",", "").replace("−", "-").replace("+", "")
    return _F(tok)
def _eval(expr):
    e = expr.replace(", ", ";")                      # min の引数の区切り
    e = _re.sub(r"\d[\d,]*(?:\.\d+)?", lambda m: f"_F('{m.group(0).replace(',', '')}')", e)
    e = e.replace(";", ",").replace("−", "-").replace("×", "*")
    return _F(eval(e, {"_F": _F, "min": min}))
def check_calc_string(sx):
    n = 0
    sx = _re.sub(r"Debt\(事業者\d+\)|Tax_pending\(事業者\d+\)|事業者\d+(のCD)?", "#", sx)
    allowed = set("0123456789,. +−×()min")
    for m in _re.finditer(r" = (" + _NUM + ")", sx):
        j = m.start(); k = j
        while k > 0 and sx[k - 1] in allowed: k -= 1
        expr = sx[k:j].strip()
        # 式の先頭に残る閉じていない括弧などを除く
        while expr and expr.count("(") < expr.count(")"): expr = expr[expr.index(")") + 1:].strip()
        while expr and expr.count("(") > expr.count(")") and not expr.startswith("min("): expr = expr[1:].strip()
        if not expr or not _re.search(r"\d", expr): continue
        lhs = _eval(expr); rhs = _tofrac(m.group(1))
        assert lhs == rhs, (sx, expr, lhs, rhs)
        n += 1
    return n

def check_all_calcs():
    total = 0
    for key, d in SC.items():
        for name, sysobj in d.items():
            for r in sysobj.rows:
                total += check_calc_string(r[9])
    return total

def maxhold(key, name): return max(r[5] for r in SC[key][name].rows)
def final(key, name): return SC[key][name].rows[-1][4]

def summary():
    f = S.fmt
    # 検算：最終の発生税収が両制度で一致
    for k, d in SC.items():
        vals = {final(k, n) for n in d}
        assert len(vals) == 1, (k, vals)
    rows = [
        ("16.1 通常の多段階取引", f(final("16.1", "VAT")), f"{f(maxhold('16.1','VAT'))} → {f(maxhold('16.1','CDAT'))}",
         "期中の相殺 ／ 次の販売の自動還付", "毎期の申告 ／ なし"),
        ("16.2 設備投資", f(final("16.2", "VAT")), f"{f(maxhold('16.2','VAT'))} → {f(maxhold('16.2','CDAT（自動還付のみ）'))}",
         "期1末の審査後の還付 ／ 販売ごとの自動還付、または審査付き還付", "還付審査 ／ 審査付き還付を用いる場合のみ"),
        ("16.3 輸出", f(final("16.3", "VAT")), f"{f(maxhold('16.3','VAT'))} → {f(maxhold('16.3','CDAT'))}",
         "期末の審査後の還付 ／ 輸出の確認時の輸出還付", "還付審査 ／ なし（税関の記録）"),
        ("16.4 輸入", f(final("16.4", "VAT")), f"{f(maxhold('16.4','VAT'))} → {f(maxhold('16.4','CDAT'))}",
         "期中の相殺 ／ 次の販売の自動還付", "毎期の申告 ／ なし"),
        ("16.5 事業退出", f"{f(final('16.5a','VAT'))}（廃棄）、{f(final('16.5b','VAT'))}（私的使用）",
         f"{f(max(maxhold('16.5a','VAT'), maxhold('16.5b','VAT')))} → {f(max(maxhold('16.5a','CDAT'), maxhold('16.5b','CDAT')))}",
         "最終の申告での審査後の還付 ／ 廃業時の審査付き還付（私的使用の場合はいずれも還付なし）", "退出時の還付審査 ／ 廃業時の審査"),
        ("16.6 長期間売上のない事業者", f(final("16.6", "VAT")), f"{f(maxhold('16.6','VAT'))} → {f(maxhold('16.6','CDAT（自動還付のみ）'))}",
         "毎期の審査後の還付 ／ 最初の販売の自動還付、または審査付き還付", "毎期の還付審査 ／ 審査付き還付を用いる場合のみ"),
        ("16.7 現金売上が記録されない場合", f"{f(final('16.7','VAT'))}（記録分。真の値は1,500）", f"{f(maxhold('16.7','VAT'))} → {f(maxhold('16.7','CDAT'))}",
         "（税収不足額の比較は16.7節）", "還付審査 ／ 還付保留と記録の照合"),
        ("16.8 共通仕入", f(final("16.8", "VAT")), f"{f(maxhold('16.8','VAT'))} → {f(maxhold('16.8','CDAT'))}（返還債務）",
         "期中の相殺（期末に按分を確定） ／ 販売時の自動還付（暫定割合）と期末調整", "毎期の申告 ／ 期末調整"),
        ("16.9 複数税率", f"{f(final('16.9a','VAT'))}（2例とも）",
         f"{f(maxhold('16.9a','VAT'))}、{f(maxhold('16.9b','VAT'))} → {f(max(maxhold('16.9a','CDAT'), maxhold('16.9b','CDAT')))}",
         "期中の相殺、構造的な超過は審査後の還付 ／ 次の販売の自動還付、構造的な超過は審査付き還付", "毎期の申告と還付審査 ／ 例外的申請"),
    ]
    assert final("16.9b", "VAT") == final("16.9a", "VAT")
    head = ["事例", "発生税収（両制度で一致）", "預かりの最大値（現行VAT → CDAT）", "立替の回収（現行VAT ／ CDAT）", "審査の契機（現行VAT ／ CDAT）"]
    out = ["表16.10 事例の総括", "\t".join(head)] + ["\t".join(r) for r in rows]
    return "\n".join(out)

# ---------- 計算式の検算：「式 = 数」の形をすべて取り出して評価する ----------
import re as _re
from fractions import Fraction as _F
_NUM = r"[+−]?\d[\d,]*(?:\.\d+)?"
def _tofrac(tok):
    tok = tok.replace(",", "").replace("−", "-").replace("+", "")
    return _F(tok)
def _eval(expr):
    e = expr.replace(", ", ";")                      # min の引数の区切り
    e = _re.sub(r"\d[\d,]*(?:\.\d+)?", lambda m: f"_F('{m.group(0).replace(',', '')}')", e)
    e = e.replace(";", ",").replace("−", "-").replace("×", "*")
    return _F(eval(e, {"_F": _F, "min": min}))
def check_calc_string(sx):
    n = 0
    sx = _re.sub(r"Debt\(事業者\d+\)|Tax_pending\(事業者\d+\)|事業者\d+(のCD)?", "#", sx)
    allowed = set("0123456789,. +−×()min")
    for m in _re.finditer(r" = (" + _NUM + ")", sx):
        j = m.start(); k = j
        while k > 0 and sx[k - 1] in allowed: k -= 1
        expr = sx[k:j].strip()
        # 式の先頭に残る閉じていない括弧などを除く
        while expr and expr.count("(") < expr.count(")"): expr = expr[expr.index(")") + 1:].strip()
        while expr and expr.count("(") > expr.count(")") and not expr.startswith("min("): expr = expr[1:].strip()
        if not expr or not _re.search(r"\d", expr): continue
        lhs = _eval(expr); rhs = _tofrac(m.group(1))
        assert lhs == rhs, (sx, expr, lhs, rhs)
        n += 1
    return n

def check_all_calcs():
    total = 0
    for key, d in SC.items():
        for name, sysobj in d.items():
            for r in sysobj.rows:
                total += check_calc_string(r[9])
    return total

def maxhold(key, name): return max(r[5] for r in SC[key][name].rows)
def final(key, name): return SC[key][name].rows[-1][4]

def summary():
    f = S.fmt
    # 検算：最終の発生税収が両制度で一致
    for k, d in SC.items():
        vals = {final(k, n) for n in d}
        assert len(vals) == 1, (k, vals)
    rows = [
        ("16.1 通常の多段階取引", f(final("16.1", "VAT")), f"{f(maxhold('16.1','VAT'))} → {f(maxhold('16.1','CDAT'))}",
         "期中の相殺 ／ 次の販売の自動還付", "毎期の申告 ／ なし"),
        ("16.2 設備投資", f(final("16.2", "VAT")), f"{f(maxhold('16.2','VAT'))} → {f(maxhold('16.2','CDAT（自動還付のみ）'))}",
         "期1末の審査後の還付 ／ 販売ごとの自動還付、または審査付き還付", "還付審査 ／ 審査付き還付を用いる場合のみ"),
        ("16.3 輸出", f(final("16.3", "VAT")), f"{f(maxhold('16.3','VAT'))} → {f(maxhold('16.3','CDAT'))}",
         "期末の審査後の還付 ／ 輸出の確認時の輸出還付", "還付審査 ／ なし（税関の記録）"),
        ("16.4 輸入", f(final("16.4", "VAT")), f"{f(maxhold('16.4','VAT'))} → {f(maxhold('16.4','CDAT'))}",
         "期中の相殺 ／ 次の販売の自動還付", "毎期の申告 ／ なし"),
        ("16.5 事業退出", f"{f(final('16.5a','VAT'))}（廃棄）、{f(final('16.5b','VAT'))}（私的使用）",
         f"{f(max(maxhold('16.5a','VAT'), maxhold('16.5b','VAT')))} → {f(max(maxhold('16.5a','CDAT'), maxhold('16.5b','CDAT')))}",
         "最終の申告での審査後の還付 ／ 廃業時の審査付き還付（私的使用の場合はいずれも還付なし）", "退出時の還付審査 ／ 廃業時の審査"),
        ("16.6 長期間売上のない事業者", f(final("16.6", "VAT")), f"{f(maxhold('16.6','VAT'))} → {f(maxhold('16.6','CDAT（自動還付のみ）'))}",
         "毎期の審査後の還付 ／ 最初の販売の自動還付、または審査付き還付", "毎期の還付審査 ／ 審査付き還付を用いる場合のみ"),
        ("16.7 現金売上が記録されない場合", f"{f(final('16.7','VAT'))}（記録分。真の値は1,500）", f"{f(maxhold('16.7','VAT'))} → {f(maxhold('16.7','CDAT'))}",
         "（税収不足額の比較は16.7節）", "還付審査 ／ 還付保留と記録の照合"),
        ("16.8 共通仕入", f(final("16.8", "VAT")), f"{f(maxhold('16.8','VAT'))} → {f(maxhold('16.8','CDAT'))}（返還債務）",
         "期中の相殺（期末に按分を確定） ／ 販売時の自動還付（暫定割合）と期末調整", "毎期の申告 ／ 期末調整"),
        ("16.9 複数税率", f"{f(final('16.9a','VAT'))}（2例とも）",
         f"{f(maxhold('16.9a','VAT'))}、{f(maxhold('16.9b','VAT'))} → {f(max(maxhold('16.9a','CDAT'), maxhold('16.9b','CDAT')))}",
         "期中の相殺、構造的な超過は審査後の還付 ／ 次の販売の自動還付、構造的な超過は審査付き還付", "毎期の申告と還付審査 ／ 例外的申請"),
    ]
    assert final("16.9b", "VAT") == final("16.9a", "VAT")
    head = ["事例", "発生税収（両制度で一致）", "預かりの最大値（現行VAT → CDAT）", "立替の回収（現行VAT ／ CDAT）", "審査の契機（現行VAT ／ CDAT）"]
    out = ["表16.10 事例の総括", "\t".join(head)] + ["\t".join(r) for r in rows]
    return "\n".join(out)

def build(template_path, out_path):
    txt = open(template_path, encoding="utf-8").read()
    t31, ro, rn, to, tn = B.b31()
    assert (ro, rn, to, tn) == (100, 300, 800, 600)
    repl = {"@@B31@@": t31, "@@B32@@": B.b32(), "@@B33@@": B.b33(), "@@B34@@": B.b34(), "@@B35@@": B.b35(),
            "@@B31_OLD@@": S.fmt(to), "@@B31_NEW@@": S.fmt(tn), "@@SUMMARY@@": summary(),
            "@@B36G@@": B.b36g()}
    for k, v in repl.items():
        assert k in txt, k
        txt = txt.replace(k, v)
    def sub_table(m):
        key, sysname, title = m.group(1).split("|")
        return table(key, sysname, title)
    def sub_detail(m):
        key, vname, cname, title = m.group(1).split("|")
        return detail(key, vname, cname, title)
    txt = re.sub(r"@@TABLE\|(.+?)@@", sub_table, txt)
    txt = re.sub(r"@@DETAIL\|(.+?)@@", sub_detail, txt)
    assert "@@" not in txt, re.findall(r"@@.*?@@", txt)[:5]
    assert "Σ" not in txt
    open(out_path, "w", encoding="utf-8").write(txt)
    return txt
