"""論文の16節の九つの事例と付録B.2、B.3.6の事例：同じ取引列に現行VATとCDATを適用し、時点ごとに
  国庫の受払い、国庫の受領累計、発生税収、預かり、立替
を計算する。両制度で
  国庫の受領累計 = 発生税収 + 立替 − 預かり
が成り立つことを assert で検算する。

現行VATモデル（15.1節）
  ・各登録事業者は課税期間の末に（売上税額 − 控除額）を申告し、正なら納付、負なら審査の後に還付を受ける。
  ・輸入は税関で課税し、登録事業者は控除する。輸出は免税で、その仕入税額は控除する。
  ・非課税売上だけに対応する仕入税額は控除しない。共通仕入は期中は暫定割合で控除見込みとし、期末に確定割合で調整する
    （発生税収の比較の便宜のため、CDATと同じ暫定割合を用いる）。
  預かり = 各事業者の未精算の純額（売上税額 − 控除額）のうち正の部分の合計
  立替   = 未精算の純額のうち負の部分の合計 ＋ 申告後・審査前の還付待ち
  発生税収 = 売上税額と輸入税額の累計 − 控除額の累計
CDAT
  預かり = Tax_pending + Debt_tot、立替 = CD_tot、発生税収 = Tax_nc
"""
from fractions import Fraction as F

def fmt(v):
    v = F(v)
    return f"{int(v):,}" if v.denominator == 1 else f"{float(v):,.1f}"

def fflow(v):
    v = F(v)
    if v == 0: return "0"
    return ("+" if v > 0 else "−") + fmt(abs(v))

def num(v):
    """計算式の中の数：負は「−」を付け、正には符号を付けない"""
    v = F(v)
    return ("−" + fmt(-v)) if v < 0 else fmt(v)

