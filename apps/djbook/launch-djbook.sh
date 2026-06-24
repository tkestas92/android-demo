#!/bin/bash
# Shared launch helper — keep DJ Book in foreground and hide WebView tester.
launch_djbook_app() {
  local pkg="com.tkestas92.djbookmobilev2"
  local adb=(docker exec ws-scrcpy-djbook adb -s redroid:5555)

  "${adb[@]}" shell pm disable-user --user 0 org.chromium.webview_shell >/dev/null 2>&1 || true
  "${adb[@]}" shell am force-stop org.chromium.webview_shell >/dev/null 2>&1 || true
  "${adb[@]}" shell am start -W -n "$pkg/.MainActivity" >/dev/null 2>&1 || true
  sleep 2
  "${adb[@]}" shell am start -n "$pkg/.MainActivity" >/dev/null 2>&1 || true

  if "${adb[@]}" shell dumpsys window 2>/dev/null | grep -q "mCurrentFocus=.*$pkg"; then
    return 0
  fi
  return 1
}
