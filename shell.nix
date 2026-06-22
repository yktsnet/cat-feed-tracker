{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  buildInputs = with pkgs; [
    mpremote
    python3
  ];

  shellHook = ''
    VENV=.venv
    if [ ! -d "$VENV" ]; then
      python3 -m venv "$VENV"
    fi
    source "$VENV/bin/activate"
    pip install -q -r server/requirements.txt -r server/requirements-dev.txt
  '';
}