class VAT:
    def __init__(s):
        s.cash = F(0); s.gross = F(0); s.ded_cum = F(0)
        s.out = {}; s.ded = {}; s.pend = {}; s.common = {}   # common[b] = [(tax, e_prov), ...]
        s.rows = []
    def _g(s, d, k): return d.get(k, F(0))
    def net(s, b): return s._g(s.out, b) - s._g(s.ded, b)
    def accrued(s): return s.gross - s.ded_cum
    def fl_bd(s):
        fl = bd = F(0)
        for b in set(s.out) | set(s.ded) | set(s.pend):
            net = s._g(s.out, b) - s._g(s.ded, b)
            if net > 0: fl += net
            else: bd += -net
            bd += s._g(s.pend, b)
        return fl, bd
    def detail(s):
        parts = []
        for b in sorted(set(s.out) | set(s.ded) | set(s.pend)):
            net = s._g(s.out, b) - s._g(s.ded, b)
            if net != 0: parts.append(f"{b} {fflow(net)}")
            if s._g(s.pend, b) != 0: parts.append(f"{b} 還付待ち{fmt(s._g(s.pend, b))}")
        return "、".join(parts) if parts else "なし"
    def log(s, t, ev, flow=0, calc=None):
        fl, bd = s.fl_bd(); acc = s.accrued()
        assert s.cash == acc + bd - fl, ("VAT", t, ev, s.cash, acc, bd, fl)
        s.rows.append((t, ev, F(flow), s.cash, acc, fl, bd, s.detail(), "", calc or "変化なし"))
    def sale(s, t, ev, seller, buyer, tax, e=1, common_prov=None, log=True):
        tax = F(tax)
        n0 = s.net(seller)
        s.out[seller] = s._g(s.out, seller) + tax; s.gross += tax
        parts = [f"{seller} {num(n0)} + {fmt(tax)} = {num(s.net(seller))}"]
        if buyer != 'GEN':
            nb0 = s.net(buyer)
            if common_prov is not None:
                d = F(common_prov) * tax; dexpr = f"{fmt(common_prov)} × {fmt(tax)}"
                s.common.setdefault(buyer, []).append((tax, F(common_prov)))
            else:
                d = F(e) * tax; dexpr = fmt(tax) if F(e) == 1 else f"{fmt(e)} × {fmt(tax)}"
            s.ded[buyer] = s._g(s.ded, buyer) + d; s.ded_cum += d
            parts.append(f"{buyer} {num(nb0)} − {dexpr} = {num(s.net(buyer))}")
        if log: s.log(t, ev, calc="、".join(parts))
    def imp(s, t, ev, importer, tax, e=1):
        tax = F(tax); s.cash += tax; s.gross += tax
        parts = [f"国庫 +{fmt(tax)}（税関）"]
        if importer != 'GEN':
            n0 = s.net(importer)
            d = F(e) * tax; s.ded[importer] = s._g(s.ded, importer) + d; s.ded_cum += d
            parts.append(f"{importer} {num(n0)} − {fmt(d)} = {num(s.net(importer))}")
        s.log(t, ev, tax, calc="、".join(parts))
    def deemed(s, t, ev, b, tax):
        n0 = s.net(b)
        s.out[b] = s._g(s.out, b) + F(tax); s.gross += F(tax)
        s.log(t, ev, calc=f"{b} {num(n0)} + {fmt(tax)} = {num(s.net(b))}（みなし譲渡の売上税額）")
    def period_end(s, t, ev, ratio=None, only=None):
        ratio = ratio or {}
        parts = []
        for b, lst in list(s.common.items()):
            r = F(ratio[b])
            for tax, ep in lst:
                adj = (r - ep) * tax
                n0 = s.net(b)
                s.ded[b] = s._g(s.ded, b) + adj; s.ded_cum += adj
                op = f"{num(n0)} + {fmt(-adj)}" if adj < 0 else f"{num(n0)} − {fmt(adj)}"
                parts.append(f"{b}の共通仕入の控除の調整 ({fmt(r)} − {fmt(ep)}) × {fmt(tax)} = {num(adj)}、未精算 {op} = {num(s.net(b))}")
        s.common = {}
        flow = F(0); pays = []
        for b in sorted(set(s.out) | set(s.ded)):
            if only is not None and b not in only: continue
            net = s._g(s.out, b) - s._g(s.ded, b)
            if net > 0:
                s.cash += net; flow += net; pays.append(fmt(net)); parts.append(f"{b} {fmt(net)}を納付")
            elif net < 0:
                s.pend[b] = s._g(s.pend, b) - net; parts.append(f"{b} {num(net)}は還付待ち{fmt(-net)}")
            s.out.pop(b, None); s.ded.pop(b, None)
        if len(pays) > 1: parts.append(f"国庫 {' + '.join(pays)} = +{fmt(flow)}")
        elif len(pays) == 1: parts.append(f"国庫 +{fmt(flow)}")
        s.log(t, ev, flow, calc="、".join(parts) if parts else "未精算なし")
    def refund(s, t, ev, b):
        a = s._g(s.pend, b); s.pend[b] = F(0); s.cash -= a
        s.log(t, ev, -a, calc=f"{b} 還付待ち{fmt(a)}を還付、国庫 −{fmt(a)}")

