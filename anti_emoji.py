import os
import re

def remove_emojis_from_text(text: str) -> str:
    # Covers most emojis, symbols, and pictographs
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & pictographs
        "\U0001F680-\U0001F6FF"  # Transport & map symbols
        "\U0001F700-\U0001F77F"  # Alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric shapes extended
        "\U0001F800-\U0001F8FF"  # Supplemental arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental symbols & pictographs
        "\U0001FA00-\U0001FA6F"  # Chess symbols, etc.
        "\U0001FA70-\U0001FAFF"  # Symbols & pictographs extended-A
        "\U00002700-\U000027BF"  # Dingbats
        "\U00002600-\U000026FF"  # Misc symbols
        "\U00002B00-\U00002BFF"  # Misc symbols and arrows
        "\U00002300-\U000023FF"  # Misc technical
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)


def clean_directory_of_emojis(directory: str):
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)

            try:
                # Read file as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Remove emojis
                cleaned_content = remove_emojis_from_text(content)

                # Only overwrite if changes are made
                if cleaned_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned_content)
                    print(f"Cleaned emojis from: {file_path}")

            except UnicodeDecodeError:
                # Skip binary files
                print(f"Skipped (binary or non-text): {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    target_dir = input("Enter the directory path to clean emojis from: ").strip()
    if os.path.isdir(target_dir):
        clean_directory_of_emojis(target_dir)
        print("Emoji removal complete.")
    else:
        print("Invalid directory path.")
