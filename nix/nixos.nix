self:
{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.monitor-autorotate;
in
{
  options.services.monitor-autorotate = {
    enable = lib.mkEnableOption "turning monitors to the orientation a Pico-mounted accelerometer reports";

    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
      defaultText = lib.literalExpression "monitor-autorotate.packages.\${pkgs.stdenv.hostPlatform.system}.default";
      description = "The monitor-autorotate package to use.";
    };

    command = lib.mkOption {
      type = lib.types.str;
      example = lib.literalExpression ''"''${pkgs.writeShellScript "rotate" "wlr-randr --output HDMI-A-1 --transform 90"}"'';
      description = "Run with `portrait` or `landscape` as its only argument whenever the orientation changes; it turns the compositor's outputs.";
    };

    target = lib.mkOption {
      type = lib.types.str;
      default = "graphical-session.target";
      description = "The user target the service runs under, i.e. the one the compositor's session starts.";
    };
  };

  config = lib.mkIf cfg.enable {
    # /dev/monitor-orient for a Pico running MicroPython, usable by whoever is logged in at the seat;
    # uaccess only takes effect before 73-seat-late.rules, so it can't go in extraRules' 99-local.rules
    services.udev.packages = [
      (pkgs.writeTextDir "lib/udev/rules.d/70-monitor-autorotate.rules" ''
        SUBSYSTEM=="tty", ATTRS{idVendor}=="2e8a", ATTRS{idProduct}=="0005", SYMLINK+="monitor-orient", TAG+="uaccess"
      '')
    ];

    # runs while the compositor does, and waits for the sensor if it isn't plugged in
    systemd.user.services.monitor-autorotate = {
      description = "Turn the monitors to match the orientation sensor";
      wantedBy = [ cfg.target ];
      partOf = [ cfg.target ];
      after = [ cfg.target ];
      environment.MONITOR_AUTOROTATE_COMMAND = cfg.command;
      serviceConfig = {
        ExecStart = lib.getExe cfg.package;
        Restart = "on-failure";
      };
    };
  };
}