class CDAT:
    def __init__(s):
        s.CD = {}; s.IT = {}; s.TP = {}; s.Debt = {}
        s.TaxRec = F(0); s.cash = F(0); s.rows = []
        s.Rauto = F(0); s.Rexp = F(0); s.Rrev = F(0)
    def _g(s, d, k): return d.get(k, F(0))
    def taxnc(s): return s.TaxRec - sum(s.IT.values(), F(0))
    def detail(s):
        parts = [f"{b} {fmt(v)}" for b, v in sorted(s.CD.items()) if v != 0]
        parts += [f"Tax_pending({b}) {fmt(v)}" for b, v in sorted(s.TP.items()) if v != 0]
        parts += [f"Debt({b}) {fmt(v)}" for b, v in sorted(s.Debt.items()) if v != 0]
        return "、".join(parts) if parts else "なし"
    def log(s, t, ev, flow=0, amt="", calc=None):
        CDt = sum(s.CD.values(), F(0)); fl = sum(s.TP.values(), F(0)) + sum(s.Debt.values(), F(0))
        acc = s.taxnc()
        assert s.cash == acc + CDt - fl, ("CDAT", t, ev, s.cash, acc, CDt, fl)
        assert all(v >= 0 for v in s.CD.values())
        s.rows.append((t, ev, F(flow), s.cash, acc, fl, CDt, s.detail(), amt, calc or "変化なし"))
    def add_elig(s, b, te):
        s.CD[b] = s._g(s.CD, b) + te; s.IT[b] = s._g(s.IT, b) + te
    def sale(s, t, ev, seller, buyer, tax, e=1, cash_unpaid=False, beta_zero=False, why0="還付保留中または取引時に記録されなかった販売"):
        tax = F(tax); cd0 = s._g(s.CD, seller)
        beta = F(0) if beta_zero else min(tax, cd0)
        s.CD[seller] = cd0 - beta; s.Rauto += beta; s.TaxRec += tax
        parts = [f"β = 0（{why0}）" if beta_zero else f"β = min({fmt(tax)}, {fmt(cd0)}) = {fmt(beta)}"]
        if cash_unpaid:
            tp0 = s._g(s.TP, seller); s.TP[seller] = tp0 + tax - beta; flow = F(0)
            parts.append(f"Tax_pending({seller}) {fmt(tp0)} + {fmt(tax)} − {fmt(beta)} = {fmt(s.TP[seller])}")
        else:
            s.cash += tax - beta; flow = tax - beta
            parts.append(f"国庫 {fmt(tax)} − {fmt(beta)} = {fflow(flow)}")
        if beta > 0: parts.append(f"{seller}のCD {fmt(cd0)} − {fmt(beta)} = {fmt(s.CD[seller])}")
        if buyer != 'GEN':
            cdb0 = s._g(s.CD, buyer); te = F(e) * tax
            s.add_elig(buyer, te)
            note = "" if F(e) == 1 else f"（適格仕入税額 {fmt(e)} × {fmt(tax)} = {fmt(te)}）"
            parts.append(f"{buyer}のCD {fmt(cdb0)} + {fmt(te)} = {fmt(s.CD[buyer])}{note}")
        s.log(t, ev, flow, f"β={fmt(beta)}", calc="、".join(parts))
        return beta
    def imp(s, t, ev, importer, tax, e=1):
        tax = F(tax); s.TaxRec += tax; s.cash += tax
        parts = [f"国庫 +{fmt(tax)}（税関）"]
        if importer != 'GEN':
            cd0 = s._g(s.CD, importer); te = F(e) * tax
            s.add_elig(importer, te)
            parts.append(f"{importer}のCD {fmt(cd0)} + {fmt(te)} = {fmt(s.CD[importer])}")
        s.log(t, ev, tax, "β=0", calc="、".join(parts))
    def _refund(s, b, a):
        s.CD[b] = s._g(s.CD, b) - a
        off = min(a, s._g(s.TP, b)); s.TP[b] = s._g(s.TP, b) - off
        s.cash -= a - off
        return a - off, off
    def export(s, t, ev, b, t_virt):
        cd0 = s._g(s.CD, b)
        x = min(F(t_virt), cd0); s.Rexp += x; paid, off = s._refund(b, x)
        parts = [f"x = min({fmt(t_virt)}, {fmt(cd0)}) = {fmt(x)}"]
        if off: parts.append(f"うちTax_pendingへの充当{fmt(off)}")
        parts += [f"国庫 −{fmt(paid)}", f"{b}のCD {fmt(cd0)} − {fmt(x)} = {fmt(s.CD[b])}"]
        s.log(t, ev, -paid, f"x={fmt(x)}", calc="、".join(parts)); return x
    def reviewed(s, t, ev, b, a):
        a = F(a); cd0 = s._g(s.CD, b); assert a <= cd0
        s.Rrev += a; paid, off = s._refund(b, a)
        parts = [f"a = {fmt(a)}（審査で認められた額。CD {fmt(cd0)}以下）"]
        if off: parts.append(f"うちTax_pendingへの充当{fmt(off)}")
        parts += [f"国庫 −{fmt(paid)}", f"{b}のCD {fmt(cd0)} − {fmt(a)} = {fmt(s.CD[b])}"]
        s.log(t, ev, -paid, f"a={fmt(a)}", calc="、".join(parts)); return a
    def correct(s, t, ev, b, D, why=""):
        D = min(F(D), s._g(s.IT, b)); s.IT[b] = s._g(s.IT, b) - D
        cd0 = s._g(s.CD, b); debt0 = s._g(s.Debt, b)
        c = min(D, cd0); s.CD[b] = cd0 - c; s.Debt[b] = debt0 + D - c
        parts = [f"Δ = {fmt(D)}{why}", f"c = min({fmt(D)}, {fmt(cd0)}) = {fmt(c)}", f"d = {fmt(D)} − {fmt(c)} = {fmt(D - c)}"]
        if c > 0: parts.append(f"{b}のCD {fmt(cd0)} − {fmt(c)} = {fmt(s.CD[b])}")
        if D - c > 0: parts.append(f"Debt({b}) {fmt(debt0)} + {fmt(D - c)} = {fmt(s.Debt[b])}")
        s.log(t, ev, 0, f"Δ={fmt(D)}（c={fmt(c)}、d={fmt(D - c)}）", calc="、".join(parts)); return c, D - c
    def upward(s, t, ev, b, u, why=""):
        cd0 = s._g(s.CD, b); s.add_elig(b, F(u))
        s.log(t, ev, 0, f"上方調整{fmt(u)}", calc=f"{b}のCD {fmt(cd0)} + {fmt(u)} = {fmt(s.CD[b])}{why}")
    def repay(s, t, ev, b, v):
        d0 = s._g(s.Debt, b)
        v = min(F(v), d0); s.Debt[b] = d0 - v; s.cash += v
        s.log(t, ev, v, f"v={fmt(v)}", calc=f"v = {fmt(v)}、国庫 +{fmt(v)}、Debt({b}) {fmt(d0)} − {fmt(v)} = {fmt(s.Debt[b])}")
    def pay_pending(s, t, ev, b, q):
        tp0 = s._g(s.TP, b)
        q = min(F(q), tp0); s.TP[b] = tp0 - q; s.cash += q
        s.log(t, ev, q, f"q={fmt(q)}", calc=f"q = {fmt(q)}、国庫 +{fmt(q)}、Tax_pending({b}) {fmt(tp0)} − {fmt(q)} = {fmt(s.TP[b])}")
    def note(s, t, ev, calc=None): s.log(t, ev, calc=calc)

