class Intentype < Formula
  desc "Voice-to-text daemon that rewrites speech with AI and injects it anywhere"
  homepage "https://github.com/YOUR_USERNAME/IntenType"
  url "https://github.com/YOUR_USERNAME/IntenType/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "FILL_IN_AFTER_FIRST_RELEASE"
  license "MIT"

  depends_on "python@3.12"
  depends_on :macos

  def install
    venv = libexec/"venv"
    system "#{Formula["python@3.12"].opt_bin}/python3", "-m", "venv", venv
    venv_pip = "#{venv}/bin/pip"
    system venv_pip, "install", "--upgrade", "pip"
    system venv_pip, "install", "-r", "requirements.txt"

    # Install daemon source into libexec
    libexec.install "daemon", "requirements.txt"

    # Wrapper script
    (bin/"intentype").write <<~SH
      #!/bin/bash
      exec "#{venv}/bin/python" -m daemon.main "$@"
    SH
    chmod 0755, bin/"intentype"

    # launchd plist for login auto-start
    (prefix/"com.intentype.app.plist").write <<~XML
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
        "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>com.intentype.app</string>
        <key>ProgramArguments</key>
        <array>
          <string>#{venv}/bin/python</string>
          <string>-m</string>
          <string>daemon.main</string>
        </array>
        <key>WorkingDirectory</key>
        <string>#{libexec}</string>
        <key>RunAtLoad</key>
        <true/>
        <key>KeepAlive</key>
        <true/>
        <key>StandardOutPath</key>
        <string>#{var}/log/intentype.log</string>
        <key>StandardErrorPath</key>
        <string>#{var}/log/intentype.log</string>
      </dict>
      </plist>
    XML
  end

  def caveats
    <<~EOS
      IntenType requires three macOS permissions — grant each in
      System Settings → Privacy & Security after first launch:
        • Accessibility
        • Input Monitoring
        • Microphone

      To start IntenType now:
        intentype

      To start automatically at login:
        mkdir -p ~/Library/LaunchAgents
        cp #{prefix}/com.intentype.app.plist ~/Library/LaunchAgents/
        launchctl load ~/Library/LaunchAgents/com.intentype.app.plist

      Set your OpenAI API key via the 🎤 menubar icon → Set API Key…
    EOS
  end

  test do
    system "#{bin}/intentype", "--help"
  end
end
