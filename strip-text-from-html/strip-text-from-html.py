from os import path
import re

from bs4 import BeautifulSoup

html_filepath = "C:\\Users\\Sean Jackman\\Downloads\\CMV_ Scalping is not immoral for non-critical products and services and provides economic value. _ r_changemyview (6_15_2024 3_01_38 PM).html"
output_folder = "C:\\Users\\Sean Jackman\\Downloads\\"

# Read the HTML file
with open(html_filepath, 'r', encoding='utf-8') as file:
    html_content = file.read()

# Parse HTML to extract text
soup = BeautifulSoup(html_content, 'html.parser')
text_content = soup.get_text()\

# Clean up the text by stripping out line returns and extra spaces
text_content = re.sub(r'\s+', ' ', text_content).strip()

# Split the text content into smaller parts
max_length = 100000  # Adjust based on ChatGPT's limits
text_parts = [text_content[i:i + max_length] for i in range(0, len(text_content), max_length)]

# Save smaller parts to individual text files
for idx, part in enumerate(text_parts):
    with open(path.join(output_folder, f'reddit_part_{idx + 1}.txt'), 'w', encoding='utf-8') as part_file:
        part_file.write(part)

print("The content has been split into smaller parts and saved as text files.")