HEAD = ["時点", "事象", "国庫の受払い", "国庫の受領累計", "発生税収", "預かり", "立替"]

def table_text(title, rows):
    out = [title, "\t".join(HEAD)]
    for r in rows:
        t, ev, flow, cash, acc, fl, bd = r[:7]
        out.append("\t".join([t, ev, fflow(flow), fmt(cash), fmt(acc), fmt(fl), fmt(bd)]))
    return "\n".join(out)

def detail_text(title, vat, cdat):
    """付録B：同じ時点の行を並べ、VATの事業者ごとの未精算額と、CDATの還付額等・事業者ごとのCDを示す"""
    out = [title, "\t".join(["時点", "事象", "現行VAT：事業者ごとの未精算額", "CDAT：当該事象の額", "CDAT：事象後のCD等"])]
    vrows = {r[0]: r for r in vat.rows}
    crows = {r[0]: r for r in cdat.rows}
    order = []
    for r in vat.rows + cdat.rows:
        if r[0] not in order: order.append(r[0])
    for t in order:
        v = vrows.get(t); c = crows.get(t)
        ev = (c or v)[1]
        out.append("\t".join([t, ev, v[7] if v else "—", (c[8] or "—") if c else "—", c[7] if c else "—"]))
    return "\n".join(out)

# ------------------------------------------------------------------
def s1():
    v = VAT(); c = CDAT()
    ev = [("1", "事業者1→事業者2", "事業者1", "事業者2", 100),
          ("2", "事業者2→事業者3", "事業者2", "事業者3", 200),
          ("3", "事業者3→消費者", "事業者3", "GEN", 300)]
    for t, e, a, b, x in ev:
        v.sale(t, f"{e}（税額{x:,}）", a, b, x); c.sale(t, f"{e}（税額{x:,}）", a, b, x)
    v.period_end("期1末", "申告・納付"); c.note("期1末", "手続なし")
    return {"VAT": v, "CDAT": c}

