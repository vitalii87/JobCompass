Unicode True

!include "MUI2.nsh"

!ifndef APP_VERSION
  !define APP_VERSION "0.11.2"
!endif

!define APP_NAME "JobCompass"
!define APP_PUBLISHER "JobCompass"
!define APP_EXE "JobCompass.exe"
!define START_MENU_FOLDER "${APP_NAME}"
!define DESKTOP_LINK "${APP_NAME}.lnk"
!define PROJECT_ROOT "${__FILEDIR__}\..\.."
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\JobCompass"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "${PROJECT_ROOT}\release\JobCompass-${APP_VERSION}-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\JobCompass"
InstallDirRegKey HKCU "Software\JobCompass" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "JobCompass"
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "JobCompass"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "FileDescription" "JobCompass installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright 2026 JobCompass contributors"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch JobCompass"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "Ukrainian"
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  ; Use the signed-in user's Shell folders. $DESKTOP therefore follows
  ; Windows Known Folder redirection, including a Desktop moved to OneDrive.
  SetShellVarContext current
FunctionEnd

Function un.onInit
  SetShellVarContext current
FunctionEnd

Section "JobCompass" MainSection
  SetOutPath "$INSTDIR"
  File /r "${PROJECT_ROOT}\dist\JobCompass\*"
  File /oname=README.md "${PROJECT_ROOT}\README.md"
  File /oname=README.en.md "${PROJECT_ROOT}\README.en.md"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\${START_MENU_FOLDER}"
  CreateShortcut "$SMPROGRAMS\${START_MENU_FOLDER}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortcut "$SMPROGRAMS\${START_MENU_FOLDER}\Uninstall ${APP_NAME}.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\${DESKTOP_LINK}" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  WriteRegStr HKCU "Software\JobCompass" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "JobCompass"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  nsExec::ExecToLog '"$INSTDIR\${APP_EXE}" --data "$LOCALAPPDATA\JobCompass\data\jobcompass.json" remove-scheduled-tasks'
  Delete "$DESKTOP\${DESKTOP_LINK}"
  Delete "$SMPROGRAMS\${START_MENU_FOLDER}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${START_MENU_FOLDER}\Uninstall ${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${START_MENU_FOLDER}"

  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  DeleteRegKey HKCU "Software\JobCompass"
  RMDir /r "$INSTDIR"

  ; User data in %LOCALAPPDATA%\JobCompass is intentionally preserved.
SectionEnd
