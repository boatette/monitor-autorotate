{
  description = "Rotate monitors from a Pico-mounted accelerometer";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (pkgs: rec {
        monitor-autorotate = pkgs.callPackage ./nix/package.nix { };
        default = monitor-autorotate;
      });

      nixosModules = rec {
        monitor-autorotate = import ./nix/nixos.nix self;
        default = monitor-autorotate;
      };

      checks = forAllSystems (pkgs: {
        # shellcheck runs as part of the build
        inherit (self.packages.${pkgs.stdenv.hostPlatform.system}) monitor-autorotate;
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.mpremote
            pkgs.shellcheck
          ];
        };
      });

      formatter = forAllSystems (pkgs: pkgs.nixfmt-tree);
    };
}