def s2():
    v = VAT(); c = CDAT(); r = CDAT()
    v.sale("1", "設備：事業者1→事業者2（税額2,000）", "事業者1", "事業者2", 2000)
    c.sale("1", "設備：事業者1→事業者2（税額2,000）", "事業者1", "事業者2", 2000)
    r.sale("1", "設備：事業者1→事業者2（税額2,000）", "事業者1", "事業者2", 2000)
    r.reviewed("1+", "審査付き還付（大型設備投資）", "事業者2", 2000)
    def sell(t):
        for x in (v, c, r): x.sale(t, "事業者2→消費者（税額500）", "事業者2", "GEN", 500)
    sell("2")
    v.period_end("期1末", "申告（事業者2は還付申告）"); c.note("期1末", "手続なし"); r.note("期1末", "手続なし")
    v.refund("期1末+", "審査後の還付", "事業者2")
    sell("3"); sell("4")
    v.period_end("期2末", "申告・納付"); c.note("期2末", "手続なし"); r.note("期2末", "手続なし")
    sell("5"); sell("6")
    v.period_end("期3末", "申告・納付"); c.note("期3末", "手続なし"); r.note("期3末", "手続なし")
    return {"VAT": v, "CDAT（自動還付のみ）": c, "CDAT（審査付き還付を利用）": r}

def s3():
    v = VAT(); c = CDAT()
    for x in (v, c): x.sale("1", "原材料：事業者1→事業者2（税額1,000）", "事業者1", "事業者2", 1000)
    v.log("2", "事業者2が輸出（仮想税額1,500）", calc="輸出は免税（売上税額0）のため未精算は変化なし"); c.export("2", "輸出の確認と輸出還付（仮想税額1,500）", "事業者2", 1500)
    v.period_end("期1末", "申告（事業者2は還付申告）"); c.note("期1末", "手続なし")
    v.refund("期1末+", "審査後の還付", "事業者2")
    return {"VAT": v, "CDAT": c}

def s3b():
    """輸出還付の上限が効く場合（付録B）：設備3,000と原材料1,000の後、仮想税額1,500の輸出を2回"""
    v = VAT(); c = CDAT()
    for x in (v, c):
        x.sale("1", "設備：事業者1→事業者2（税額3,000）", "事業者1", "事業者2", 3000)
        x.sale("2", "原材料：事業者3→事業者2（税額1,000）", "事業者3", "事業者2", 1000)
    v.log("3", "輸出（仮想税額1,500）", calc="輸出は免税（売上税額0）のため未精算は変化なし"); c.export("3", "輸出還付（仮想税額1,500）", "事業者2", 1500)
    v.period_end("期1末", "申告（還付申告）"); c.note("期1末", "手続なし")
    v.refund("期1末+", "審査後の還付", "事業者2")
    v.log("4", "輸出（仮想税額1,500）", calc="輸出は免税（売上税額0）のため未精算は変化なし"); c.export("4", "輸出還付（仮想税額1,500）", "事業者2", 1500)
    v.period_end("期2末", "申告"); c.note("期2末", "手続なし")
    return {"VAT": v, "CDAT": c}

def s4():
    v = VAT(); c = CDAT()
    for x in (v, c):
        x.imp("1", "事業者1が輸入（税関で税額600）", "事業者1", 600)
        x.imp("2", "消費者が輸入（税関で税額100）", "GEN", 100)
        x.sale("3", "事業者1→消費者（税額900）", "事業者1", "GEN", 900)
    v.period_end("期1末", "申告・納付"); c.note("期1末", "手続なし")
    return {"VAT": v, "CDAT": c}

