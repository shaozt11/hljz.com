from __future__ import annotations

import sys
import time
from pathlib import Path


NULL_TOKEN = "@[Editor_NULLinput]_Replace_NULLinput_[SrcInfoOfEditor]"
LOCK_CAN_TYPEWRITE = "@Editor_REwrite[locked]@CanTypewrite"
LOCK_CAN_NOT_TYPEWRITE = "@Editor_REwrite[locked]@CanNotTypewrite"
LOCK_TIP_TEXT = "@Editor_REwrite[locked]@TipText"


def read_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return text.splitlines()


def write_lines(path: Path, lines: list[str]) -> None:
    text = "\n".join(lines)
    if lines:
        text += "\n"
    path.write_text(text, encoding="utf-8")


def edit_write_mode() -> None:
    print("Message: Edit Mode (Write)")
    print("Message: Type '/help' for help.")
    print("Message: Type '/exit' to exit.")

    text_lines: list[str] = []
    up_line_count = 0

    while True:
        up_line_count += 1
        print(f"[{up_line_count}]>>", end="", flush=True)
        try:
            input_text = input()
        except EOFError:
            input_text = NULL_TOKEN

        low = input_text.lower()
        if low == "/help":
            print("Message: Edit Mode (Write) Help")
            print("Message: Type '/help' for help.")
            print("Message: Type '/exit' to exit.")
            print("Message: Type '/clear' to clear the text.")
            print("Tip: '[Up_LineCount]>>' means the current line number.")
        elif low == "/exit":
            print("Message: Starting to save the text.")
            print("Step1:Select the save mode.")
            print("1:Save to file.")
            print("2:Output to console.")
            print("3:New file and save to it.")
            print("4:Append to file.")
            print("5:Cancel.")
            save_mode_raw = input("Input the number:")
            try:
                save_mode = int(save_mode_raw)
            except Exception:
                print("Message: Invalid input. Defaulting to output to console.")
                save_mode = 2

            output_text = "\n".join(text_lines)
            if text_lines:
                output_text += "\n"

            if save_mode == 1:
                print("Step2:Input the file path.")
                file_path = input().strip()
                if file_path and not Path(file_path).exists():
                    print("Message: File not created. Want to create it?[Y/N]")
                    create_file = input("Input the Y/N:").strip().lower()
                    if create_file == "y":
                        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                        Path(file_path).touch()
                    elif create_file in ("n", ""):
                        print("Message: Text not saved.")

                if file_path and Path(file_path).exists():
                    try:
                        Path(file_path).write_text(output_text, encoding="utf-8")
                    except Exception as ex:
                        print(f"Message: Error saving file. {ex}")
                        print("Message: Text not saved.")
                else:
                    print("Message: Invalid file path. Text not saved.")
            elif save_mode == 2:
                print("Message: Outputting text to console.")
                print(output_text, end="")
            elif save_mode == 3:
                print("Step2:Input the new file path.")
                new_file_path = input().strip()
                if new_file_path:
                    try:
                        Path(new_file_path).parent.mkdir(parents=True, exist_ok=True)
                        Path(new_file_path).write_text(output_text, encoding="utf-8")
                    except Exception as ex:
                        print(f"Message: Error saving file. {ex}")
                        print("Message: Text not saved.")
                else:
                    print("Message: Invalid file path. Text not saved.")
            elif save_mode == 4:
                print("Step2:Input the file path to append.")
                append_file_path = input().strip()
                if append_file_path and Path(append_file_path).exists():
                    try:
                        with Path(append_file_path).open("a", encoding="utf-8") as f:
                            f.write(output_text)
                    except Exception as ex:
                        print(f"Message: Error saving file. {ex}")
                        print("Message: Text not saved.")
                else:
                    print("Message: Invalid file path. Text not saved.")
            elif save_mode == 5:
                print("Message: Cancelled. Text not saved.")
            return
        elif low == "/clear":
            text_lines.clear()
            print("Message: Text cleared.")
        elif input_text.startswith(NULL_TOKEN):
            text_lines.append("")
        else:
            text_lines.append(input_text)


