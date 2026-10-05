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

# ---------- 表16.7(c) 最終的に国庫に残る仕入税額 K と税収不足額 L ----------
VAT_ROWS = ["VAT還付", "VAT否認", "VAT共謀"]
CDAT_ROWS = ["CDAT契機なし", "CDAT後の販売", "CDAT共謀", "旧版即時清算"]

def _check_167(r):
    """16.7節の本文の比較を、計算した K と L で確かめる"""
    for a in VAT_ROWS:
        for b in CDAT_ROWS:
            (kv, lv), (kc, lc) = r[a], r[b]
            assert lc - lv == kv - kc                                          # L_CDAT − L_VAT = K_VAT − K_CDAT
    assert r["CDAT契機なし"][0] > r["VAT還付"][0]                              # 還付が審査を通る ／ CDが契機を得ない
    assert r["CDAT後の販売"][0] < r["VAT否認"][0]                              # 還付を否認 ／ 後の販売の自動還付で相殺
    assert r["VAT還付"] == r["CDAT後の販売"] and r["VAT否認"] == r["CDAT契機なし"]  # 同じ額を相殺または還付すれば一致
    assert r["VAT共謀"] == r["CDAT共謀"] and r["CDAT共謀"][0] == 0            # 共謀による移転では両制度とも K = 0
    assert r["旧版即時清算"][0] == 0

def _check_sign(r):
    """S_u が K を下回る場合：L は負になり、L を0以上に限ると差の式が成り立たない組がある。その組の数を返す"""
    assert r["CDAT契機なし"][1] < 0
    bad = 0
    for a in VAT_ROWS:
        for b in CDAT_ROWS:
            (kv, lv), (kc, lc) = r[a], r[b]
            assert lc - lv == kv - kc
            if max(lc, 0) - max(lv, 0) != kv - kc: bad += 1
    assert bad > 0
    return bad

def t167c():
    """表16.7(c)。各行の K と L は scenarios.s7c の取引列から求める。"""
    r = S.s7c()
    assert r["sys"]["VAT"].rows == SC["16.7"]["VAT"].rows       # 表16.7(a)と同じ取引列
    assert r["sys"]["CDAT"].rows == SC["16.7"]["CDAT"].rows     # 表16.7(b)と同じ取引列
    _check_167(r)
    f = S.fmt
    rows = [("現行VAT", f"控除不足額{f(r['refund'])}を審査の後に還付", "VAT還付"),
            ("現行VAT", "控除不足額を審査で否認、または申告しない", "VAT否認"),
            ("現行VAT", "共謀する事業者への架空の販売によって控除を移す（17.4節(1)）", "VAT共謀"),
            ("CDAT", f"CD {f(r['cd'])}が還付の契機を得ない", "CDAT契機なし"),
            ("CDAT", "後の記録された販売の自動還付、または審査付き還付でCDが回収される", "CDAT後の販売"),
            ("CDAT", "共謀する事業者への架空の販売によってCDが移される（17.4節(1)）", "CDAT共謀"),
            ("旧版のCDAT", "即時清算によってCDを現金化", "旧版即時清算")]
    out = [f"表16.7(c) 最終的に国庫に残る仕入税額と税収不足額（S_u = {f(r['s_u'])}）",
           "\t".join(["制度", "仕入税額の扱い", "K_VAT／K_CDAT", "税収不足額"])]
    out += ["\t".join([a, b, f(r[k][0]), f(r[k][1])]) for a, b, k in rows]
    return "\n".join(out)

def ex41():
    """4.1節の例（仕入の税額10,000、記録された販売なし、S_u = 15,000）を、表16.7(c)と同じ計算で求める"""
    e = S.s7c(p_in=10000, s_rec=0, s_u=15000)
    _check_167(e)
    return e

def t167c_check():
    """表16.7(c)の照合の要約と、4.1節の例"""
    f = S.fmt
    r = S.s7c()
    m = sum(check_calc_string(row[9]) for x in r["all"] for row in x.rows)
    bad = _check_sign(S.s7c(s_u=300))
    e = ex41()
    return (f"表16.7(c)の照合：各行の K と L は、表16.7(a)(b)と同じ取引列に行ごとの続きを加えて計算した"
            f"（後の記録された販売と共謀する事業者の販売は、税額を3通りに変えた）。各行で L = S_u − K であり、"
            f"K は国庫の受領累計と台帳の両方から求めて一致した。同じ行にまとめた続き（否認と申告しない、後の販売と審査付き還付）は"
            f"同じ K と L を与えた。現行VATの行とCDATの行のすべての組で L_CDAT − L_VAT = K_VAT − K_CDAT が成り立った。"
            f"S_u = 300 では L が負の行があり、L を0以上に限ると差の式が成り立たない組が{bad}組あった。"
            f"取引列の計算式 {m} 個で左辺と右辺が一致した。\n"
            f"同じ計算による4.1節の例（仕入の税額{f(10000)}、記録された販売なし、S_u = {f(15000)}）：税収不足額は、"
            f"現行VATで還付申告が審査を通れば{f(e['VAT還付'][1])}、還付申告を行わなければ{f(e['VAT申告せず'][1])}"
            f"（国庫に残る仕入税額{f(e['VAT申告せず'][0])}）、CDATでCDが還付の契機を得なければ{f(e['CDAT契機なし'][1])}、"
            f"審査付き還付が認められれば{f(e['CDAT審査付き還付'][1])}、旧版の即時清算では{f(e['旧版即時清算'][1])}"
            f"（国庫に残る仕入税額{f(e['旧版即時清算'][0])}）。")