def s5():
    res = {}
    for case in ("a", "b"):
        v = VAT(); c = CDAT()
        for x in (v, c):
            x.sale("1", "商品：事業者1→事業者2（税額400）", "事業者1", "事業者2", 400)
            x.sale("2", "事業者2→消費者（税額200）", "事業者2", "GEN", 200)
        if case == "a":
            v.log("3", "残る商品を廃棄", calc="税額の生じる取引はなく変化なし"); c.note("3", "残る商品を廃棄", calc="税額の生じる取引はなく変化なし")
            v.period_end("期1末", "廃業：最終の申告（事業者2は還付申告）"); c.note("期1末", "廃業：届出と還付申請", calc="届出と申請のみで変化なし（還付は期1末+）")
            v.refund("期1末+", "審査後の還付", "事業者2"); c.reviewed("期1末+", "審査付き還付（廃業時）", "事業者2", 200)
        else:
            v.deemed("3", "残る商品を私的に使用（みなし譲渡、税額200）", "事業者2", 200)
            c.sale("3", "残る商品を私的に使用（事業者自身への販売として記録、税額200）", "事業者2", "GEN", 200)
            v.period_end("期1末", "廃業：最終の申告・納付"); c.note("期1末", "廃業：届出（審査で確認、還付なし）", calc="CDは0のため還付なし")
        res[case] = {"VAT": v, "CDAT": c}
    return res

def s6():
    v = VAT(); c = CDAT(); r = CDAT()
    for p in (1, 2, 3):
        for x in (v, c, r): x.sale(f"{p}", f"期{p}：事業者1→事業者2（税額300）", "事業者1", "事業者2", 300)
        r.reviewed(f"{p}+", "審査付き還付（売上に先立つ長期の仕入）", "事業者2", 300)
        v.period_end(f"期{p}末", "申告（事業者2は還付申告）"); c.note(f"期{p}末", "手続なし"); r.note(f"期{p}末", "手続なし")
        v.refund(f"期{p}末+", "審査後の還付", "事業者2")
    for x in (v, c, r): x.sale("4", "期4：事業者2→消費者（税額2,000）", "事業者2", "GEN", 2000)
    v.period_end("期4末", "申告・納付"); c.note("期4末", "手続なし"); r.note("期4末", "手続なし")
    return {"VAT": v, "CDAT（自動還付のみ）": c, "CDAT（審査付き還付を利用）": r}

def s7():
    """真の取引：仕入税額1,000、電子決済の売上600（記録）、現金売上900（未記録）。真の発生税収は1,500。"""
    v = VAT(); c = CDAT()
    for x in (v, c):
        x.sale("1", "仕入：事業者1→事業者2（税額1,000）", "事業者1", "事業者2", 1000)
        x.sale("2", "電子決済の売上：事業者2→消費者（税額600）", "事業者2", "GEN", 600)
    v.log("3", "現金売上（税額900）を申告しない", calc="申告されないため未精算は変化なし"); c.note("3", "現金売上（税額900）を記録しない", calc="台帳に記録されないため変化なし")
    v.period_end("期1末", "申告（記録分のみ、控除は全額→還付申告）"); c.note("期1末", "手続なし")
    v.refund("期1末+", "審査後の還付（審査を通った場合）", "事業者2")
    return {"VAT": v, "CDAT": c}

def s8():
    v = VAT(); c = CDAT()
    v.sale("1", "共通仕入：事業者1→事業者2（税額200、暫定割合0.8）", "事業者1", "事業者2", 200, common_prov=F(8, 10))
    c.sale("1", "共通仕入：事業者1→事業者2（税額200、暫定割合0.8）", "事業者1", "事業者2", 200, e=F(8, 10))
    for x in (v, c): x.sale("2", "課税売上：事業者2→消費者（税額600）", "事業者2", "GEN", 600)
    v.log("3", "非課税売上（税額なし）", calc="非課税のため税額なし"); c.note("3", "非課税売上（税額なし）", calc="非課税のため税額なし")
    v.period_end("期1末", "申告：確定割合0.6で按分し納付", ratio={"事業者2": F(6, 10)})
    c.correct("期1末", "期末調整：確定割合0.6（下方調整Δ=40）", "事業者2", 40, why="（下方調整 (0.8 − 0.6) × 200 = 40）")
    c.repay("期1末+", "返還債務の納付", "事業者2", 40)
    return {"VAT": v, "CDAT": c}

