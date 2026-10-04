"""付録B.4「無作為な取引列による検査」の全体の検査。
・事業者6者（課税売上だけの事業者、共通仕入を持つ事業者、非課税売上だけの事業者をランダムに割り当てる）について、
  200事象からなる取引列を3,000本生成し、各事象の後に、論文の5節、6節、7節、10節の恒等式と不変条件、
  および命題3の事業者ごとの不等式を検査する（計600,000時点）。
・事象：事業取引と一般取引の販売（電子決済と、未決済税額を生じる現金決済）、取引時に記録されない販売とその申告（β_k = 0、12.3節）、
  輸入、輸出の確認と輸出還付、還付保留とその解除（保留中に確認された輸出は9節の規則）、審査付き還付、未決済税額の納付、
  事後訂正、返還納付、共通仕入の期末調整（2.5節）、区分間の振替および一般財源等への移管（6.5節）。
・計算はすべて fractions.Fraction による有理数の正確な演算。乱数の種は 20261004 に固定。
・検査が一つでも成り立たなければ AssertionError で止まる。最後まで進めば、検査した時点の数などを出力する。
使い方：python3 check_random_b4.py（数分かかる）"""
import random
from fractions import Fraction as F

class Biz:
    def __init__(s, kind):
        s.CD = s.IT = s.Ra = s.Rx = s.Rr = s.Debt = s.Repay = s.TP = F(0); s.hold = False
        s.kind = kind
        s.BT = F(0); s.corrected = False
        s.e_prov = F(1, 2); s.common_period = F(0)
        s.held_exports = []          # [t_virt, 確認後に算入された適格仕入税額]
        s.unrecorded = []            # 取引時に記録されなかった販売 (buyer, t)
    def add_elig(s, te):
        s.CD += te; s.IT += te
        for h in s.held_exports: h[1] += te

class T:
    def __init__(s, L, M):
        s.b = {}; s.buf = s.hold = F(0); s.L, s.M = F(L), F(M)
        s.TaxRec = s.TaxC = s.TaxNE = s.TR = F(0)
    def TP(s): return sum((x.TP for x in s.b.values()), F(0))
    def Tax_prov(s): return sum(((1 - x.e_prov) * x.common_period for x in s.b.values() if x.kind == 'mixed'), F(0))
    def cash_buf(s): return s.buf - s.TP()
    def pay(s, q):
        short = q - s.cash_buf()
        if short > 0: m = min(short, s.hold); s.hold -= m; s.buf += m
        assert s.cash_buf() >= q, "還付バッファの受領済み資金が不足"
        s.buf -= q
    def replenish(s):
        if s.cash_buf() < s.L: m = min(s.L - s.cash_buf(), s.hold); s.hold -= m; s.buf += m
    def move(s):
        ex = s.cash_buf() - s.L
        if ex > 0: s.buf -= ex; s.hold += ex
    def purchase_elig(s, j, t):
        y = s.b[j]
        if y.kind == 'tax': return t
        if y.kind == 'exempt': return F(0)
        y.common_period += t; return y.e_prov * t
    def buyer_side(s, buyer, t):
        if buyer == "GEN": s.TaxC += t
        else:
            te = s.purchase_elig(buyer, t); s.b[buyer].add_elig(te); s.TaxNE += t - te
            s.b[buyer].BT += t
    def sale(s, i, buyer, t, deferred_cash=False, beta_zero=False):
        x = s.b[i]; beta = F(0) if (x.hold or beta_zero) else min(t, x.CD)
        x.CD -= beta; x.Ra += beta; s.TaxRec += t; s.buf += t - beta
        if deferred_cash: x.TP += t - beta
        s.buyer_side(buyer, t)
        s.replenish()
    def unrecorded_sale(s, i, buyer, t): s.b[i].unrecorded.append((buyer, t))   # 台帳には何も起きない
    def declare(s, i):                                 # 12.3 の申告：β = 0
        x = s.b[i]
        for buyer, t in x.unrecorded:
            if buyer == "GEN": s.sale(i, "GEN", t, deferred_cash=True, beta_zero=True)
            else: s.sale(i, buyer, t, beta_zero=True)   # 事業取引：申告時に納付し、同時に買い手の CD に反映
        x.unrecorded = []
    def imp(s, importer, t):
        s.TaxRec += t; s.buf += t; s.buyer_side(importer, t); s.replenish()
    def refund_with_offset(s, x, amount, kind):
        off = min(amount, x.TP)
        x.CD -= amount
        if kind == 'x': x.Rx += amount
        else: x.Rr += amount
        x.TP -= off; s.buf -= off
        if amount - off > 0: s.pay(amount - off)
        s.replenish()
    def export_confirm(s, i, t_virt):
        x = s.b[i]
        if x.hold: x.held_exports.append([t_virt, F(0)]); return
        q = min(t_virt, x.CD)
        if q > 0: s.refund_with_offset(x, q, 'x')
    def release_hold(s, i):
        x = s.b[i]; x.hold = False
        for tv, p_after in x.held_exports:
            q = max(F(0), min(tv, x.CD - p_after))
            if q > 0: s.refund_with_offset(x, q, 'x')
        x.held_exports = []
    def reviewed(s, i):
        x = s.b[i]
        if x.hold or x.CD == 0: return
        a = F(random.randint(1, int(x.CD) if x.CD >= 1 else 1)); a = min(a, x.CD)
        s.refund_with_offset(x, a, 'r')
    def correct(s, i, D):
        x = s.b[i]; D = min(F(D), x.IT); x.corrected = x.corrected or D > 0; x.IT -= D; s.TaxNE += D; c = min(D, x.CD); x.CD -= c; x.Debt += D - c
    def period_end(s):
        for n, x in s.b.items():
            s.declare(n)                                       # 期末の申告
            if x.kind != 'mixed' or x.common_period == 0: continue
            e_fin = F(random.randint(0, 10), 10)
            delta = (e_fin - x.e_prov) * x.common_period
            if delta > 0: x.add_elig(delta); s.TaxNE -= delta  # 上方調整
            elif delta < 0: s.correct(n, -delta)               # 下方調整 = 10節の事後訂正（Tax_ne に加える）
            x.common_period = F(0); x.e_prov = e_fin if e_fin > 0 else F(1, 2)
    def pay_pending(s, i, v):
        x = s.b[i]; v = min(F(v), x.TP); x.TP -= v
    def repay(s, i, v):
        x = s.b[i]; v = min(F(v), x.Debt); x.Debt -= v; x.Repay += v; s.buf += v
    def transfer(s, want):
        CDtot = sum((x.CD for x in s.b.values()), F(0)); net = s.buf + s.hold - CDtot
        y = max(F(0), min(F(want), s.hold, net - s.TP() - s.Tax_prov() - s.M)); s.hold -= y; s.TR += y

