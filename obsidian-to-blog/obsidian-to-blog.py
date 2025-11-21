from __future__ import annotations
import os
import shutil
import re
import sys
from dotenv import load_dotenv
import datetime


def _main(document_name):
    load_dotenv()
    source_folder = os.getenv('OBSIDIAN_SOURCE_FOLDER')
    destination_folder = os.getenv('BLOG_DESTINATION_FOLDER')
    image_folder_name = "images"

    source_file = find_file_by_name_or_alias(document_name, source_folder)
    if not source_file:
        print(f"Error: Markdown file with name or alias '{document_name}' not found.")
        return

    folder_name = _determine_destination_folder_name(source_file, document_name, destination_folder)
    dest_post_folder = os.path.join(destination_folder, folder_name)
    dest_image_folder = os.path.join(dest_post_folder, image_folder_name)

    os.makedirs(dest_post_folder, exist_ok=True)
    os.makedirs(dest_image_folder, exist_ok=True)

    dest_file = os.path.join(dest_post_folder, "index.md")
    shutil.copy2(source_file, dest_file)

    with open(dest_file, 'r', encoding="utf-8") as file:
        content = file.read()

    clear_directory(dest_image_folder)
    images = re.findall(r"!\[\[(.*?)]]", content)

    for image_name in images:
        source_image_path = find_file(image_name, source_folder)
        sanitized_image_name = _sanitize_filename(image_name)
        dest_image_path = os.path.join(dest_image_folder, sanitized_image_name)

        if source_image_path:
            shutil.copy2(source_image_path, dest_image_path)
        else:
            print(f"Warning: Image {image_name} not found in Attachments.")

    updated_content = _update_image_links(content, image_folder_name)
    updated_content = _convert_internal_header_refs(updated_content)

    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    updated_content = _update_front_matter(updated_content, current_date)

    with open(dest_file, 'w', encoding="utf-8") as file:
        file.write(updated_content)

    print(f"Blog post '{folder_name}' has been successfully published to the blog repo.")


def find_file(filename, root_folder):
    for subdir, dirs, files in os.walk(root_folder):
        for file in files:
            if file == filename:
                return os.path.join(subdir, file)
    return None


def _extract_aliases_from_front_matter(file_path):
    """
    Extract aliases from the YAML front matter of a markdown file.
    Returns a list of aliases, or empty list if none found.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            return []

        front_matter = fm_match.group(1)

        aliases = []
        alias_match = re.search(r'^aliases:\s*\n((?:  - .+\n?)+)', front_matter, re.MULTILINE)
        if alias_match:
            alias_lines = alias_match.group(1).strip().split('\n')
            aliases = [line.strip().lstrip('- ').strip() for line in alias_lines]
        else:
            single_match = re.search(r'^aliases:\s*(.+)$', front_matter, re.MULTILINE)
            if single_match:
                aliases = [single_match.group(1).strip()]

        return aliases
    except Exception:
        return []


def _extract_title_from_front_matter(file_path):
    """
    Extract the title from the YAML front matter of a markdown file.
    Returns the title string or None if not found.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            return None

        front_matter = fm_match.group(1)

        title_match = re.search(r'^title:\s*(.+)$', front_matter, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()

        return None
    except Exception:
        return None


def _determine_destination_folder_name(source_file, document_name, destination_folder):
    """
    Determine the destination folder name by:
    1. Checking if a folder with the file's title already exists
    2. If yes, use that title
    3. If no, use the document_name (which could be an alias)
    """
    title = _extract_title_from_front_matter(source_file)

    if title:
        title_folder = os.path.join(destination_folder, title)
        if os.path.exists(title_folder) and os.path.isdir(title_folder):
            return title

    return document_name


def find_file_by_name_or_alias(document_name, root_folder):
    """
    Find a markdown file by its filename (without .md) or by matching an alias
    in its front matter.
    """
    filename = f"{document_name}.md"

    for subdir, dirs, files in os.walk(root_folder):
        for file in files:
            if file == filename:
                return os.path.join(subdir, file)

    for subdir, dirs, files in os.walk(root_folder):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(subdir, file)
                aliases = _extract_aliases_from_front_matter(file_path)
                if document_name in aliases:
                    return file_path

    return None


def clear_directory(directory_path):
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")


def _update_image_links(content, image_folder_name):
    pattern = r"!\[\[(.*?)\]\]"

    def replace_func(match):
        image_name = match.group(1)
        sanitized_image_name = _sanitize_filename(image_name)
        return f'![image]({image_folder_name}/{sanitized_image_name})'

    return re.sub(pattern, replace_func, content)


def _sanitize_filename(filename):
    return filename.replace(" ", "_")


def _update_front_matter(content, current_date):
    front_matter_pattern = r'^(---\s+.*?\s+---)'
    if front_matter := re.search(front_matter_pattern, content, re.DOTALL):
        fm = front_matter.group(1)
        updated_fm = re.sub(r'(\s+---)$', f'\nlastmod: {current_date}\\1', fm)
        content = content.replace(fm, updated_fm)
    return content


def _convert_internal_header_refs(content: str) -> str:
    """
    Convert Obsidian-style internal header links [[#This Header]]
    into Markdown links [This Header](#this-header).
    """
    pattern = r"\[\[#([^\]]+)\]\]"

    def repl(m):
        header_text = m.group(1).strip()
        slug = _slugify_header(header_text)
        return f"[{header_text}](#{slug})"

    return re.sub(pattern, repl, content)


def _slugify_header(text: str) -> str:
    """
    Create an anchor slug similar to GitHub/Hugo style:
    - lowercase
    - remove punctuation except spaces and hyphens
    - collapse whitespace to hyphens
    - collapse repeated hyphens
    - trim leading/trailing hyphens
    """
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)      # drop punctuation
    s = re.sub(r"\s+", "-", s)          # spaces -> hyphens
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <document_name>")
        sys.exit(1)

    document_name = sys.argv[1]
    _main(document_name)