def s8b():
    """上方調整の場合（付録B）：確定割合0.9"""
    v = VAT(); c = CDAT()
    v.sale("1", "共通仕入（税額200、暫定割合0.8）", "事業者1", "事業者2", 200, common_prov=F(8, 10))
    c.sale("1", "共通仕入（税額200、暫定割合0.8）", "事業者1", "事業者2", 200, e=F(8, 10))
    for x in (v, c): x.sale("2", "課税売上（税額600）", "事業者2", "GEN", 600)
    v.period_end("期1末", "申告：確定割合0.9", ratio={"事業者2": F(9, 10)})
    c.upward("期1末", "期末調整：確定割合0.9（上方調整20）", "事業者2", 20, why="（上方調整 (0.9 − 0.8) × 200 = 20）")
    for x in (v, c): x.sale("3", "期2：課税売上（税額600）", "事業者2", "GEN", 600)
    v.period_end("期2末", "申告・納付"); c.note("期2末", "手続なし")
    return {"VAT": v, "CDAT": c}

def s9():
    va = VAT(); ca = CDAT()
    for x in (va, ca):
        x.sale("1", "食品原料（8%）：事業者1→事業者3（税額400）", "事業者1", "事業者3", 400)
        x.sale("2", "包装資材（10%）：事業者2→事業者3（税額100）", "事業者2", "事業者3", 100)
        x.sale("3", "食品（8%）：事業者3→消費者（税額800）", "事業者3", "GEN", 800)
    va.period_end("期1末", "申告・納付"); ca.note("期1末", "手続なし")
    vb = VAT(); cb = CDAT()
    for x in (vb, cb):
        x.sale("1", "標準税率の仕入（10%）：事業者2→事業者3（税額900）", "事業者2", "事業者3", 900)
        x.sale("2", "軽減税率の売上（8%）：事業者3→消費者（税額800）", "事業者3", "GEN", 800)
    vb.period_end("期1末", "申告（事業者3は還付申告）"); cb.note("期1末", "例外的申請", calc="申請のみで変化なし（還付は期1末+）")
    vb.refund("期1末+", "審査後の還付", "事業者3"); cb.reviewed("期1末+", "審査付き還付（例外的申請）", "事業者3", 100)
    return {"a": {"VAT": va, "CDAT": ca}, "b": {"VAT": vb, "CDAT": cb}}

def sF():
    """付録B.3.6：共謀によるCDの移転。事業者1は売上のない事業者で、私的な消費のための購入（税額1,000）を事業取引として記録する。
    事業者1は事業者2へ架空の販売（税額1,000）を記録し、事業者2は消費者へ販売する（税額1,500）。真の発生税収は2,500。"""
    v = VAT(); c = CDAT()
    for x in (v, c):
        x.sale("1", "事業者3→事業者1（私的な消費のための購入を事業仕入とする、税額1,000）", "事業者3", "事業者1", 1000)
        x.sale("2", "事業者1→事業者2（架空の販売、税額1,000）", "事業者1", "事業者2", 1000)
        x.sale("3", "事業者2→消費者（税額1,500）", "事業者2", "GEN", 1500)
    v.period_end("期1末", "申告・納付"); c.note("期1末", "手続なし")
    return {"VAT": v, "CDAT": c}

def all_scenarios():
    out = {}
    out["16.1"] = s1(); out["16.2"] = s2(); out["16.3"] = s3(); out["B.3"] = s3b(); out["16.4"] = s4()
    r5 = s5(); out["16.5a"] = r5["a"]; out["16.5b"] = r5["b"]
    out["16.6"] = s6(); out["16.7"] = s7(); out["16.8"] = s8(); out["B.8"] = s8b()
    r9 = s9(); out["16.9a"] = r9["a"]; out["16.9b"] = r9["b"]
    out["B.3.6"] = sF()
    return out

if __name__ == "__main__":
    allsc = all_scenarios()
    for key, d in allsc.items():
        finals = {}
        for name, sys in d.items():
            print(table_text(f"[{key}] {name}", sys.rows)); print()
            finals[name] = sys.rows[-1][4]
        print(f"  → 最終の発生税収: {finals}"); print("=" * 60)
