; Tetrad Studio installer for Windows (per-user, no admin needed)
Unicode true
SetCompressor /SOLID lzma
!include "MUI2.nsh"

!define APPNAME "Tetrad Studio"
!define VERSION "1.5.0"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\TetradStudio"

Name "${APPNAME}"
OutFile "..\dist\Tetrad-Studio-Setup-${VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\Tetrad Studio"
InstallDirRegKey HKCU "Software\TetradStudio" "InstallDir"
RequestExecutionLevel user
BrandingText "Tetrad Studio ${VERSION}"
VIProductVersion "1.5.0.0"
VIAddVersionKey "ProductName" "${APPNAME}"
VIAddVersionKey "FileDescription" "${APPNAME} Setup"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" ""

!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "sidebar.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "sidebar.bmp"
!define MUI_WELCOMEPAGE_TITLE "Install Tetrad Studio"
!define MUI_WELCOMEPAGE_TEXT "Russian reading, vocabulary and OPI practice.$\r$\n$\r$\nThis installs Tetrad Studio with the Russian Reader, List Trainer and OPI Memory Tool. It installs just for you and doesn't need an administrator password."
!define MUI_FINISHPAGE_RUN "$INSTDIR\Tetrad Studio.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Open Tetrad Studio now"
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  ; close a running copy so files can be replaced on upgrade
  nsExec::Exec 'taskkill /F /IM "Tetrad Studio.exe"'
  Sleep 500
  SetOutPath "$INSTDIR"
  RMDir /r "$INSTDIR\resources"
  File /r "..\dist\win-unpacked\*.*"
  File "icon.ico"
  WriteUninstaller "$INSTDIR\Uninstall Tetrad Studio.exe"

  CreateShortCut "$DESKTOP\Tetrad Studio.lnk" "$INSTDIR\Tetrad Studio.exe" "" "$INSTDIR\icon.ico" 0
  CreateDirectory "$SMPROGRAMS\Tetrad Studio"
  CreateShortCut "$SMPROGRAMS\Tetrad Studio\Tetrad Studio.lnk" "$INSTDIR\Tetrad Studio.exe" "" "$INSTDIR\icon.ico" 0
  CreateShortCut "$SMPROGRAMS\Tetrad Studio\Russian Reader.lnk" "$INSTDIR\Tetrad Studio.exe" "reader" "$INSTDIR\icon.ico" 0
  CreateShortCut "$SMPROGRAMS\Tetrad Studio\List Trainer.lnk" "$INSTDIR\Tetrad Studio.exe" "list-trainer" "$INSTDIR\icon.ico" 0
  CreateShortCut "$SMPROGRAMS\Tetrad Studio\OPI Memory Tool.lnk" "$INSTDIR\Tetrad Studio.exe" "opi-tool" "$INSTDIR\icon.ico" 0
  CreateShortCut "$SMPROGRAMS\Tetrad Studio\OPI Worked Example.lnk" "$INSTDIR\Tetrad Studio.exe" "opi-example" "$INSTDIR\icon.ico" 0
  CreateShortCut "$SMPROGRAMS\Tetrad Studio\Uninstall Tetrad Studio.lnk" "$INSTDIR\Uninstall Tetrad Studio.exe"

  WriteRegStr HKCU "Software\TetradStudio" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayName" "${APPNAME}"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINSTKEY}" "Publisher" "Tetrad Studio"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\icon.ico"
  WriteRegStr HKCU "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "UninstallString" '"$INSTDIR\Uninstall Tetrad Studio.exe"'
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  nsExec::Exec 'taskkill /F /IM "Tetrad Studio.exe"'
  Sleep 500
  Delete "$DESKTOP\Tetrad Studio.lnk"
  RMDir /r "$SMPROGRAMS\Tetrad Studio"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "${UNINSTKEY}"
  DeleteRegKey HKCU "Software\TetradStudio"
  ; your study progress lives in %APPDATA%\Tetrad Studio and is kept on purpose
SectionEnd
