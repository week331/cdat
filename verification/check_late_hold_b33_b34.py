"""付録B.3.3（取引時に記録されなかった販売）と付録B.3.4（還付保留中に確認された輸出）の無作為な検査。
(1) B.3.3：20万通りの取引列（各2〜12事象。仕入と販売、販売の一部は取引時に記録されず期末に申告）について、
    遅れて記録した販売の自動還付の規則ごとに、取引時に記録した場合より有利／不利になった数を数える。
    有利＝期末のCDが小さい（同じ額だけ納付が少ない）。納付の累計 − CD は規則によらず一定であることを assert で確認する。
    さらに、β_k = 0 の規則（12.3節）で増える納付額が、遅れた販売が取引時に記録されていれば受けた自動還付の額を
    超えないことを assert で確認する。
    規則1：記録時点のCD（採らない）　規則2：β_k = 0（12.3節）　規則3：取引時点と記録時点のCDの小さい方（採らない）
(2) B.3.4：20万通りの保留期間（保留中は自動還付・輸出還付・審査付き還付なし。仕入と事後訂正はあり）について、
    保留中に確認された輸出を確認終了後に処理する規則を、輸出を確認時に処理した場合と比べる。
    確認終了時のCDをそのまま上限とする規則（採らない）と、9節の規則 x = max(0, min(t_virt, CD − p_k)) を比べる。
    確認終了時は、事後訂正を先に行い、その後で輸出を確認の順に処理する。
    (2)では、保留中の事後訂正を、それが生じた時点で行う。
(3) B.3.4の変形：(2)と同じ保留期間（同じ乱数列）で、保留中の事後訂正を確認終了時にまとめて行い、その後で輸出を処理する
    （付録B.3.4の表と同じ扱い）。確認時に処理する場合も、事後訂正は確認終了時に行う。
乱数の種は (1) 20261003、(2) と (3) 9 に固定。
使い方：python3 check_late_hold_b33_b34.py"""
import random

# ---------- (1) 遅れて記録した販売 ----------
def run_sales(seq, late_rule=None):
    CD = 0; refunded = 0; paid = 0; hist = []; pending = []; late_b_timely = 0
    for idx, ev in enumerate(seq):
        hist.append(CD)
        if ev[0] == 'P': CD += ev[1]
        else:
            t, late = ev[1], ev[2]
            if late and late_rule is not None: pending.append((idx, t)); continue
            b = min(t, CD); CD -= b; refunded += b; paid += t - b
            if late: late_b_timely += b          # 取引時に記録した場合に、遅れる販売が受ける自動還付
    for idx, t in pending:
        if late_rule == 1: b = min(t, CD)
        elif late_rule == 2: b = 0
        else: b = min(t, hist[idx], CD)
        CD -= b; refunded += b; paid += t - b
    return CD, refunded, paid, late_b_timely

rng = random.Random(20261003)
N = 200000
adv = {1: 0, 2: 0, 3: 0}; dis = {1: 0, 2: 0, 3: 0}
for _ in range(N):
    seq = []
    for _ in range(rng.randint(2, 12)):
        if rng.random() < 0.45: seq.append(('P', rng.randint(1, 100)))
        else: seq.append(('S', rng.randint(1, 100), rng.random() < 0.4))
    cd0, r0, p0, lb0 = run_sales(seq)
    for rule in (1, 2, 3):
        cd, r, p, _ = run_sales(seq, rule)
        assert p - cd == p0 - cd0                 # 納付の増減は CD の増減と同額（総額は不変）
        if rule == 2: assert p - p0 <= lb0        # β=0 で増える納付額は、取引時に記録していれば受けた自動還付を超えない
        if cd < cd0: adv[rule] += 1
        if cd > cd0: dis[rule] += 1
print(f"(1) B.3.3：{N}通りの取引列で、遅れて記録した方が 有利 / 不利 になった数")
for rule, name in ((1, '記録時点のCD（採らない）'), (2, 'β_k = 0（12.3節）'), (3, '取引時点と記録時点のCDの小さい方（採らない）')):
    print(f"   規則{rule} {name}：有利 {adv[rule]} / 不利 {dis[rule]}")

# ---------- (2) 保留中に確認された輸出 ----------
def run_hold(CD0, IT0, seq, rule):
    CD, IT, R, Debt = CD0, IT0, 0, 0
    held = []                                       # (t_virt, 確認後の仕入を数えるためのリスト)
    for ev in seq:
        if ev[0] == 'P':
            CD += ev[1]; IT += ev[1]
            for h in held: h[1] += ev[1]            # 確認後に算入された適格仕入税額
        elif ev[0] == 'C':
            D = min(ev[1], IT); IT -= D; c = min(D, CD); CD -= c; Debt += D - c
        else:                                       # 'X'：輸出の確認
            if rule == 'timely':
                x = min(ev[1], CD); CD -= x; R += x
            else:
                held.append([ev[1], 0])
    for tv, p_after in held:                        # 確認終了：確認の順に処理
        if rule == 'end': x = min(tv, CD)
        else: x = max(0, min(tv, CD - p_after))
        CD -= x; R += x
    assert CD >= 0 and CD - Debt == CD0 + (IT - IT0) - R
    return CD, R, Debt

