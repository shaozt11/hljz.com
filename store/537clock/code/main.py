#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
537 Clock - Python translation
Windows console stopwatch / clock.
"""

from __future__ import annotations

import ctypes
import locale
import os
import threading
import sys
import time
import webbrowser
from datetime import datetime
from collections import deque
from typing import Dict


APP_NAME_L = "537 Clock"
APP_NAME_S = "537Clock"
APP_NAME_CN = "537秒表"

APP_VERSION = "1.3"
APP_BUILDVERSION = "1.3"

APP_IDEA = "Less is more"
APP_IDEA_CN = "少即是多"

APP_DEVELOPER = "537 Studio"
APP_WEBSITE = "https://www.537studio.com"
APP_EMAIL = "hello@537studio.com"
APP_OPENSOURCE_ADDRESS_LISENCE = "https://www.gnu.org/licenses/lgpl-3.0-standalone.html"
APP_OPENSOURCE_ADDRESS_GITEE = "https://gitee.com/FTS-537Studio/537Clock"
APP_OPENSOURCE_ADDRESS_GITHUB = "https://github.com/537Studio/537Clock"

LANG_EN_US = 0
LANG_ZH_CN = 1
LANG_ZH_CN_TR = 2

FOREGROUND_BLUE = 0x0001
FOREGROUND_GREEN = 0x0002
FOREGROUND_RED = 0x0004
FOREGROUND_INTENSITY = 0x0008
STD_OUTPUT_HANDLE = -11

VK_SPACE = 0x20
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B


def _enable_utf8_console() -> None:
    if os.name == "nt":
        os.system("chcp 65001 >nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _get_default_language() -> int:
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except Exception:
        lang_id = 0
    if lang_id in (0x0804, 0x1004):
        return LANG_ZH_CN
    if lang_id in (0x0404, 0x0C04, 0x1404, 0x7C04):
        return LANG_ZH_CN_TR
    return LANG_EN_US


def _resolve_cli_language(token: str) -> int | None:
    t = token.lower()
    cn = {
        "cn", "zh-cn", "simplified-cn", "sim-cn", "chinese", "simplified-chinese",
        "prc", "people's-republic-of-china", "china", "chinese-mainland",
        "china-mainland",
    }
    tr = {
        "traditional-cn", "tra-cn", "tr-cn", "traditional-chinese", "hong-kong",
        "hk", "taiwan", "tw", "macao", "macau", "mo", "zh-cn-tr", "zh-tw",
        "zh-hk", "zh-mo",
    }
    en = {
        "en", "english", "en-us", "en-gb", "en-au", "en-ca", "en-nz", "en-ie",
        "en-za", "en-jm", "en-tt", "en-ph", "en-in", "en-my", "en-sg",
    }
    if t in cn:
        return LANG_ZH_CN
    if t in tr:
        return LANG_ZH_CN_TR
    if t in en:
        return LANG_EN_US
    return None


def make_texts(lan: int) -> Dict[str, str]:
    if lan == LANG_ZH_CN:
        return {
            "app_name": APP_NAME_CN,
            "version": "版本",
            "build_version": "构建版本",
            "support": "由 537工作室 提供支持",
            "copyright": "版权所有 (C) 537工作室. 2023-2024. 保留所有权利.",
            "tip": "呼吁俄乌两国停战！停止这场无意义的战争！",
            "year": "年",
            "month": "月",
            "date": "日",
            "hour": "时",
            "min": "分",
            "sec": "秒",
            "timer_sec": "秒",
            "pausepanel": "暂停面板",
            "pausepanel_line1": "------------",
            "pausepanel_line2": "------------------",
            "pausepanel_line3": "-------------------",
            "timerclear": "计时清零",
            "abouttheprogram": "关于程序",
            "changecolor": "更改颜色",
            "officialwebsite": "官方网站",
            "email": "电子邮件",
            "license": "使用许可",
            "opensourcewebsite": "开源网站",
            "clearscreen": "清空屏幕",
            "continuethetimer": "继续计时",
            "exit": "退出程序",
            "cancel": "取消",
            "paused": "已暂停",
            "press_key": "按下按键",
            "press_key_enable": "按下按键以启用功能",
            "time_clear": "时间已清零，",
            "website_is": "网站地址: ",
            "official_opened": "已打开官方网站，",
            "email_opened": "已打开邮件窗口，",
            "license_opened": "已打开开源协议网站，",
            "select_website": "请选择要访问的站点",
            "already_open": "已打开 ",
            "exiting": "正在退出...",
            "press_enter": "按回车键以继续...",
            "press_space": "按空格键以继续...",
            "menu_head": "\n>>-年--月--日----时--分--秒-----\nUnix时间戳-----\n-计时----------------------------",
            "menu_title": "537秒表",
        }
    if lan == LANG_ZH_CN_TR:
        return {
            "app_name": APP_NAME_CN,
            "version": "版本",
            "build_version": "構建版本",
            "support": "由 537工作室 提供支援",
            "copyright": "版權所有 (C) 537工作室. 2023-2024. 保留所有權利.",
            "tip": "呼籲俄烏兩國停戰！ 停止這場無意義的戰爭！",
            "year": "年",
            "month": "月",
            "date": "日",
            "hour": "時",
            "min": "分",
            "sec": "秒",
            "timer_sec": "秒",
            "pausepanel": "暫停面板",
            "pausepanel_line1": "------------",
            "pausepanel_line2": "------------------",
            "pausepanel_line3": "----------------------",
            "timerclear": "計時清零",
            "abouttheprogram": "關於程式",
            "changecolor": "更改顏色",
            "officialwebsite": "官方網站",
            "email": "電子郵件",
            "license": "使用許可",
            "opensourcewebsite": "開源網站",
            "clearscreen": "清空螢幕",
            "continuethetimer": "繼續計時",
            "exit": "退出程式",
            "cancel": "取消",
            "paused": "已暫停",
            "press_key": "按下按鍵",
            "press_key_enable": "按下按鍵以啟用功能",
            "time_clear": "時間已清零，",
            "website_is": "網站位址: ",
            "official_opened": "已打開官方網站，",
            "email_opened": "已打開郵件視窗，",
            "license_opened": "已打開開源協議網站，",
            "select_website": "請選擇要訪問的網站",
            "already_open": "已打開 ",
            "exiting": "正在退出...",
            "press_enter": "按回車鍵以繼續...",
            "press_space": "按空格鍵以繼續...",
            "menu_head": "\n>>-年--月--日----時--分--秒-----\nUnix時間戳-----\n-計時----------------------------",
            "menu_title": "537秒表",
        }
    return {
        "app_name": APP_NAME_L,
        "version": "Version",
        "build_version": "Build Version",
        "support": "Powered by 537 Studio",
        "copyright": "Copyright (C) 537 Studio. 2023-2024. All rights reserved.",
        "tip": "Call for a truce between Russia and Ukraine! Stop this senseless war!",
        "year": ".",
        "month": ".",
        "date": " ",
        "hour": ":",
        "min": ":",
        "sec": "  ",
        "timer_sec": "s",
        "pausepanel": "Pause Panel",
        "pausepanel_line1": "------------",
        "pausepanel_line2": "------------------",
        "pausepanel_line3": "-------------------",
        "timerclear": "Timer Clear",
        "abouttheprogram": "About The Program",
        "changecolor": "Change Color",
        "officialwebsite": "Official Website",
        "email": "E-mail",
        "license": "License",
        "opensourcewebsite": "Open Source Website",
        "clearscreen": "Clear Screen",
        "continuethetimer": "Continue the Timer",
        "exit": "Exit",
        "cancel": "Cancel",
        "paused": "Paused",
        "press_key": "Press the key",
        "press_key_enable": "Press the key to enable the function",
        "time_clear": "Time has been cleared. ",
        "website_is": "The website address: ",
        "official_opened": "The official website has been opened. ",
        "email_opened": "The email window has been opened. ",
        "license_opened": "The open source license website has been opened. ",
        "select_website": "Please select the site you want to visit",
        "already_open": "Already open ",
        "exiting": "Exiting...",
        "press_enter": "Press Enter to continue...",
        "press_space": "Press Space to continue...",
        "menu_head": "\n>>YY-MM-D--------H-MM-S----\nUnix Timestamps---\n-Timer-----------------------------",
        "menu_title": "537 Clock",
    }


TEXT = make_texts(_get_default_language())
LANG = _get_default_language()
TIMER = 0
LAST_UNIXTIME = 0

_STDOUT_HANDLE = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
_WEB_MODE = not getattr(sys.stdin, "isatty", lambda: False)() or not getattr(sys.stdout, "isatty", lambda: False)()
_WEB_INPUTS: deque[str] = deque()
_WEB_INPUT_LOCK = threading.Lock()


def _start_web_input_reader() -> None:
    def reader() -> None:
        for raw in sys.stdin:
            cmd = raw.strip().lower()
            if not cmd:
                continue
            with _WEB_INPUT_LOCK:
                _WEB_INPUTS.append(cmd)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()


def _web_matches(vk: int, cmd: str) -> bool:
    if vk == VK_SPACE:
        return cmd in {"space", "pause", "p"}
    if vk == VK_RETURN:
        return cmd in {"enter", "return", "ok"}
    if vk == VK_ESCAPE:
        return cmd in {"esc", "escape"}
    if 65 <= vk <= 90:
        return cmd == chr(vk).lower()
    if 48 <= vk <= 57:
        return cmd == chr(vk)
    return False


def _web_take(vk: int) -> bool:
    with _WEB_INPUT_LOCK:
        for index, cmd in enumerate(_WEB_INPUTS):
            if _web_matches(vk, cmd):
                del _WEB_INPUTS[index]
                return True
    return False


def set_console_color(color: int) -> None:
    if _WEB_MODE:
        return
    ctypes.windll.kernel32.SetConsoleTextAttribute(_STDOUT_HANDLE, color)


def set_console_title(title: str) -> None:
    if _WEB_MODE:
        return
    ctypes.windll.kernel32.SetConsoleTitleW(title)


def key_down(vk: int) -> bool:
    if _WEB_MODE:
        return _web_take(vk)
    return (ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000) != 0


def wait_key_release(vk: int) -> None:
    if _WEB_MODE:
        return
    while key_down(vk):
        time.sleep(0.01)


def tprint(content, sleep_ms: int = 0, times: int = 1) -> None:
    for _ in range(times):
        sys.stdout.write(str(content))
    try:
        sys.stdout.flush()
    except OSError:
        pass
    if sleep_ms:
        time.sleep(sleep_ms / 1000.0)


def clear_screen() -> None:
    if _WEB_MODE:
        sys.stdout.write("\n")
        sys.stdout.flush()
        return
    os.system("cls")


def tsleep(milliseconds: int) -> None:
    time.sleep(milliseconds / 1000.0)


def menu() -> None:
    set_console_color(FOREGROUND_GREEN | FOREGROUND_INTENSITY)
    tprint(TEXT["menu_head"])


def logo() -> None:
    set_console_color(FOREGROUND_GREEN | FOREGROUND_INTENSITY)
    lines = [
        r"# #     # #    === === ===    /==\  ||          | =",
        r"# # # # # #    |     |   /    |    ====         |",
        "  # ^-^ #      === ===  /     \\==\\  ||  |  |  /=| | /==\\",
        r"# # # # # #      |   | /         |  ||  |  | |  | | |  |",
        r"# #     # #    === === =      \==/  ||  \==/\ \=/\| \==/",
    ]
    for line in lines:
        tprint(line + "\n", 30)


def about() -> None:
    logo()
    tprint("  ", 15)
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY)
    tprint(TEXT["app_name"] + "\t")
    tprint(TEXT["version"] + " ")
    tprint(APP_VERSION + "\t")
    set_console_color(FOREGROUND_BLUE | FOREGROUND_GREEN)
    tprint(TEXT["support"] + "\n")
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
    tprint(TEXT["tip"] + "\n\n")
    set_console_color(FOREGROUND_GREEN | FOREGROUND_INTENSITY)


def press_enter_to_continue() -> None:
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE)
    tprint(TEXT["press_enter"] + "\n")
    while True:
        if key_down(VK_RETURN):
            wait_key_release(VK_RETURN)
            menu()
            return
        tsleep(25)


def waitpress() -> None:
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE)
    tprint("\n>")
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY)
    tprint(APP_NAME_S)
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE)
    tprint(">>")
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
    tprint(TEXT["press_key"])
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE)
    tprint(">>")
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY)


def open_url(url: str) -> None:
    if _WEB_MODE:
        set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
        tprint(f"[web mode] {url}\n")
        return
    webbrowser.open(url, new=1, autoraise=True)


def play_hint() -> None:
    try:
        import winsound

        winsound.Beep(880, 80)
        winsound.Beep(1320, 80)
    except Exception:
        sys.stdout.write("\a")
        sys.stdout.flush()


def control() -> None:
    play_hint()
    tprint("\n\n>>")
    tprint(TEXT["pausepanel"] + "\n")
    tprint(TEXT["pausepanel_line1"] + "\n")
    tprint(TEXT["pausepanel_line2"] + "\n")
    tprint(TEXT["pausepanel_line3"] + "\n")
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE)
    tprint(TEXT["press_key_enable"] + "\n\n")

    menu_items = [
        ("T", TEXT["timerclear"]),
        ("A", TEXT["abouttheprogram"]),
        ("W", TEXT["officialwebsite"]),
        ("E", TEXT["email"]),
        ("L", TEXT["license"]),
        ("O", TEXT["opensourcewebsite"]),
        ("S", TEXT["clearscreen"]),
        ("X", TEXT["continuethetimer"]),
        ("Q", TEXT["exit"]),
    ]
    for key, label in menu_items:
        set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY)
        tprint(f"{key.lower()} ")
        set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
        tprint(label + "\n")

    waitpress()
    while True:
        if key_down(ord("T")):
            wait_key_release(ord("T"))
            play_hint()
            tprint(TEXT["timerclear"] + "\n\n")
            global TIMER
            TIMER = 0
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            tprint(TEXT["time_clear"])
            press_enter_to_continue()
            return
        if key_down(ord("A")):
            wait_key_release(ord("A"))
            play_hint()
            tprint(TEXT["abouttheprogram"] + "\n\n")
            set_console_color(FOREGROUND_GREEN | FOREGROUND_INTENSITY)
            logo()
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY)
            tprint(TEXT["app_name"] + "\n")
            tprint(f"{TEXT['version']} {APP_VERSION}\n")
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN)
            tprint(f"{TEXT['build_version']}: {APP_BUILDVERSION}\n")
            set_console_color(FOREGROUND_GREEN | FOREGROUND_BLUE)
            tprint(TEXT["support"] + "\n")
            set_console_color(FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            tprint(f"{TEXT['website_is']}{APP_WEBSITE}\n")
            set_console_color(FOREGROUND_RED | FOREGROUND_INTENSITY)
            tprint(TEXT["copyright"] + "\n\n")
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            tprint(TEXT["tip"] + "\n\n")
            press_enter_to_continue()
            return
        if key_down(ord("W")):
            wait_key_release(ord("W"))
            tprint(TEXT["officialwebsite"] + "\n\n")
            play_hint()
            open_url(APP_WEBSITE)
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            tprint(TEXT["official_opened"])
            press_enter_to_continue()
            return
        if key_down(ord("E")):
            wait_key_release(ord("E"))
            tprint(TEXT["email"] + "\n\n")
            play_hint()
            open_url("mailto:" + APP_EMAIL)
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            tprint(TEXT["email_opened"])
            press_enter_to_continue()
            return
        if key_down(ord("L")):
            wait_key_release(ord("L"))
            tprint(TEXT["license"] + "\n\n")
            play_hint()
            open_url(APP_OPENSOURCE_ADDRESS_LISENCE)
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            tprint(TEXT["license_opened"])
            press_enter_to_continue()
            return
        if key_down(ord("O")):
            wait_key_release(ord("O"))
            tprint(TEXT["opensourcewebsite"] + "\n\n")
            play_hint()
            tprint(TEXT["select_website"] + "\n")
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY)
            tprint("1\t")
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            tprint("Gitee: ")
            set_console_color(FOREGROUND_GREEN | FOREGROUND_INTENSITY)
            tprint(APP_OPENSOURCE_ADDRESS_GITEE + "\n")
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY)
            tprint("2\t")
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            tprint("GitHub: ")
            set_console_color(FOREGROUND_GREEN | FOREGROUND_INTENSITY)
            tprint(APP_OPENSOURCE_ADDRESS_GITHUB + "\n")
            set_console_color(FOREGROUND_RED | FOREGROUND_INTENSITY)
            tprint("ESC")
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            tprint("\t" + TEXT["cancel"] + "\n")
            waitpress()
            while True:
                if key_down(ord("1")):
                    wait_key_release(ord("1"))
                    tprint("Gitee\n\n")
                    play_hint()
                    open_url(APP_OPENSOURCE_ADDRESS_GITEE)
                    tprint(TEXT["already_open"] + "Gitee\n")
                    press_enter_to_continue()
                    return
                if key_down(ord("2")):
                    wait_key_release(ord("2"))
                    tprint("GitHub\n\n")
                    play_hint()
                    open_url(APP_OPENSOURCE_ADDRESS_GITHUB)
                    tprint(TEXT["already_open"] + "GitHub\n")
                    press_enter_to_continue()
                    return
                if key_down(VK_ESCAPE):
                    wait_key_release(VK_ESCAPE)
                    tprint(TEXT["cancel"] + "\n\n")
                    play_hint()
                    menu()
                    return
                tsleep(25)
        if key_down(ord("S")):
            wait_key_release(ord("S"))
            tprint(TEXT["clearscreen"] + "\n")
            play_hint()
            clear_screen()
            about()
            menu()
            return
        if key_down(ord("X")):
            wait_key_release(ord("X"))
            tprint(TEXT["continuethetimer"] + "\n")
            play_hint()
            menu()
            return
        if key_down(ord("Q")):
            wait_key_release(ord("Q"))
            tprint(TEXT["exit"] + "\n")
            tprint(TEXT["exiting"] + "\n")
            set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
            raise SystemExit(0)
        tsleep(15)


def print_clock_line(now: datetime, timer: int) -> None:
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE)
    tprint("\n")
    tprint(f"{now.year}{TEXT['year']}")
    tprint(f"{now.month}{TEXT['month']}")
    tprint(f"{now.day}{TEXT['date']}\t")
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
    tprint(f"{now.hour}{TEXT['hour']}")
    tprint(f"{now.minute}{TEXT['min']}")
    tprint(f"{now.second}{TEXT['sec']}\t")
    set_console_color(FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_INTENSITY)
    tprint(int(now.timestamp()))
    tprint("\t")
    set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY)
    tprint(f"{timer}{TEXT['timer_sec']}")
    set_console_color(FOREGROUND_GREEN | FOREGROUND_INTENSITY)


def set_language(lan: int) -> None:
    global TEXT, LANG
    LANG = lan
    TEXT = make_texts(lan)


def main(argv: list[str]) -> int:
    _enable_utf8_console()
    if _WEB_MODE:
        _start_web_input_reader()

    lang = _get_default_language()
    want_version = False
    args = [arg.lower() for arg in argv[1:]]
    index = 0
    while index < len(args):
        cmd = args[index]
        if cmd in {"--ver", "--version", "-v"}:
            want_version = True
        elif cmd in {"/lan", "/lang"} and index + 1 < len(argv):
            resolved = _resolve_cli_language(argv[index + 2])
            if resolved is not None:
                lang = resolved
            index += 1
        index += 1

    if want_version:
        set_language(lang)
        set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
        tprint(f"{TEXT['app_name']}\t")
        set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY)
        tprint(f"{TEXT['version']} {APP_VERSION}\t")
        set_console_color(FOREGROUND_BLUE | FOREGROUND_INTENSITY)
        tprint(f"{TEXT['build_version']} {APP_BUILDVERSION}\n")
        return 0

    set_language(lang)
    set_console_title(TEXT["app_name"])
    about()
    menu()
    if _WEB_MODE:
        set_console_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY)
        tprint("Web mode: type `space` to open the control menu, `enter` to continue, `q` to quit.\n\n")

    global LAST_UNIXTIME, TIMER
    now = datetime.now()
    LAST_UNIXTIME = int(now.timestamp())

    while True:
        now = datetime.now()
        current = int(now.timestamp())
        if current != LAST_UNIXTIME:
            TIMER += 1
            print_clock_line(now, TIMER)
            LAST_UNIXTIME = current

        set_console_title(f"{TEXT['app_name']} - {TIMER}{TEXT['timer_sec']}")
        if key_down(VK_SPACE):
            wait_key_release(VK_SPACE)
            set_console_title(f"{TEXT['app_name']} - {TIMER}{TEXT['timer_sec']} {TEXT['paused']}")
            control()
        tsleep(20)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except KeyboardInterrupt:
        raise SystemExit(0)
