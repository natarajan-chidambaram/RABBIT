{
  inputs = {
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default";
  };

  outputs =
    inputs@{ ... }:
    inputs.flake-parts.lib.mkFlake { inherit inputs; } {
      systems = import inputs.systems;

      perSystem =
        { pkgs, ... }:
        {
          devShells.default = pkgs.mkShell {
            venvDir = "./.venv";
            packages = [
              pkgs.uv
              (pkgs.python3.withPackages (python-pkgs: [
                python-pkgs.joblib
                python-pkgs.numpy
                python-pkgs.pandas
                python-pkgs.python-dateutil
                python-pkgs.requests
                python-pkgs.scikit-learn
                python-pkgs.scipy
                python-pkgs.tqdm
              ]))
              pkgs.python3Packages.pandas
              pkgs.ruff
              # This execute some shell code to initialize a venv in $venvDir before
              # dropping into the shell
              pkgs.python3Packages.venvShellHook
            ];

            # Run this command, only after creating the virtual environment
            postVenvCreation = ''
              uv sync
            '';
          };
        };
    };
}
