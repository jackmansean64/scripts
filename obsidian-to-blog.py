import os
import shutil
import re
import sys

def update_image_links(content, image_folder_name):
    # Regular expression to find Obsidian image links
    pattern = r"!\[\[(.*?)\]\]"
    replacement = r"![image](\1)"

    def replace_func(match):
        image_name = match.group(1)
        # Modify the replacement string to include the image folder
        return replacement.replace("(\1)", f"{image_folder_name}/{image_name}")

    # Replace all occurrences of the pattern with the modified replacement string
    return re.sub(pattern, replace_func, content)

def main(document_name):
    # Environment variables for source and destination folders
    source_folder = os.environ.get('SOURCE_FOLDER')
    destination_folder = os.environ.get('DESTINATION_FOLDER')
    image_folder_name = "images"  # Name of the subfolder for images

    # Paths
    source_file = os.path.join(source_folder, f"{document_name}.md")
    dest_post_folder = os.path.join(destination_folder, "content", "posts", document_name)
    dest_image_folder = os.path.join(dest_post_folder, image_folder_name)

    # Create required directories
    os.makedirs(dest_post_folder, exist_ok=True)
    os.makedirs(dest_image_folder, exist_ok=True)

    # Copy and rename the markdown file
    dest_file = os.path.join(dest_post_folder, "index.md")
    shutil.copy2(source_file, dest_file)

    # Update the content of the markdown file for image links
    with open(dest_file, 'r') as file:
        content = file.read()

    updated_content = update_image_links(content, image_folder_name)

    with open(dest_file, 'w') as file:
        file.write(updated_content)

    # Copy images
    images = re.findall(r"!\[\[(.*?)\]\]", updated_content)
    for image in images:
        source_image_path = os.path.join(source_folder, "Attachments", image)
        dest_image_path = os.path.join(dest_image_folder, image)
        shutil.copy2(source_image_path, dest_image_path)

    print(f"Blog post '{document_name}' has been successfully published.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <document_name>")
        sys.exit(1)

    document_name = sys.argv[1]
    main(document_name)
