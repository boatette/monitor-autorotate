{
  writeShellApplication,
  coreutils,
}:

# the command that turns the outputs comes from the service, so it is the configured one
writeShellApplication {
  name = "monitor-autorotate";
  runtimeInputs = [ coreutils ];
  text = builtins.readFile ../daemon/monitor-autorotate.sh;
  meta.description = "Turn the monitors to the orientation a Pico-mounted accelerometer reports";
}
