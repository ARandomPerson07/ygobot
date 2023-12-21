{pkgs}: {
  deps = [
    pkgs.glibcLocales
    pkgs.glibc
    pkgs.postgresql
    pkgs.openssl
  ];
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.glibcLocales
      pkgs.postgresql
    ];
  };
}
