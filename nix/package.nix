{
  writeShellApplication,
  coreutils,
}:

# `aion` comes from the service's path, so it is the configured build
writeShellApplication {
  name = "monitor-autorotate";
  runtimeInputs = [ coreutils ];
  text = builtins.readFile ../daemon/monitor-autorotate.sh;
  meta.description = "Turn aion's monitors to the orientation a Pico-mounted accelerometer reports";
}
