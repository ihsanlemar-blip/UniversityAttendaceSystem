# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.05"; # or "unstable"

  # System packages required for this full-stack monorepo
  packages = [
    # Flutter & Android SDK toolchain
    pkgs.flutter
    pkgs.jdk17
    pkgs.android-tools

    # Node.js toolchain for apps/web
    pkgs.nodejs_20
    pkgs.nodePackages.npm

    # Python toolchain for backend
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv

    # Utilities
    pkgs.git
    pkgs.curl
    pkgs.unzip
    pkgs.which
  ];

  # Environment variables in the workspace
  env = {
    FLUTTER_CHANNEL = "stable";
  };

  idx = {
    # Open-VSX / VS Code extensions
    extensions = [
      # Python & Backend
      "ms-python.python"
      "charliermarsh.ruff"

      # Flutter & Dart
      "Dart-Code.flutter"
      "Dart-Code.dart-code"

      # Frontend / Next.js / TypeScript
      "dbaeumer.vscode-eslint"
      "bradlc.vscode-tailwindcss"
      "esbenp.prettier-vscode"
    ];

    # Workspace lifecycle hooks
    workspace = {
      # Runs when a workspace is first created with this dev.nix file
      onCreate = {
        # Initialize Flutter dependencies
        setup-flutter = "cd apps/mobile && flutter pub get";
        # Initialize Next.js web dependencies
        setup-web = "cd apps/web && npm ci";
        # Open essential workspace documentation
        default.openFiles = [ "README.md" "apps/web/src/app/page.tsx" "apps/mobile/lib/main.dart" ];
      };
      # Runs each time the workspace is (re)started
      onStart = {
        # Optional warm-up checks
      };
    };

    # Live Previews Configuration
    previews = {
      enable = true;
      previews = {
        # Next.js Web Frontend Preview
        web = {
          command = [
            "npm"
            "run"
            "dev"
            "--prefix"
            "apps/web"
            "--"
            "--port"
            "$PORT"
            "--hostname"
            "0.0.0.0"
          ];
          manager = "web";
        };

        # Flutter Mobile Cloud Emulator Preview
        android = {
          command = [
            "flutter"
            "run"
            "--enable-software-rendering"
            "-d"
            "android-arm64"
          ];
          cwd = "apps/mobile";
          manager = "flutter";
        };
      };
    };
  };
}