def edit_read_write_mode(path: Path) -> None:
    if not path.exists():
        print("Message: Invalid file path.")
        return

    print("Message: Edit Mode (Read-Write)")
    print("Message: Type '/help' for help.")
    print("Message: Type '/exit' to exit.")

    raw_text = path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()
    line_count = len(lines)
    check_lock = lines[0] if lines else ""

    if check_lock.startswith(LOCK_CAN_TYPEWRITE):
        print("Message: The file is locked. Do you want to read the text? (Y/N)")
        read_choice = input().strip().lower() or "y"
        if read_choice == "y":
            print("Message: The text is:")
            print(raw_text[len(LOCK_CAN_TYPEWRITE):], end="")
        else:
            print("Message: Exiting without reading.")
        print("Message: Press any key to exit.")
        input()
        return

    if check_lock.startswith(LOCK_CAN_NOT_TYPEWRITE):
        print("Message: The file is locked and cannot be edited. You can not read the text. Press any key to exit.")
        input()
        return

    if check_lock.startswith(LOCK_TIP_TEXT):
        print("Message: The file is locked. The text is:")
        print(check_lock[len(LOCK_TIP_TEXT):])
        print("Message: Press any key to exit.")
        input()
        return

    text_lines: list[str] = []
    into_line_count = 0
    print_org = False

    if lines:
        print(lines[0] + "\n")

    up_line_count = 0
    while True:
        up_line_count += 1
        if print_org:
            if into_line_count < len(lines):
                up_line_count -= 1
                print(lines[into_line_count])
            print_org = False

        print(f"[{up_line_count}|{line_count}|{into_line_count}]>>", end="", flush=True)
        try:
            input_text = input()
        except EOFError:
            input_text = NULL_TOKEN

        low = input_text.lower()
        if low == "/help":
            print("Message: Edit Mode (Read-Write) Help")
            print("Message: Type '/help' for help.")
            print("Message: Type '/exit' to exit.")
            print("Message: Type '/clear' to clear the text.")
            print("Message: Type '/wexit' to exit and save the text.")
            print("Message: Type '/lockcre' to lock the file and save the text and exit. (The file will be locked and can not be edited, but can be read.)")
            print("Message: Type '/lockno' to lock the file and save the text and exit. (The file will be locked and can not be edited, and can not be read.)")
            print("Message: Type '/lockwt' to lock the file with a tip and save the text and exit. (The file will be locked and can not be edited, and can not be read. The tip will be shown at the beginning of the text.)")
            print("Tip: '[Up_LineCount|LineCount|intoLineCount]>>' means the current line number, total line number and the line number that has been read into the text.")
            print("About Lock: Locking the file will add a lock tag at the beginning of the file. The lock tag can be '@Editor_REwrite[locked]@CanTypewrite' or '@Editor_REwrite[locked]@CanNotTypewrite'. The former means the file is locked but can be read, while the latter means the file is locked and cannot be read.")
            print("About Lock with Tip: Locking the file with a tip will add a lock tag with a tip at the beginning of the file. The lock tag can be '@Editor_REwrite[locked]@TipText' followed by the tip text. The former means the file is locked and cannot be read, but the tip will be shown at the beginning of the text.")
            print('About "[{Up_LineCount}|{LineCount}|{intoLineCount}]>>" in the console: \'Up_LineCount\' => \'Updated line count\'.')
            print("Message: Press any key to continue.")
            input()
            continue
        elif low == "/exit":
            print("Message:Do you want to save the text? (Y/N)")
            save_choice = input().strip().lower() or "y"
            if save_choice == "y":
                if into_line_count > len(lines):
                    print("Message: No more lines to read. Saving the text.")
                else:
                    for i in range(into_line_count, len(lines)):
                        text_lines.append(lines[i])
                write_lines(path, text_lines)
            else:
                print("Message: Exiting without saving.")
            return
        elif low == "/wexit":
            if into_line_count > len(lines):
                print("Message: No more lines to read. Saving the text.")
            else:
                for i in range(into_line_count, len(lines)):
                    text_lines.append(lines[i])
            write_lines(path, text_lines)
            return
        elif low == "/clear":
            text_lines.clear()
            print("Message: Text cleared.")
            into_line_count = 0
        elif low == "/lockcre":
            text_lines.insert(0, LOCK_CAN_TYPEWRITE)
            for i in range(into_line_count, len(lines)):
                text_lines.append(lines[i])
            write_lines(path, text_lines)
            print("Message: File locked and saved. Exiting.")
            return
        elif low == "/lockno":
            text_lines.insert(0, LOCK_CAN_NOT_TYPEWRITE)
            for i in range(into_line_count, len(lines)):
                text_lines.append(lines[i])
            write_lines(path, text_lines)
            print("Message: File locked and saved. Exiting.")
            return
        elif low == "/lockwt":
            print("Message: Please enter the tip text:")
            tip_text = input().strip() or "This file is locked."
            text_lines.insert(0, LOCK_TIP_TEXT + tip_text)
            for i in range(into_line_count, len(lines)):
                text_lines.append(lines[i])
            write_lines(path, text_lines)
            print("Message: File locked with tip and saved. Exiting.")
            return
        elif not input_text or input_text.startswith(NULL_TOKEN):
            if into_line_count < len(lines):
                text_lines.append(lines[into_line_count])
                print_org = True
                into_line_count += 1
                continue
            else:
                into_line_count += 1
                text_lines.append("")
        else:
            into_line_count += 1
            text_lines.append(input_text)


def type_mode(path: Path, typewrite: bool = False) -> None:
    if not path.exists():
        print("Message: File not found.Starting write mode (no file loaded).")
        edit_write_mode()
        return

    line_count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line_count += 1
            if typewrite:
                time.sleep(0.005)
            print(line.rstrip("\n"))
    print("All lines read: " + str(line_count))


def main(argv: list[str]) -> int:
    if len(argv) >= 1 and argv[0]:
        if argv[0] == "/help":
            print("Useage:")
            print(" [this program] - EditWriteMode")
            print(" [this program] <file path> - EditReadAndWriteMode")
            print(" [this program] <file path> /type - TypeMode")
            print(" [this program] <file path> /type /typewrite - TypeWriteMode")
            print(" [this program] /help - Show this help message")
            return 0
        elif argv[0] == "/type" and len(argv) >= 2 and argv[1]:
            if argv[1] == "/help":
                print("Useage:")
                print(" [this program] /type <file path> - TypeMode")
                print(" [this program] /type <file path> /typewrite - TypeWriteMode")
                print(" [this program] /type /help - Show this help message")
                return 0
            type_mode(Path(argv[1]), len(argv) >= 3 and argv[2] == "/typewrite")
            return 0
        elif Path(argv[0]).exists():
            edit_read_write_mode(Path(argv[0]))
            return 0

    edit_write_mode()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
