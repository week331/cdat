"""論文の16節と付録Bの表を、本文と同じ順に出力し、付録B.1の計算式の左辺と右辺が一致することを確かめる。
使い方：python3 print_tables.py"""
import scenarios as S
import appendix_b as B
import tables_lib as L

SPECS = [
    ('TABLE', '16.1', 'VAT', '表16.1(a) 現行VAT'),
    ('TABLE', '16.1', 'CDAT', '表16.1(b) CDAT'),
    ('TABLE', '16.2', 'VAT', '表16.2(a) 現行VAT'),
    ('TABLE', '16.2', 'CDAT（自動還付のみ）', '表16.2(b) CDAT（自動還付のみ）'),
    ('TABLE', '16.2', 'CDAT（審査付き還付を利用）', '表16.2(c) CDAT（審査付き還付を利用）'),
    ('TABLE', '16.3', 'VAT', '表16.3(a) 現行VAT'),
    ('TABLE', '16.3', 'CDAT', '表16.3(b) CDAT'),
    ('TABLE', '16.4', 'VAT', '表16.4(a) 現行VAT'),
    ('TABLE', '16.4', 'CDAT', '表16.4(b) CDAT'),
    ('TABLE', '16.5a', 'VAT', '表16.5(a) 現行VAT（残る商品を廃棄する場合）'),
    ('TABLE', '16.5a', 'CDAT', '表16.5(b) CDAT（残る商品を廃棄する場合）'),
    ('TABLE', '16.5b', 'VAT', '表16.5(c) 現行VAT（残る商品を私的に使用する場合）'),
    ('TABLE', '16.5b', 'CDAT', '表16.5(d) CDAT（残る商品を私的に使用する場合）'),
    ('TABLE', '16.6', 'VAT', '表16.6(a) 現行VAT'),
    ('TABLE', '16.6', 'CDAT（自動還付のみ）', '表16.6(b) CDAT（自動還付のみ）'),
    ('TABLE', '16.6', 'CDAT（審査付き還付を利用）', '表16.6(c) CDAT（審査付き還付を利用）'),
    ('TABLE', '16.7', 'VAT', '表16.7(a) 現行VAT（控除不足額の還付が審査を通った場合）'),
    ('TABLE', '16.7', 'CDAT', '表16.7(b) CDAT'),
    ('TABLE', '16.8', 'VAT', '表16.8(a) 現行VAT'),
    ('TABLE', '16.8', 'CDAT', '表16.8(b) CDAT'),
    ('TABLE', '16.9a', 'VAT', '表16.9(a) 現行VAT（軽減税率の販売）'),
    ('TABLE', '16.9a', 'CDAT', '表16.9(b) CDAT（軽減税率の販売）'),
    ('TABLE', '16.9b', 'VAT', '表16.9(c) 現行VAT（構造的な超過）'),
    ('TABLE', '16.9b', 'CDAT', '表16.9(d) CDAT（構造的な超過）'),
    ('SUMMARY',),
    ('DETAIL', '16.1', 'VAT', 'CDAT', '表B.1.1 16.1節（通常の多段階取引）の内訳'),
    ('DETAIL', '16.2', 'VAT', 'CDAT（自動還付のみ）', '表B.1.2 16.2節（設備投資、CDATは自動還付のみ）の内訳'),
    ('DETAIL', '16.2', 'VAT', 'CDAT（審査付き還付を利用）', '表B.1.3 16.2節（設備投資、CDATは審査付き還付を利用）の内訳'),
    ('DETAIL', '16.3', 'VAT', 'CDAT', '表B.1.4 16.3節（輸出）の内訳'),
    ('DETAIL', '16.4', 'VAT', 'CDAT', '表B.1.5 16.4節（輸入）の内訳'),
    ('DETAIL', '16.5a', 'VAT', 'CDAT', '表B.1.6 16.5節（事業退出、残る商品を廃棄）の内訳'),
    ('DETAIL', '16.5b', 'VAT', 'CDAT', '表B.1.7 16.5節（事業退出、残る商品を私的に使用）の内訳'),
    ('DETAIL', '16.6', 'VAT', 'CDAT（自動還付のみ）', '表B.1.8 16.6節（長期間売上のない事業者、CDATは自動還付のみ）の内訳'),
    ('DETAIL', '16.6', 'VAT', 'CDAT（審査付き還付を利用）', '表B.1.9 16.6節（長期間売上のない事業者、CDATは審査付き還付を利用）の内訳'),
    ('DETAIL', '16.7', 'VAT', 'CDAT', '表B.1.10 16.7節（現金売上が記録されない場合）の内訳'),
    ('DETAIL', '16.8', 'VAT', 'CDAT', '表B.1.11 16.8節（共通仕入）の内訳'),
    ('DETAIL', '16.9a', 'VAT', 'CDAT', '表B.1.12 16.9節（軽減税率の販売）の内訳'),
    ('DETAIL', '16.9b', 'VAT', 'CDAT', '表B.1.13 16.9節（構造的な超過）の内訳'),
    ('TABLE', 'B.3', 'VAT', '表B.2.1(a) 現行VAT'),
    ('TABLE', 'B.3', 'CDAT', '表B.2.1(b) CDAT'),
    ('TABLE', 'B.8', 'VAT', '表B.2.2(a) 現行VAT'),
    ('TABLE', 'B.8', 'CDAT', '表B.2.2(b) CDAT'),
    ('B31',),
    ('B32',),
    ('B33',),
    ('B34',),
    ('B35',),
    ('TABLE', 'B.3.6', 'VAT', '表B.3.6(a) 現行VAT'),
    ('TABLE', 'B.3.6', 'CDAT', '表B.3.6(b) CDAT'),
    ('B36G',),
]

def main():
    n = L.check_all_calcs()
    out = []
    for spec in SPECS:
        kind = spec[0]
        if kind == "TABLE":
            out.append(L.table(spec[1], spec[2], spec[3]))
        elif kind == "DETAIL":
            out.append(L.detail(spec[1], spec[2], spec[3], spec[4]))
        elif kind == "SUMMARY":
            out.append(L.summary())
        elif kind == "B31":
            t31, ro, rn, to, tn = B.b31()
            out.append(t31 + f"\n還付の累計：旧版 {S.fmt(ro)}、本稿 {S.fmt(rn)}。国庫の正味の税収：旧版 {S.fmt(to)}、本稿 {S.fmt(tn)}")
        elif kind == "B32": out.append(B.b32())
        elif kind == "B33": out.append(B.b33())
        elif kind == "B34": out.append(B.b34())
        elif kind == "B35": out.append(B.b35())
        elif kind == "B36G": out.append(B.b36g())
        else: raise ValueError(spec)
    print("\n\n".join(out))
    print(f"\n付録B.1等の計算式：{n}個の式で左辺と右辺が一致した。各表の各行で 国庫の受領累計 = 発生税収 + 立替 − 預かり を検算した（scenarios.py の assert）。")

if __name__ == "__main__":
    main()
