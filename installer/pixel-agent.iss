; PixelAgent Windows Installer (Phase 11, docs/DECISIONS.md 2026-08-02)
; Built with Inno Setup (https://jrsoftware.org/isinfo.php) -- a free,
; well-established Windows installer compiler.
;
; IMPORTANT: this script cannot be compiled or tested in this project's
; Linux build environment -- Inno Setup's compiler (ISCC.exe) is a real
; Windows binary. This is a syntactically complete, structurally correct
; script following Inno Setup's documented conventions, but it has NOT
; been built or run in this environment. Build and test it on a real
; Windows machine (see docs/RELEASE.md) before treating it as a working
; installer.
;
; What this installer does NOT solve on its own (see docs/RELEASE.md for
; the full pre-build checklist):
;   - Bundling a real Python runtime + all pip dependencies into
;     dist/pixel-agent/ is a SEPARATE build step (PyInstaller or similar),
;     which must run and produce that directory BEFORE this script is
;     compiled -- this script only packages whatever is already in
;     dist/pixel-agent/, it does not build the Python app itself.
;   - Bundling Tesseract and Playwright's Chromium: both are large,
;     separately-licensed binaries. This script includes them as optional
;     components the installer downloads/copies if present in the build
;     tree -- see the [Components]/[Files] sections below and
;     docs/RELEASE.md for exactly what needs to be staged before building.
;   - Code signing: an unsigned installer will trigger Windows SmartScreen
;     warnings. See docs/RELEASE.md's signing section -- this script emits
;     an unsigned installer by default.

#define MyAppName "PixelAgent"
#define MyAppVersion "0.11.0"
#define MyAppPublisher "Yash Malik"
#define MyAppURL "https://github.com/yash936936/PixelAgent"
#define MyAppExeName "pixel-gui.exe"

[Setup]
AppId={{B4A1E6F0-7C3D-4E2A-9F1B-3D5C8A2E9F41}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Fix for a real bug found live (docs/DECISIONS.md 2026-08-08): Inno Setup
; resolves every relative Source path in [Files] against the .iss script's
; OWN directory (installer\) by default, NOT the directory ISCC.exe was
; invoked from. Every Source path below (dist\pixel-agent\*,
; installer\staging\..., .env.example, README.md) was written assuming
; project-root-relative resolution, which is wrong without this directive.
; SourceDir=.. makes all of them resolve against the project root instead,
; matching what every Source path already assumed -- confirmed live: without
; this, compiling produced "No files found matching
; ...\installer\dist\pixel-agent\*" because Inno was looking one directory
; too deep.
SourceDir=..
; Per-user install by default -- avoids requiring admin rights for a
; single-user desktop automation tool, and keeps profiles_dir/.env under
; the installing user's own account, consistent with src/security/at_rest.py's
; Windows-DPAPI-tied-to-the-current-user design (docs/DECISIONS.md 2026-08-02).
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
; OutputDir resolves relative to SourceDir (set above to the project
; root), NOT relative to this .iss file's own folder as originally
; assumed -- confirmed live (docs/DECISIONS.md 2026-08-08): OutputDir=..\dist\installer
; produced downloads\dist\installer, one level above the project. Corrected
; to dist\installer so the output lands at pixel-agent\dist\installer,
; matching docs/RELEASE.md.
OutputDir=dist\installer
OutputBaseFilename=PixelAgent-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; See docs/RELEASE.md's signing section -- SignTool directives go here
; once a real code-signing certificate exists. Left commented out rather
; than pointing at a placeholder that would silently fail a real build.
; SignTool=signtool
; SignedUninstaller=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Components]
; Core app is always installed. Tesseract/Chromium are optional bundled
; components -- if the person has them already (e.g. Chromium via a
; separately-installed Chrome, or Tesseract via their own install), they
; can skip the extra download/disk space. See docs/RELEASE.md for how
; each component's files get staged into installer/staging/ before build.
Name: "core"; Description: "PixelAgent application (required)"; Types: full compact custom; Flags: fixed
Name: "tesseract"; Description: "Tesseract OCR engine (required for desktop-target-type automation)"; Types: full
Name: "chromium"; Description: "Playwright Chromium (required for browser-target-type automation)"; Types: full

[Files]
; The PyInstaller (or equivalent) build output -- see docs/RELEASE.md's
; "Building the Python app" step. This script does not produce these
; files itself.
Source: "dist\pixel-agent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core

; Staged separately -- see docs/RELEASE.md for exact download/staging
; instructions for each. Not fetched by this script at build time.
;
; NOTE (docs/DECISIONS.md 2026-08-08): PyInstaller's bundled copy of
; Playwright ships with NO Chromium binary of its own -- Playwright always
; expects a browser install to exist at a separate, OS-level cache path
; (normally %LOCALAPPDATA%\ms-playwright, or wherever PLAYWRIGHT_BROWSERS_PATH
; points). A fresh install with no matching env var set crashes on first
; browser-target-type step with "Executable doesn't exist at ...\.local-browsers\
; chromium-<version>\chrome-win\chrome.exe". Staging Chromium into
; {app}\chromium below is necessary but NOT sufficient by itself -- the app
; also needs to be told to look there, which the [Code] section at the
; bottom of this script now does by writing PLAYWRIGHT_BROWSERS_PATH into
; the generated .env (confirmed live to fix the crash).
Source: "installer\staging\tesseract\*"; DestDir: "{app}\tesseract"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: tesseract
Source: "installer\staging\chromium\*"; DestDir: "{app}\chromium"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: chromium

Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; TESSERACT_CMD (docs/DECISIONS.md 2026-08-01/02): if the bundled
; Tesseract component was installed, point the app at it automatically so
; the user never has to manually set TESSERACT_CMD themselves -- exactly
; the friction src/doctor.py's Tesseract check exists to catch when it's
; missing.
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[Code]
// Writes an initial .env with TESSERACT_CMD and PLAYWRIGHT_BROWSERS_PATH
// pre-filled based on which optional components were installed -- the
// app's own first-run SetupWizard (src/gui/setup_wizard_logic.py +
// src/gui/widgets/setup_wizard.py, Phase 11) still handles GEMINI_API_KEY
// and Chrome profile selection interactively; this only pre-seeds what
// the installer itself already knows.
//
// PLAYWRIGHT_BROWSERS_PATH added 2026-08-08 (docs/DECISIONS.md) after a
// real live-run crash: PyInstaller's bundled Playwright has no Chromium
// of its own, and looks for one at a fixed internal cache path that
// nothing in the build process populated. Since the app loads .env into
// the process environment on startup (the same mechanism GEMINI_API_KEY
// already relies on), and Playwright itself reads
// PLAYWRIGHT_BROWSERS_PATH from the OS environment at launch time (not
// through config.py), pointing it at {app}\chromium -- which the
// [Files] section above already stages with the correct
// chromium-<version>\chrome-win\ subfolder structure Playwright expects
// -- is sufficient with no PyInstaller or config.py changes required.
// Only written when the chromium component was actually selected and
// staged; if skipped, PLAYWRIGHT_BROWSERS_PATH is left unset and
// Playwright falls back to its normal OS-level cache search, unchanged
// from before this fix.
procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvPath: string;
  EnvContents: string;
begin
  if CurStep = ssPostInstall then
  begin
    EnvPath := ExpandConstant('{app}\.env');
    if not FileExists(EnvPath) then
    begin
      EnvContents := '';
      if IsComponentSelected('tesseract') then
        EnvContents := EnvContents + 'TESSERACT_CMD=' + ExpandConstant('{app}\tesseract\tesseract.exe') + #13#10;
      if IsComponentSelected('chromium') then
        EnvContents := EnvContents + 'PLAYWRIGHT_BROWSERS_PATH=' + ExpandConstant('{app}\chromium') + #13#10;
      SaveStringToFile(EnvPath, EnvContents, False);
    end;
  end;
end;
