import os


def crawl_directory(root_folder):
    items = []

    # Get immediate subdirectories and files
    for item in os.listdir(root_folder):
        item_path = os.path.join(root_folder, item)
        relative_path = os.path.relpath(item_path, root_folder)
        items.append(relative_path)

    return items


def main():
    # Get the folder path from user input
    folder_path = input("Enter the folder path to crawl: ")

    # Check if the folder exists
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    # Crawl the directory and get the list of items
    item_list = crawl_directory(folder_path)

    # Create the output file path
    output_file = os.path.join(folder_path, "directory_contents.txt")

    # Write the list of items to the output file
    with open(output_file, "w") as f:
        for item in item_list:
            f.write(f"{item}\n")
        f.write(f"\nTotal items: {len(item_list)}")

    print(f"Results have been written to: {output_file}")


if __name__ == "__main__":
    main()
