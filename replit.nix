{pkgs}: {
  deps = [
    pkgs.opencode
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.ffmpeg
    pkgs.unzip
    pkgs.stdenv.cc.cc.lib
    pkgs.playwright-driver
  ];
}
