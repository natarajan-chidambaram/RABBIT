{ ... }:

{
  perSystem =
    { pkgs, ... }:
    {
      devShells.default = pkgs.mkShell {
        venvDir = "./.venv";
        packages = [
          pkgs.poetry
          pkgs.python3Packages.numpy
          pkgs.python3Packages.pandas
          pkgs.ruff
          # This execute some shell code to initialize a venv in $venvDir before
          # dropping into the shell
          pkgs.python3Packages.venvShellHook
        ];

        # Run this command, only after creating the virtual environment
        postVenvCreation = ''
          poetry install
        '';
      };
    };
}
