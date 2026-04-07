import cv2
import json
import time
from pathlib import Path

SOURCE = "auto"  # "auto" / 0 / 1 / 2 / "http://..."
WINDOW_NAME = "ClubGG Capture"
OUTPUT_DIR = Path("clubgg_captures")
LAYOUT_FILE = Path("clubgg_layout.json")

OUTPUT_DIR.mkdir(exist_ok=True)

drawing = False
start_point = None
end_point = None
current_roi = None
last_frame = None


def load_layout():
    if not LAYOUT_FILE.exists():
        return {}

    try:
        text = LAYOUT_FILE.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        return json.loads(text)
    except Exception:
        return {}


def save_layout(data: dict):
    LAYOUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def normalize_roi(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    return {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}


def open_capture(source):
    if isinstance(source, str) and source not in ("auto",) and not source.isdigit():
        cap = cv2.VideoCapture(source)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                return cap, source
        raise RuntimeError(f"Не удалось открыть поток: {source}")

    if source == "auto":
        candidates = [0, 1, 2, 3, 4]
    else:
        candidates = [int(source)]

    for idx in candidates:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None and frame.size > 0:
                return cap, idx
            cap.release()

    raise RuntimeError("Не удалось найти камеру. Попробуй SOURCE = 0, 1 или 2.")


def mouse_callback(event, x, y, flags, param):
    global drawing, start_point, end_point, current_roi

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_point = (x, y)
        end_point = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        end_point = (x, y)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        end_point = (x, y)
        current_roi = normalize_roi(start_point, end_point)


def draw_overlay(frame):
    preview = frame.copy()

    if current_roi:
        x = current_roi["x"]
        y = current_roi["y"]
        w = current_roi["w"]
        h = current_roi["h"]
        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)

    if drawing and start_point and end_point:
        temp_roi = normalize_roi(start_point, end_point)
        x = temp_roi["x"]
        y = temp_roi["y"]
        w = temp_roi["w"]
        h = temp_roi["h"]
        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 200, 255), 1)

    lines = [
        "Q / ESC - exit",
        "S - save full frame",
        "C - save crop from selected ROI",
        "L - save ROI to clubgg_layout.json",
        "R - reset ROI",
        "Mouse drag - select tables area"
    ]

    y0 = 25
    for line in lines:
        cv2.putText(
            preview,
            line,
            (12, y0),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        y0 += 24

    return preview


def save_full_frame(frame):
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"clubgg_full_{ts}.jpg"
    cv2.imwrite(str(path), frame)
    print(f"[OK] saved full frame -> {path}")


def save_crop(frame, roi):
    if not roi:
        print("[!] Сначала выдели область мышкой")
        return

    x = roi["x"]
    y = roi["y"]
    w = roi["w"]
    h = roi["h"]

    if w <= 0 or h <= 0:
        print("[!] ROI пустой")
        return

    crop = frame[y:y + h, x:x + w]
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"clubgg_crop_{ts}.jpg"
    cv2.imwrite(str(path), crop)
    print(f"[OK] saved crop -> {path}")


def save_roi_to_layout(roi):
    if not roi:
        print("[!] Сначала выдели область мышкой")
        return

    data = load_layout()
    data["tables_roi"] = roi
    save_layout(data)
    print(f"[OK] ROI saved -> {LAYOUT_FILE}")


def main():
    global last_frame, current_roi

    layout = load_layout()
    if "tables_roi" in layout:
        current_roi = layout["tables_roi"]

    cap, used_source = open_capture(SOURCE)
    print(f"[OK] source = {used_source}")

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 1280, 800)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            print("[!] Кадр не получен")
            break

        last_frame = frame
        preview = draw_overlay(frame)
        cv2.imshow(WINDOW_NAME, preview)

        key = cv2.waitKey(1) & 0xFF

        if key in (27, ord("q")):
            break
        elif key == ord("s"):
            save_full_frame(last_frame)
        elif key == ord("c"):
            save_crop(last_frame, current_roi)
        elif key == ord("l"):
            save_roi_to_layout(current_roi)
        elif key == ord("r"):
            current_roi = None
            print("[OK] ROI reset")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()