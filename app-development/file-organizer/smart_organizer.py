import os
import subprocess
import shutil
import sys
from pathlib import Path

def remove_metadata(input_path, output_path):
    """Removes metadata using exiftool."""
    try:
        subprocess.run(['exiftool', '-all=', '-o', output_path, input_path], 
                       check=True, capture_output=True)
        return True
    except Exception:
        return False

def get_category(filename):
    """Categorizes file based on extension."""
    ext = Path(filename).suffix.lower()
    video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.mpeg', '.mpg', '.m4v'}
    note_exts = {'.txt', '.pdf', '.docx', '.doc', '.md', '.rtf', '.odt', '.csv'}
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}
    
    if ext in video_exts: return 'video'
    if ext in note_exts: return 'note'
    if ext in image_exts: return 'image'
    return 'file'

def main():
    print("==========================================")
    print("      SMART FILE ORGANIZER v1.4")
    print("==========================================")
    
    # Get the folder path
    print("\nSTEP 1: Paste the folder path or drag the folder here.")
    user_input = input("Path: ").strip()
    
    # Clean up quotes from drag-and-drop
    user_input = user_input.replace("'", "").replace('"', "")
    
    target_path = Path(os.path.expanduser(user_input)).resolve()

    if not target_path.is_dir():
        print(f"\nERROR: '{target_path}' is not a valid folder.")
        input("\nPress ENTER to exit...")
        return

    print(f"\nTarget: {target_path}")
    print("------------------------------------------")
    print("This will RENAME, SCRUB METADATA, and DELETE originals.")
    confirm = input("Type 'YES' to confirm: ").strip().upper()
    
    if confirm != "YES":
        print("Aborted.")
        input("\nPress ENTER to exit...")
        return

    output_dir = target_path / "Organized_Cleaned"
    os.makedirs(str(output_dir), exist_ok=True)

    # Gather files
    files = [f for f in target_path.iterdir() if f.is_file()]
    
    # Filter out the program itself if it's in the same folder
    if getattr(sys, 'frozen', False):
        my_name = Path(sys.executable).name
        files = [f for f in files if f.name != my_name]

    if not files:
        print(f"\nNo files found in: {target_path}")
        input("\nPress ENTER to exit...")
        return

    print(f"\nProcessing {len(files)} files...")
    
    counters = {'video': 1, 'note': 1, 'image': 1, 'file': 1}
    count = 0

    for file_path in files:
        cat = get_category(file_path.name)
        new_name = f"{cat} {counters[cat]}{file_path.suffix}"
        new_path = output_dir / new_name
        
        while new_path.exists():
            counters[cat] += 1
            new_name = f"{cat} {counters[cat]}{file_path.suffix}"
            new_path = output_dir / new_name

        print(f" > {file_path.name} -> {new_name}")
        
        # Try metadata removal, fallback to copy
        if not remove_metadata(str(file_path), str(new_path)):
            try:
                shutil.copy(file_path, new_path)
            except Exception as e:
                print(f"   Error: {e}")
                continue

        # Delete original
        try:
            os.remove(file_path)
            counters[cat] += 1
            count += 1
        except Exception as e:
            print(f"   Could not delete original: {e}")

    print(f"\nDONE! {count} files organized in 'Organized_Cleaned'.")
    input("\nPress ENTER to close...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nCritical Error: {e}")
        input("\nPress ENTER to exit...")
