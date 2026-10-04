#!/bin/sh
# すべての検算を実行し、期待される出力（expected/）と比べる。
set -e
cd "$(dirname "$0")"
python3 print_tables.py > out_tables.txt
python3 check_late_hold_b33_b34.py > out_b33_b34.txt
python3 check_random_b4.py > out_b4.txt
diff expected/tables.txt out_tables.txt
diff expected/b33_b34.txt out_b33_b34.txt
diff expected/b4.txt out_b4.txt
echo "すべての出力が expected/ と一致した"
