#!/usr/bin/env bash
# What is the server short of? Run on the server after a crash (sudo for the logs):
#   sudo bash deploy/diagnose.sh
echo "== memory (MB)"; free -m
echo; echo "== swap"; swapon --show 2>/dev/null || echo "none"
echo; echo "== processes by memory (top 8)"; ps -eo pid,rss,comm,args --sort=-rss | head -9 | awk 'NR==1 {print; next} {printf "%7s %6.0f MB  %s\n", $1, $2/1024, substr($0, index($0,$3), 70)}'
echo; echo "== services"
for s in guandan boardgames nginx; do printf "%-11s %s  (restarts: %s)\n" "$s" "$(systemctl is-active $s 2>/dev/null)" "$(systemctl show $s -p NRestarts --value 2>/dev/null)"; done
echo; echo "== killed for memory? (kernel log)"; (dmesg -T 2>/dev/null || journalctl -k --no-pager 2>/dev/null) | grep -i -E "out of memory|oom-kill|killed process" | tail -5 || true
echo; echo "== Rust core in the server's environment"
/opt/guandan/venv/bin/python -c "import guandan_core as c; print('guandan_core OK, features up to version 5:', hasattr(c, 'STATE_DIM_V5'))" 2>&1 | tail -1
echo; echo "== last guandan log lines"; journalctl -u guandan -n 25 --no-pager 2>/dev/null | cut -c1-180
echo; echo "== last boardgames log lines"; journalctl -u boardgames -n 10 --no-pager 2>/dev/null | cut -c1-180
