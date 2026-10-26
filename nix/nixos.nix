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
    enable = lib.mkEnableOption "turning aion's monitors to the orientation a Pico-mounted accelerometer reports";

    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
      defaultText = lib.literalExpression "monitor-autorotate.packages.\${pkgs.stdenv.hostPlatform.system}.default";
      description = "The monitor-autorotate package to use.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = config.programs.aion.enable or false;
        message = "services.monitor-autorotate switches aion's monitor profiles, so it needs programs.aion.enable";
      }
    ];

    # /dev/monitor-orient for a Pico running MicroPython, usable by whoever is logged in at the seat;
    # uaccess only takes effect before 73-seat-late.rules, so it can't go in extraRules' 99-local.rules
    services.udev.packages = [
      (pkgs.writeTextDir "lib/udev/rules.d/70-monitor-autorotate.rules" ''
        SUBSYSTEM=="tty", ATTRS{idVendor}=="2e8a", ATTRS{idProduct}=="0005", SYMLINK+="monitor-orient", TAG+="uaccess"
      '')
    ];

    # runs while aion does, and waits for the sensor if it isn't plugged in
    systemd.user.services.monitor-autorotate = {
      description = "Turn aion's monitors to match the orientation sensor";
      wantedBy = [ "aion-session.target" ];
      partOf = [ "aion-session.target" ];
      after = [ "aion-session.target" ];
      path = [ config.programs.aion.package ];
      serviceConfig = {
        ExecStart = lib.getExe cfg.package;
        Restart = "on-failure";
      };
    };
  };
}