rng = random.Random(9)
M = 200000
hadv = {'end': 0, 'rule9': 0}; hdis = {'end': 0, 'rule9': 0}; neq_nocorr = 0; n_nocorr = 0
for _ in range(M):
    CD0 = rng.randint(0, 100); IT0 = CD0 + rng.randint(0, 100)
    seq = []
    for _ in range(rng.randint(1, 10)):
        u = rng.random()
        if u < 0.4: seq.append(('P', rng.randint(1, 100)))
        elif u < 0.8: seq.append(('X', rng.randint(1, 100)))
        else: seq.append(('C', rng.randint(1, 60)))
    cdT, _, _ = run_hold(CD0, IT0, seq, 'timely')
    has_corr = any(e[0] == 'C' for e in seq)
    for rule in ('end', 'rule9'):
        cd, _, _ = run_hold(CD0, IT0, seq, rule)
        if cd < cdT: hadv[rule] += 1
        if cd > cdT: hdis[rule] += 1
        if rule == 'rule9' and not has_corr:
            n_nocorr += 1
            if cd != cdT: neq_nocorr += 1
print(f"(2) B.3.4：{M}通りの保留期間で、確認時に処理した場合より 有利 / 不利 になった数")
print(f"   確認終了時のCDをそのまま上限（採らない）：有利 {hadv['end']} / 不利 {hdis['end']}")
print(f"   9節の規則（確認後の仕入p_kを除く）：有利 {hadv['rule9']} / 不利 {hdis['rule9']}（事後訂正のない{n_nocorr}通りで、確認時に処理した場合と一致しなかった数：{neq_nocorr}）")
print("   例 [CD50で輸出100の確認 → 仕入100]（CD, 輸出還付の累計, 返還債務）：", {r: run_hold(50, 50, [('X', 100), ('P', 100)], r) for r in ('timely', 'end', 'rule9')})
print("   例 [CD100で輸出100 → 輸出100 → 仕入100]（CD, 輸出還付の累計, 返還債務）：", {r: run_hold(100, 100, [('X', 100), ('X', 100), ('P', 100)], r) for r in ('timely', 'end', 'rule9')})
print("   （timely：確認時に処理、end：確認終了時のCDをそのまま上限、rule9：9節の規則）")
print("(1)の規則2で増える納付額は、すべての取引列で、取引時に記録していれば受けた自動還付の額を超えなかった。")

# ---------- (3) 事後訂正を確認終了時にまとめて行う場合 ----------
def run_hold_deferred(CD0, IT0, seq, rule):
    CD, IT, R, Debt = CD0, IT0, 0, 0
    held = []; corr = []
    for ev in seq:
        if ev[0] == 'P':
            CD += ev[1]; IT += ev[1]
            for h in held: h[1] += ev[1]
        elif ev[0] == 'C':
            corr.append(ev[1])
        else:
            if rule == 'timely':
                x = min(ev[1], CD); CD -= x; R += x
            else:
                held.append([ev[1], 0])
    for D in corr:                                  # 確認終了時：事後訂正を先に行う
        D = min(D, IT); IT -= D; c = min(D, CD); CD -= c; Debt += D - c
    for tv, p_after in held:
        x = min(tv, CD) if rule == 'end' else max(0, min(tv, CD - p_after))
        CD -= x; R += x
    assert CD >= 0 and CD - Debt == CD0 + (IT - IT0) - R
    return CD, R, Debt

rng = random.Random(9)
dadv = {'end': 0, 'rule9': 0}; ddis = {'end': 0, 'rule9': 0}; dneq = 0; dn0 = 0
for _ in range(M):
    CD0 = rng.randint(0, 100); IT0 = CD0 + rng.randint(0, 100)
    seq = []
    for _ in range(rng.randint(1, 10)):
        u = rng.random()
        if u < 0.4: seq.append(('P', rng.randint(1, 100)))
        elif u < 0.8: seq.append(('X', rng.randint(1, 100)))
        else: seq.append(('C', rng.randint(1, 60)))
    cdT, _, _ = run_hold_deferred(CD0, IT0, seq, 'timely')
    has_corr = any(e[0] == 'C' for e in seq)
    for rule in ('end', 'rule9'):
        cd, _, _ = run_hold_deferred(CD0, IT0, seq, rule)
        if cd < cdT: dadv[rule] += 1
        if cd > cdT: ddis[rule] += 1
        if rule == 'rule9' and not has_corr:
            dn0 += 1
            if cd != cdT: dneq += 1
print(f"(3) B.3.4の変形（事後訂正を確認終了時にまとめて行う）：{M}通りの保留期間で、確認時に処理した場合より 有利 / 不利 になった数")
print(f"   確認終了時のCDをそのまま上限（採らない）：有利 {dadv['end']} / 不利 {ddis['end']}")
print(f"   9節の規則（確認後の仕入p_kを除く）：有利 {dadv['rule9']} / 不利 {ddis['rule9']}（事後訂正のない{dn0}通りで、確認時に処理した場合と一致しなかった数：{dneq}）")
