import json
from pathlib import Path
import cv2

CAPTURE_DIR = Path("clubgg_captures")
LAYOUT_FILE = Path("clubgg_layout.json")


def load_layout():
    if not LAYOUT_FILE.exists():
        return {}
    try:
        return json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))
    except:
        return {}


def latest_crop():
    files = sorted(
        CAPTURE_DIR.glob("clubgg_crop_*.jpg"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return files[0] if files else None


def get_table_rows(img):
    h, w = img.shape[:2]

    # Оставляем только нижнюю часть, где реально идут столы
    y1 = int(h * 0.48)
    y2 = int(h * 0.98)

    rows = 3
    work_h = y2 - y1
    row_h = work_h // rows

    boxes = []
    for i in range(rows):
        ry1 = y1 + i * row_h
        ry2 = y2 if i == rows - 1 else y1 + (i + 1) * row_h
        boxes.append((0, ry1, w, ry2))

    return boxes


def draw_row_guides(img):
    out = img.copy()
    for i, (x1, y1, x2, y2) in enumerate(get_table_rows(img), start=1):
        cv2.rectangle(out, (x1, y1), (x2 - 1, y2 - 1), (0, 255, 0), 2)
        cv2.putText(
            out,
            f"TABLE {i}",
            (12, y1 + 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )
    return out


def split_row_zones(row_img):
    h, w = row_img.shape[:2]

    x_game_1 = 0
    x_game_2 = int(w * 0.02)

    x_players_1 = int(w * 0.03)
    x_players_2 = int(w * 0.07)

    x_name_1 = int(w * 0.07)
    x_name_2 = int(w * 0.20)

    x_buyin_1 = int(w * 0.43)
    x_buyin_2 = int(w * 0.57)

    x_tags_1 = int(w * 0.57)
    x_tags_2 = w

    return {
        "game": row_img[:, x_game_1:x_game_2],
        "players": row_img[:, x_players_1:x_players_2],
        "name_blinds": row_img[:, x_name_1:x_name_2],
        "buyin": row_img[:, x_buyin_1:x_buyin_2],
        "tags": row_img[:, x_tags_1:x_tags_2],
    }


def draw_zone_preview(row_img):
    out = row_img.copy()
    h, w = out.shape[:2]

    cuts = [
        int(w * 0.09),
        int(w * 0.22),
        int(w * 0.63),
        int(w * 0.82),
    ]

    labels = [
        ("GAME", 8),
        ("PLAYERS", int(w * 0.09) + 8),
        ("NAME/BLINDS", int(w * 0.22) + 8),
        ("BUYIN", int(w * 0.63) + 8),
        ("TAGS", int(w * 0.82) + 8),
    ]

    for x in cuts:
        cv2.line(out, (x, 0), (x, h - 1), (0, 255, 255), 2)

    for text, x in labels:
        cv2.putText(
            out,
            text,
            (x, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
            cv2.LINE_AA
        )

    cv2.rectangle(out, (0, 0), (w - 1, h - 1), (0, 255, 0), 2)
    return out


def main():
    crop_path = latest_crop()
    if not crop_path:
        print("Нет crop файла в папке clubgg_captures")
        return

    img = cv2.imread(str(crop_path))
    if img is None:
        print("Не удалось открыть crop")
        return

    rows_preview = draw_row_guides(img)
    rows_preview_path = CAPTURE_DIR / "clubgg_rows_preview.jpg"
    cv2.imwrite(str(rows_preview_path), rows_preview)

    row_boxes = get_table_rows(img)

    for i, (x1, y1, x2, y2) in enumerate(row_boxes, start=1):
        row_img = img[y1:y2, x1:x2]

        row_path = CAPTURE_DIR / f"clubgg_row_{i}.jpg"
        cv2.imwrite(str(row_path), row_img)

        zone_preview = draw_zone_preview(row_img)
        zone_preview_path = CAPTURE_DIR / f"clubgg_row_{i}_zones.jpg"
        cv2.imwrite(str(zone_preview_path), zone_preview)

        zones = split_row_zones(row_img)
        for zone_name, zone_img in zones.items():
            zone_path = CAPTURE_DIR / f"clubgg_row_{i}_{zone_name}.jpg"
            cv2.imwrite(str(zone_path), zone_img)

    print(f"[OK] latest crop: {crop_path}")
    print(f"[OK] rows preview: {rows_preview_path}")
    print("[OK] row images and zone images saved")


if __name__ == "__main__":
    main()