random.seed(20261004)
n_checks = 0; n_late = 0; n_held = 0; n_prop3 = 0
for run in range(3000):
    w = T(L=random.randint(0, 80), M=random.randint(0, 50))
    names = [f"N{k}" for k in range(6)]
    for n in names: w.b[n] = Biz(random.choice(['tax', 'tax', 'mixed', 'exempt']))
    for step in range(200):
        if step % 50 == 49: w.period_end()
        u = random.random(); t = F(random.randint(1, 60))
        if u < 0.20: i, j = random.sample(names, 2); w.sale(i, j, t)
        elif u < 0.27: w.sale(random.choice(names), "GEN", t)
        elif u < 0.34: w.sale(random.choice(names), "GEN", t, deferred_cash=True)
        elif u < 0.39:
            i = random.choice(names); buyer = random.choice(["GEN", "GEN", random.choice([n for n in names if n != i])])
            w.unrecorded_sale(i, buyer, t); n_late += 1
        elif u < 0.41: w.declare(random.choice(names))          # 非常時の申告
        elif u < 0.45: w.imp(random.choice(names), t)
        elif u < 0.47: w.imp("GEN", t)
        elif u < 0.52:
            n = random.choice(names); n_held += w.b[n].hold; w.export_confirm(n, t)
        elif u < 0.55: w.reviewed(random.choice(names))
        elif u < 0.60: w.pay_pending(random.choice(names), random.randint(1, 60))
        elif u < 0.64:
            n = random.choice(names); x = w.b[n]
            if x.hold: w.release_hold(n)
            else: x.hold = True
        elif u < 0.67: w.correct(random.choice(names), random.randint(1, 40))
        elif u < 0.70: w.repay(random.choice(names), random.randint(1, 40))
        elif u < 0.85: w.move()
        else: w.transfer(random.randint(1, 200))
        B = list(w.b.values())
        CDtot = sum((x.CD for x in B), F(0)); IT = sum((x.IT for x in B), F(0))
        Ra = sum((x.Ra for x in B), F(0)); Rx = sum((x.Rx for x in B), F(0)); Rr = sum((x.Rr for x in B), F(0))
        Debt = sum((x.Debt for x in B), F(0)); Rep = sum((x.Repay for x in B), F(0)); TP = w.TP(); Pv = w.Tax_prov()
        BalT = w.buf + w.hold; net = BalT - CDtot; TaxNC = w.TaxRec - IT
        for x in B: assert x.CD >= 0 and x.CD - x.Debt == x.IT - x.Ra - x.Rx - x.Rr + x.Repay
        assert BalT == w.TaxRec - Ra - Rx - Rr + Rep - w.TR
        assert net == TaxNC - Debt - w.TR
        assert TaxNC == w.TaxC + w.TaxNE                       # 7節、10節
        assert 0 <= Pv <= w.TaxNE
        assert net >= 0 and net - TP >= 0 and net - TP - Pv >= 0, (net, TP, Pv)
        for x in B:
            R = x.Ra + x.Rx + x.Rr
            assert x.CD + R <= x.BT, ("命題3", x.kind, x.CD, R, x.BT)
            if x.kind == 'tax' and not x.corrected: assert x.CD + R == x.BT
            n_prop3 += 1
        n_checks += 1
print(f"{n_checks}時点（取引時に記録されない販売 {n_late} 件、保留中の輸出の確認 {n_held} 件を含む）で、次がすべて成り立った：")
print("  CD_i − Debt_i = IT_i − R_auto,i − R_exp,i − R_rev,i + Repay_i、Bal_T = Tax_rec − R_auto − R_exp − R_rev + Repay_tot − TR、")
print("  Bal_net = Tax_nc − Debt_tot − TR、Tax_nc = Tax_C + Tax_ne、0 ≤ Tax_prov ≤ Tax_ne、")
print("  Bal_net ≥ 0、Bal_net − Tax_pending ≥ 0、Bal_net − Tax_pending − Tax_prov ≥ 0。還付はすべて受領済みの資金から支払うことができた")

print(f"命題3：事業者ごとに CD_i + R_auto,i + R_exp,i + R_rev,i ≤ BT_i を {n_prop3} 回検査（適格割合1・事後訂正なしの事業者では等号）")
