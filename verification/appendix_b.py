"""付録B.3の回帰テストの表を計算する。"""
from fractions import Fraction as F
from scenarios import fmt, fflow

def sfmt(v):
    v = F(v)
    if v == 0: return "0"
    return ("+" if v > 0 else "−") + fmt(abs(v))

def T(title, head, rows):
    out = [title, "\t".join(head)]
    for r in rows: out.append("\t".join(str(x) for x in r))
    return "\n".join(out)

# ---------- B.3.1 旧版の定義との比較：仕入100 → 販売200 の反復 ----------
def b31():
    rows = []
    old = F(0); new = F(0); rold = F(0); rnew = F(0)
    for n in (1, 2, 3):
        # 仕入（適格仕入税額100）
        old -= 100; new += 100
        rows.append((f"{n}-仕入", "仕入（税額100）", "—", sfmt(old), "—", fmt(new)))
        # 販売（税額200）
        b_old = min(F(200), max(F(0), -old)); old += 200; rold += b_old
        b_new = min(F(200), new); new -= b_new; rnew += b_new
        rows.append((f"{n}-販売", "販売（税額200）", fmt(b_old), sfmt(old), fmt(b_new), fmt(new)))
    tbl = T("表B.3.1 仕入100 → 販売200 の反復（旧版の定義と本稿の定義）",
            ["時点", "事象", "旧版の還付額", "旧版の累積差額", "本稿のβ", "本稿のCD"], rows)
    # 国庫の正味（仕入先の納付300を含む）。最終消費者の税額は600
    treas_old = 300 + 600 - rold; treas_new = 300 + 600 - rnew
    return tbl, rold, rnew, treas_old, treas_new

# ---------- B.3.2 順序の入替え ----------
def b32():
    rows = []
    # (a) 仕入→販売
    cd = F(0); cash = F(0)
    cash += 100; cd += 100                 # 仕入：仕入先の販売（仕入先のCDは0）
    b = min(F(200), cd); cd -= b; cash += 200 - b
    rows.append(("仕入 → 販売", fmt(b), fmt(cd), fmt(cash), "200", "200（期末に一括）"))
    cd = F(0); cash = F(0)
    b = min(F(200), cd); cd -= b; cash += 200 - b    # 販売（CDは0）
    cash += 100; cd += 100                 # 仕入
    rows.append(("販売 → 仕入", fmt(b), fmt(cd), fmt(cash), "200", "200（期末に一括）"))
    return T("表B.3.2 取引順序の入替え（事業者2：仕入税額100、消費者への販売の税額200、同じ課税期間）",
             ["順序", "販売時のβ", "期末のCD", "CDATの国庫の受領累計", "発生税収", "現行VATの国庫の受領累計"], rows)

# ---------- B.3.3 遅れて記録した販売 ----------
def seq_run(seq, rule=None):
    """seq: ('P', p) | ('S', t, late)。rule=None は全取引を取引時に記録。
    rule='b0'：遅れた販売は β=0（12.3節）。'now'：記録時点のCD。'then'：取引時点と記録時点のCDの小さい方。"""
    CD = F(0); refunded = F(0); paid = F(0); hist = []; pend = []
    for i, ev in enumerate(seq):
        hist.append(CD)
        if ev[0] == 'P': CD += ev[1]
        else:
            t, late = F(ev[1]), ev[2]
            if late and rule is not None: pend.append((i, t)); continue
            b = min(t, CD); CD -= b; refunded += b; paid += t - b
    for i, t in pend:
        if rule == 'b0': b = F(0)
        elif rule == 'now': b = min(t, CD)
        else: b = min(t, hist[i], CD)
        CD -= b; refunded += b; paid += t - b
    return CD, refunded, paid

def b33():
    ex1 = [('S', 100, True), ('P', 100)]
    ex2 = [('P', 100), ('S', 100, True), ('S', 100, False), ('P', 100)]
    rows = []
    for name, seq in (("例1：未記録の販売100 → 仕入100 → 期末に申告", ex1),
                      ("例2：仕入100 → 未記録の販売100 → 記録された販売100 → 仕入100 → 期末に申告", ex2)):
        for rname, rule in (("取引時に記録した場合", None), ("β=0（12.3節）", 'b0'),
                            ("記録時点のCD（採らない）", 'now'), ("取引時点と記録時点のCDの小さい方（採らない）", 'then')):
            cd, r, p = seq_run(seq, rule)
            rows.append((name if rule is None else "", rname, fmt(r), fmt(p), fmt(cd)))
    return T("表B.3.3 取引時に記録されなかった販売の自動還付の規則",
             ["取引列", "規則", "自動還付の累計", "納付の累計", "期末のCD"], rows)

# ---------- B.3.4 保留中に確認された輸出 ----------
def hold_run(CD0, IT0, seq, rule):
    """保留期間中の事象列。rule: 'timely'（確認時に処理）、'now'（確認終了時のCD）、'pk'（9節：p_kを除く）
    確認終了時は事後訂正を先に行い、その後で保留中の輸出を確認の順に処理する。"""
    CD, IT, R, Debt = F(CD0), F(IT0), F(0), F(0)
    held = []; corr = []
    for ev in seq:
        if ev[0] == 'P':
            CD += ev[1]; IT += ev[1]
            for h in held: h[1] += ev[1]
        elif ev[0] == 'C':
            corr.append(F(ev[1]))
        else:
            if rule == 'timely':
                x = min(F(ev[1]), CD); CD -= x; R += x
            else:
                held.append([F(ev[1]), F(0)])
    for D in corr:                          # 確認終了時：事後訂正を先に行う
        D = min(D, IT); IT -= D; c = min(D, CD); CD -= c; Debt += D - c
    xs = []
    for tv, p in held:
        x = min(tv, CD) if rule == 'now' else max(F(0), min(tv, CD - p))
        CD -= x; R += x; xs.append(x)
    return R, CD, Debt, xs

