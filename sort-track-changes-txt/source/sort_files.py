import json
import csv
from pathlib import Path
from tkinter import Tk, filedialog

def select_folder():
    root = Tk()
    root.withdraw()  # Hide the root window
    folder_selected = filedialog.askdirectory()
    return Path(folder_selected) if folder_selected else None

def process_files(folder: Path):
    json_content = []
    same_content = []

    for f_path in folder.rglob('*.txt'):
        if not f_path.stem.endswith('_reviewed'):
            f_reviewed_path = f_path.with_stem(f_path.stem + '_reviewed')

            if f_reviewed_path.exists():
                content_f = f_path.read_text(encoding='utf-8')
                content_f_reviewed = f_reviewed_path.read_text(encoding='utf-8')

                if content_f == content_f_reviewed:
                    same_content.append(content_f)
                else:
                    json_content.append({
                        "messages": [
                            {"role": "system", "content": "Revise the content."},
                            {"role": "user", "content": content_f},
                            {"role": "assistant", "content": content_f_reviewed}
                        ]
                    })

    return json_content, same_content

def save_to_files(json_content, same_content):
    with Path('training_data.json').open('w', encoding='utf-8') as json_file:
        json.dump(json_content, json_file, ensure_ascii=False, indent=4)

    with Path('same_content.csv').open('w', encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        for content in same_content:
            writer.writerow([content])

if __name__ == "__main__":
    folder = select_folder()
    if folder:
        json_content, same_content = process_files(folder)
        save_to_files(json_content, same_content)
        print("Processing complete. Files saved as 'training_data.json' and 'same_content.csv'.")
    else:
        print("No folder selected.")