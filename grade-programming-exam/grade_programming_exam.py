# Grade the Advanced Programming I midterm exam

from pathlib import Path
import pandas as pd
from tkinter import filedialog
import openai

advanced_programming_i_midterm_prompt = """Create a tab-delimited table with five columns. The first column has one of the criteria below. The second column has a Chinese translation of the criteria. The third column has an evaluation of how well the code below (denoted as [code] satisfies each row of the rubric on a scale from 1-5. The fourth column is an explanation if the criteria does not score 5. The fifth column has a Chinese translation of the explanation.

Prompts the user to select a folder using filedialog.askdirectory and converts the result to a Path object.
Sets up a tuple for headers for a translate.csv file
Sets up a list of rows for a translate.csv file
Sets up a tuple for headers for a word_count.csv file
Sets up a list of rows for a word_count.csv file
Compiles a regular expression that matches queueDialogue\("(.*?"),"(.*?)"
The regular expression has two capture groups
Each capture group matches any text between double quotes.
Iterates over all *.gml files in the selected folder by using rglob
Reads each file using .read_text()
Specifies the encoding of the file: "utf-8"
Initializes a variable to count all the words in the file
Iterates over matches of the regular expression pattern in the file content
For each match, appends a tuple to the rows to be used for translate.csv.
Each tuple has the text from match group 1 or 2, followed by an empty string, followed by the relative filename.
Adds the word count of each match to the total word count of the file
Appends one tuple per file to the list of tuples to be used for word_count.csv
Each tuple has the five elements: the relative filepath, the filename, the parent filepath, the suffix, and the word count
Prompts the user to select a save as filename for the translate.csv file
Writes the headers and rows of translatable content to translate.csv
Prompts the user to select a save as filename for the word_count.csv file.
Writes the headers and rows of word count information to the word_count.csv file.
The code conforms to PEP8 standards.
"""

MY_FOLDER = Path(filedialog.askdirectory(title="Select directory"))

for student_folder in MY_FOLDER.iterdir():
    student_name = student_folder.name.split("_")[0]
    student_number = student_folder.name.split("_")[-1]
    python_file: Path = student_folder.glob("*.py*")[0]
    code = python_file.read_text(encoding="utf-8")
    prompt = "\n\n".join(advanced_programming_i_midterm_prompt, "[code]", code, "[/code]")
    messages = [ {"role": "system", "content": "You are a university programming teacher, fluent in English and Chinese, and very good at explaining concepts in a simple, basic way."} ]
    messages.append({"role": "user", "content": prompt}) 
    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages) 
    reply = chat.choices[0].message.content
    print(reply)


