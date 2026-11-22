## Sample 26576

| Step | Tool | Call | Events | Exit code | Command | Output | Model's view |
|---|---|---|---|---|---|---|---|
| 1 | `bash` | pwd && ls -la | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 1 | `bash` | which bash sh od tail wc grep date; bash --vers… | 1 | 0 | same after known change (wrapper) | same | same |
| 2 | `text_editor` | view /test_task.py | 10 | 0 | same after known change (envelope) | same after known change (envelope) | same |
| 3 | `text_editor` | create /solution.sh | 1 | 0 | same after known change (envelope) | same after known change (envelope) | same |
| 4 | `bash` | chmod +x /solution.sh && cd / && rm -f string_l… | 1 | 0 | same after known change (wrapper) | same | same |
| 5 | `bash` | cd / && rm -f string_log.txt for i in $(seq 1 1… | 1 | 0 | same after known change (wrapper) | same | same |
| 5 | `bash` | mkdir -p /tmp/otherdir && cd /tmp/otherdir && r… | 1 | 0 | same after known change (wrapper) | same | same |
| 6 | `bash` | cd / echo "=== invalid arg ==="; ./solution.sh … | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 7 | `run_tests` |  | 1 | 0 | cannot compare: the call holds no command | same after known change (layout) | same |
| 8 | `bash` | cd / && ls -la solution.sh string_log.txt 2>&1;… | 1 | 0 | same after known change (wrapper) | same | same |
| 8 | `run_tests` |  | 1 | 0 | cannot compare: the call holds no command | same after known change (layout) | same |
| 9 | `submit` |  | 0 |  | cannot compare: no event | cannot compare: no event | same |

Events outside tool calls: init 1, setup (add_test_file) 2, scorer 2
Pairs of calls of one step with events that overlap in time: 2

## Sample 76105

| Step | Tool | Call | Events | Exit code | Command | Output | Model's view |
|---|---|---|---|---|---|---|---|
| 1 | `bash` | ls -la / && ls -la ~ && pwd | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 1 | `bash` | which nano; nano --version 2>/dev/null \| head … | 1 | 0 | same after known change (wrapper) | same | same |
| 2 | `text_editor` | view /test_task.py | 10 | 0 | same after known change (envelope) | same after known change (envelope) | same |
| 2 | `bash` | command -v nano && echo "nano found" \|\| echo … | 1 | 0 | same after known change (wrapper) | same | same |
| 3 | `bash` | ls /bin/sh /bin/bash 2>&1; echo "---"; which aw… | 1 | 0 | same after known change (wrapper) | same | same |
| 3 | `bash` | apk add nano 2>&1 \| tail -5 | 1 | 0 | same after known change (wrapper) | same | same |
| 4 | `bash` | apk update 2>&1 \| tail -3 && apk add nano 2>&1… | 1 | 0 | same after known change (wrapper) | same | same |
| 5 | `bash` | cat /etc/resolv.conf; echo "---"; cat /etc/nssw… | 1 | 0 | same after known change (wrapper) | same | same |
| 5 | `bash` | nslookup dl-cdn.alpinelinux.org 2>&1 \| head -5… | 1 | 0 | same after known change (wrapper) | same | same |
| 6 | `bash` | find / -name "*nano*" -not -path "/proc/*" -not… | 1 | 0 | same after known change (wrapper) | same | same |
| 6 | `bash` | find / -name "*.apk" -not -path "/proc/*" -not … | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 7 | `bash` | ls /opt/venv/bin 2>/dev/null \| head; env \| gr… | 1 | 0 | same after known change (wrapper) | same | same |
| 8 | `bash` | cat > /usr/local/bin/nano << 'EOF' #!/bin/sh # … | 1 | 0 | same after known change (wrapper) | same | same |
| 9 | `text_editor` | create /solution.sh | 1 | 0 | same after known change (envelope) | same after known change (envelope) | same |
| 10 | `bash` | chmod +x /solution.sh && ls -la /solution.sh # … | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 11 | `bash` | cd /tmp # Error case 1: non-existent file /solu… | 1 | 0 | same after known change (wrapper) | same after known change (stream separator) | same |
| 11 | `bash` | cd /tmp # Whitespace-only lines (spaces and tab… | 1 | 0 | same after known change (wrapper) | same | same |
| 12 | `bash` | cd / && (which pytest \|\| /opt/venv/bin/pytest… | 1 | 0 | same after known change (wrapper) | same | same |
| 13 | `run_tests` |  | 1 | 0 | cannot compare: the call holds no command | same after known change (layout) | same |
| 14 | `bash` | cd / && for i in 1 2 3 4 5; do pytest test_task… | 1 | 0 | same after known change (wrapper) | same | same |
| 15 | `bash` | find / -name "pytest" -type f -not -path "/proc… | 1 | 0 | same after known change (wrapper) | same | same |

Events outside tool calls: init 1, setup (add_test_file) 2, scorer 2
Pairs of calls of one step with events that overlap in time: 5

## Sample 511704

| Step | Tool | Call | Events | Exit code | Command | Output | Model's view |
|---|---|---|---|---|---|---|---|
| 1 | `bash` | pwd && ls -la && echo "---" && bash --version \… | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 1 | `bash` | find / -maxdepth 4 \( -name "*test*" -o -name "… | 1 | 0 | same after known change (wrapper) | same | same |
| 2 | `text_editor` | view /test_task.py | 10 | 0 | same after known change (envelope) | same after known change (envelope) | same |
| 3 | `bash` | ls -la /bin/bash /usr/bin/bash 2>&1; which tr h… | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 4 | `text_editor` | create /solution.sh | 1 | 0 | same after known change (envelope) | same after known change (envelope) | same |
| 5 | `bash` | chmod +x /solution.sh && cd / && rm -rf /tmp/t1… | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 6 | `bash` | cd / && for p in /root/test /proc /dev /sys /pr… | 1 | 0 | same after known change (wrapper) | same after known change (stream separator) | same |
| 6 | `bash` | cd / && rm -rf /tmp/t2 && mkdir -p /tmp/t2 && t… | 1 | 0 | same after known change (wrapper) | same after known change (stream separator) | same |
| 7 | `run_tests` |  | 1 | 0 | cannot compare: the call holds no command | same after known change (layout) | same |
| 8 | `bash` | cd / && rm -rf /tmp/final && ./solution.sh /tmp… | 1 | 0 | same after known change (wrapper) | same | same |
| 8 | `bash` | cd / && for i in 1 2 3; do python3 -m pytest te… | 1 | 0 | same after known change (wrapper) | same | same |
| 9 | `bash` | ls /opt/ 2>/dev/null; which -a python python3 2… | 1 | 0 | same after known change (wrapper) | same | same |
| 10 | `bash` | cd / && for i in 1 2 3 4 5; do /opt/venv/bin/py… | 1 | 0 | same after known change (wrapper) | same | same |
| 11 | `bash` | rm -rf /tmp/t1 /tmp/t2 /tmp/nest /tmp/final /tm… | 1 | 0 | same after known change (wrapper) | same | same |
| 12 | `submit` |  | 0 |  | cannot compare: no event | cannot compare: no event | same |

Events outside tool calls: init 1, setup (add_test_file) 2, scorer 2
Pairs of calls of one step with events that overlap in time: 3

## Sample 574105

| Step | Tool | Call | Events | Exit code | Command | Output | Model's view |
|---|---|---|---|---|---|---|---|
| 1 | `bash` | whoami; id; cat /etc/os-release 2>/dev/null \| … | 1 | 1 | same after known change (wrapper) | same | same |
| 1 | `bash` | ls -la /var/log/ \| head -20; ls -la / \| head … | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 2 | `bash` | cat /test_task.py | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 2 | `bash` | which sshd; ls /usr/sbin/sshd 2>/dev/null; ls /… | 1 | 1 | same after known change (wrapper) | same | same |
| 3 | `bash` | ls -la /.pytest_cache/ 2>/dev/null; cat /.pytes… | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 3 | `bash` | apk list --installed 2>/dev/null \| grep -i -E … | 1 | 0 | same after known change (wrapper) | same | same |
| 4 | `bash` | timeout 60 apk add --no-cache openssh-server 2>… | 1 | 0 | same after known change (wrapper) | same | same |
| 5 | `bash` | which pgrep pkill setsid nohup kill sleep 2>&1;… | 1 | 0 | same after known change (wrapper) | same | same |
| 5 | `bash` | sh -c 'exec -a testname sleep 0.1' & sleep 0.05… | 1 | 0 | same after known change (wrapper) | same after known change (stream separator) | same |
| 6 | `bash` | mkdir -p /usr/local/sbin cat > /usr/local/sbin/… | 1 | 0 | same after known change (wrapper) | same | same |
| 7 | `bash` | cat /proc/168/cmdline 2>/dev/null \| tr '\0' ' … | 1 | 0 | same after known change (wrapper) | same | same |
| 8 | `bash` | ps aux \| grep -E 'sshd\|sleep' \| grep -v grep… | 1 | 0 | same after known change (wrapper) | same | same |
| 9 | `bash` | cat > /tmp/exp.sh <<'EOF' #!/bin/sh setsid /usr… | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 10 | `bash` | sleep 0.1 && echo "fractional sleep OK"; pgrep … | 1 | 0 | same after known change (wrapper) | same | same |
| 11 | `bash` | which flock; setsid sleep 300 & sleep 0.3; GP=$… | 1 | 0 | same after known change (wrapper) | same | same |
| 12 | `bash` | setsid sleep 300 & sleep 0.3 # find the real sl… | 1 | 1 | same after known change (wrapper) | same | same |
| 13 | `bash` | kill 262 272 2>/dev/null; sleep 0.2 kill -- -28… | 1 | 0 | same after known change (wrapper) | same | same |
| 14 | `bash` | tr '\0' ' ' < /proc/314/cmdline 2>/dev/null; ec… | 1 | 0 | same after known change (wrapper) | same | same |
| 15 | `bash` | kill -- -218 2>&1; echo "exit: $?"; sleep 0.5; … | 1 | 0 | same after known change (wrapper) | same | same |

Events outside tool calls: init 1, setup (add_test_file) 2, scorer 2
Pairs of calls of one step with events that overlap in time: 4

## Sample 598634

| Step | Tool | Call | Events | Exit code | Command | Output | Model's view |
|---|---|---|---|---|---|---|---|
| 1 | `bash` | pwd && ls -la | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 1 | `bash` | ls -la / /app /workspace /repo /test 2>/dev/nul… | 1 | 0 | same after known change (wrapper) | same after known change (cut) | same |
| 2 | `text_editor` | view /test_task.py | 10 | 0 | same after known change (envelope) | same after known change (envelope) | same |
| 3 | `text_editor` | create /solution.sh | 1 | 0 | same after known change (envelope) | same after known change (envelope) | same |
| 4 | `bash` | chmod +x /solution.sh && ls -la /solution.sh | 1 | 0 | same after known change (wrapper) | same | same |
| 5 | `bash` | mkdir -p /tmp/t1 && cd /tmp/t1 && printf 'chr1\… | 1 | 0 | same after known change (wrapper) | same | same |
| 6 | `bash` | mkdir -p /tmp/t2 && cd /tmp/t2 && cp /solution.… | 1 | 0 | same after known change (wrapper) | same | same |
| 6 | `bash` | mkdir -p /tmp/t3 && cd /tmp/t3 && cp /solution.… | 1 | 0 | same after known change (wrapper) | same | same |
| 7 | `bash` | mkdir -p /tmp/t4 && cd /tmp/t4 && cp /solution.… | 1 | 0 | same after known change (wrapper) | same | same |
| 7 | `bash` | mkdir -p /tmp/t5 && cd /tmp/t5 && cp /solution.… | 1 | 0 | same after known change (wrapper) | same | same |
| 7 | `bash` | mkdir -p /tmp/t6 && cd /tmp/t6 && cp /solution.… | 1 | 0 | same after known change (wrapper) | same | same |
| 7 | `bash` | mkdir -p /tmp/t7 && cd /tmp/t7 && cp /solution.… | 1 | 0 | same after known change (wrapper) | same | same |
| 8 | `run_tests` |  | 1 | 0 | cannot compare: the call holds no command | same after known change (layout) | same |
| 9 | `bash` | ls -la /solution.sh && [ -x /solution.sh ] && e… | 1 | 0 | same after known change (wrapper) | same | same |
| 10 | `submit` |  | 0 |  | cannot compare: no event | cannot compare: no event | same |

Events outside tool calls: init 1, setup (add_test_file) 2, scorer 2
Pairs of calls of one step with events that overlap in time: 8

## Counts, all samples

| Tool | Calls | Events | Calls with no event | Calls with more than one event |
|---|---|---|---|---|
| `bash` | 66 | 66 | 0 | 0 |
| `run_tests` | 5 | 5 | 0 | 0 |
| `submit` | 3 | 0 | 3 | 0 |
| `text_editor` | 8 | 44 | 0 | 4 |

| Where the events sit | Events |
|---|---|
| in tool calls | 115 |
| init | 5 |
| scorer | 10 |
| setup (add_test_file) | 10 |

| Comparison | Count |
|---|---|
| command: cannot compare: the call holds no command | 5 |
| command: same after known change (envelope) | 8 |
| command: same after known change (wrapper) | 66 |
| events not placed | 0 |
| exit code not 0 | 3 |
| exit code not 0 and no error in the tool result | 3 |
| model's view: same | 82 |
| output: same | 48 |
| output: same after known change (cut) | 14 |
| output: same after known change (envelope) | 8 |
| output: same after known change (layout) | 5 |
| output: same after known change (stream separator) | 4 |
| pairs of calls that overlap in time | 22 |