def b34():
    cases = [
        ("(i) 輸出の確認 → 仕入 → 確認終了", 50, 50, [('X', 100), ('P', 100)]),
        ("(ii) 輸出1 → 仕入 → 輸出2 → 仕入 → 確認終了", 50, 50, [('X', 100), ('P', 100), ('X', 100), ('P', 100)]),
        ("(iii) 輸出の確認 → 仕入 → 事後訂正 → 確認終了", 100, 100, [('X', 100), ('P', 100), ('C', 80)]),
        ("(iv) 輸出の確認 → 事後訂正 → 確認終了", 100, 100, [('X', 100), ('C', 80)]),
    ]
    rows = []
    for name, cd0, it0, seq in cases:
        for rname, rule in (("確認時に処理した場合", 'timely'), ("9節の規則（p_kを除く）", 'pk'), ("確認終了時のCDをそのまま上限（採らない）", 'now')):
            R, CD, Debt, xs = hold_run(cd0, it0, seq, rule)
            rows.append((name if rule == 'timely' else "", fmt(cd0) if rule == 'timely' else "", rname, fmt(R), fmt(CD), fmt(Debt)))
    return T("表B.3.4 還付保留中に確認された輸出（仮想税額はいずれも100、仕入の適格仕入税額は100、事後訂正はΔ=80）",
             ["事象列", "保留開始時のCD", "規則", "輸出還付の累計", "確認終了後のCD", "返還債務"], rows)

# ---------- B.3.5 Tax_prov と移管 ----------
def b35():
    rows = []
    Bal_net = F(1000); TP = F(0); prov = F(40); M = F(0); u = F(20)
    for name, use_prov in (("Tax_provを除かない場合", False), ("Tax_provを除く場合（6.5節）", True)):
        y = Bal_net - TP - (prov if use_prov else 0) - M
        after = Bal_net - y
        after_adj = after - u
        rows.append((name, fmt(y), fmt(after), sfmt(after_adj) if after_adj < 0 else fmt(after_adj), "成り立たない" if after_adj - TP < 0 else "成り立つ"))
    return T("表B.3.5 共通仕入の暫定割合と移管（移管前のBal_net = 1,000、Tax_pending = 0、Tax_prov = 40、M = 0、期末の上方調整20）",
             ["移管の判定", "移管額y", "移管後のBal_net", "上方調整後のBal_net", "Bal_net − Tax_pending ≥ 0"], rows)

# ---------- B.3.6 共謀によるCDの移転：集合Gについての命題3の各項 ----------
def b36g():
    """G = {事業者1、事業者2}。scenarios.sF と同じ取引列を、集合Gについての量を追って再計算し、
    CDの合計を scenarios の CDAT の行と照合する。"""
    import scenarios as S
    G = {"事業者1", "事業者2"}
    ev = [("1", "事業者3→事業者1（私的な消費のための購入を事業仕入とする、税額1,000）", "事業者3", "事業者1", F(1000)),
          ("2", "事業者1→事業者2（架空の販売、税額1,000）", "事業者1", "事業者2", F(1000)),
          ("3", "事業者2→消費者（税額1,500）", "事業者2", "GEN", F(1500))]
    CD = {}; BX = PI = RX = F(0); rows = []
    ref = S.sF()["CDAT"].rows
    for k, (t, name, i, j, tax) in enumerate(ev):
        beta = min(tax, CD.get(i, F(0))); CD[i] = CD.get(i, F(0)) - beta
        if j != "GEN": CD[j] = CD.get(j, F(0)) + tax          # 適格割合1
        if i in G and j in G: PI += tax - beta                  # Gの内部の取引：納付額
        elif j in G: BX += tax                                  # Gの外部からの購入
        if i in G and j not in G: RX += beta                    # Gの外部への販売に対する自動還付
        CDG = sum((CD.get(g, F(0)) for g in G), F(0))
        assert ref[k][0] == t and ref[k][6] == sum(CD.values(), F(0))   # CD_tot を scenarios と照合
        assert RX + CDG <= BX + PI and RX + CDG == BX + PI               # 命題3（等号の条件を満たす）
        rows.append((t, name, fmt(CDG), fmt(BX), fmt(PI), fmt(RX), fmt(RX + CDG), fmt(BX + PI)))
    return T("表B.3.6(c) G = {事業者1、事業者2}についての命題3の各項（CDAT）",
             ["時点", "事象", "CD_G", "BX_G", "PI_G", "RX_G", "RX_G + CD_G", "BX_G + PI_G"], rows)

if __name__ == "__main__":
    t, ro, rn, to, tn = b31(); print(t); print(f"還付累計 旧{ro} 新{rn}、国庫 旧{to} 新{tn}"); print()
    print(b32()); print(); print(b33()); print(); print(b34()); print(); print(b35()); print(); print(b36g())
