# monitor-autorotate [device]: turns aion's monitors to the orientation the Pico reports
#
# The Pico prints "portrait" or "landscape" on every change and every couple of seconds
# besides. Each change becomes `aion msg profile <orientation>`, which moves every monitor
# to its rule in that profile. The device is reopened whenever it comes back.
device=${1:-/dev/monitor-orient}
last=

follow() {
  # raw, so the tty doesn't echo the Pico's lines back to it
  stty raw -echo || return
  local line
  while IFS= read -r line; do
    line=${line%$'\r'}
    [[ $line == portrait || $line == landscape ]] || continue
    [[ $line != "$last" ]] || continue
    last=$line
    echo "turning to $line"
    aion msg profile "$line" || true
  done
}

while :; do
  if [[ -e $device ]]; then
    follow <"$device" || true
  fi
  sleep 2
done
