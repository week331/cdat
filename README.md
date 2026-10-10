# CDAT（累積差額調整税）

東 昭博（Azuma, Akihiro）の論文「累積差額調整税 (CDAT)：累積差額のリアルタイム管理に基づく消費課税の設計仮説」に関するプログラムを置くリポジトリです。

## 内容

- `verification/`：論文（2026-10-10版）の16節と付録Bの数値を再現する検算プログラム。使い方は `verification/README.md` を参照。
- `.github/workflows/verify.yml`：ファイルが更新されるたびに、GitHub上で検算を自動実行する設定。結果は「Actions」タブで確認できます。

今後、CDATウォレットと還付バッファの動きを確かめる模擬アプリケーション（実際のお金や個人情報は扱わない）を加える予定です。

## English summary

Verification code for the paper "Cumulative Difference Adjustment Tax (CDAT): A Design Hypothesis for Consumption Taxation Based on Real-Time Management of Cumulative Differences" by Akihiro Azuma. `verification/` reproduces the numbers in Section 16 and Appendix B (Python 3 standard library only, fixed random seeds, exact rational arithmetic). The checks run automatically on GitHub Actions.

## ライセンス

MIT License（`LICENSE` を参照）。
