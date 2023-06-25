import json
import pandas as pd
from pathlib import Path
from tkinter import filedialog, Tk
import re

Tk().withdraw()

pd.set_option('mode.chained_assignment', None)

JSON_FILES = Path(filedialog.askdirectory(title="Select folder of JSON files exported from WordPress"))
tables = dict()

RESULT = JSON_FILES.parent / "RESULT"
RESULT.mkdir(exist_ok=True)

for f in JSON_FILES.glob("*.json"):
    if "gEV" not in f.stem:
        continue
    table_name = re.split("_gEV_", f.stem)[-1]
    with open(f, "r", encoding="utf-8") as json_file:
        json_content = json_file.read()
        json_content = json_content.strip(",")
        tables[table_name] = json.loads(json_content)

# get user id and map it to user_login
users = tables["users"]["data"]
users_df = pd.DataFrame(users)
users_df = users_df.set_index("ID")
user_id_series = users_df["user_login"]

# get sections and sort them by course_id and section order.
sections = tables["learnpress_sections"]["data"]
sections_df = pd.DataFrame(sections)
sections_df = sections_df.set_index("section_id")
sections_df = sections_df.sort_values(by=['section_course_id', 'section_order'])

# get the items in each section, sort them by section_id and item order
# only keep lp_quiz and lp_assignment. Discard lp_lesson.
section_items = tables["learnpress_section_items"]["data"]
section_items_df = pd.DataFrame(section_items)
section_items_df = section_items_df.set_index("section_item_id")
section_items_df = section_items_df.sort_values(by=['section_id', 'item_order'])
section_items_df = section_items_df[section_items_df["item_type"].isin(["lp_quiz", "lp_assignment"])]

# get the user_items
user_items = tables["learnpress_user_items"]["data"]
user_items_df = pd.DataFrame(user_items)
user_items_df = user_items_df.set_index("user_item_id")
user_items_df = user_items_df[user_items_df["status"].isin(["evaluated", "completed"])]

# get the user_item_results
user_item_results = tables["learnpress_user_item_results"]["data"]
user_item_results_df = pd.DataFrame(user_item_results)
user_item_results_df = user_item_results_df.set_index("id")

# get the marks for the assignments
user_itemmeta = tables["learnpress_user_itemmeta"]["data"]
user_itemmeta_df = pd.DataFrame(user_itemmeta)
user_itemmeta_df = user_itemmeta_df[user_itemmeta_df["meta_key"] == "_lp_assignment_mark"]
user_itemmeta_df = user_itemmeta_df.set_index("learnpress_user_item_id")
user_itemmeta_df = user_itemmeta_df[["meta_value"]]

# get the post ids and their titles
posts = tables["posts"]["data"]
posts_df = pd.DataFrame(posts)
posts_df = posts_df.set_index("ID")
posts_series = posts_df["post_title"]

# iterate over each course
for section_course_id, my_sections_df in sections_df.groupby("section_course_id"):

    # sort the sections by section order and get the user_items for all users
    my_sections_df = my_sections_df.sort_values("section_order")
    my_section_items_df = section_items_df[section_items_df["section_id"].isin(my_sections_df.index)]
    my_section_items_df = my_section_items_df.sort_values("item_order")
    my_columns = my_section_items_df["item_id"].to_list()
    my_user_items_df = user_items_df[user_items_df["item_id"].isin(my_columns)]
    
    # for each user get the scores for each quiz and assignment for this course
    all_users_results = list()
    for user_id, each_user_items_df in my_user_items_df.groupby("user_id"):

        # get the quiz results from user_item_results_df if the user_itm_id is in this user's items
        quiz_results = user_item_results_df[user_item_results_df["user_item_id"].isin(each_user_items_df.index)]

        # extract the mark with a regular expression
        quiz_results["user_mark"] = quiz_results["result"].str.extract(pat=r"\"user_mark\":(\d+)")
        quiz_results = quiz_results.set_index("user_item_id")
        quiz_results = quiz_results.drop("result", axis=1)
        quiz_results = quiz_results.drop_duplicates()

        # get the assignment results for this student
        assignment_results = user_itemmeta_df[user_itemmeta_df.index.isin(each_user_items_df.index)]
        assignment_results = assignment_results.rename(columns={"meta_value": "user_mark"})
        assignment_results.index = assignment_results.index.rename("user_item_id")

        # concatenate the quiz and assignment results together
        quiz_and_assignment_results = pd.concat([quiz_results, assignment_results])
        user_all_results = each_user_items_df.join(quiz_and_assignment_results)
        user_all_results = user_all_results[["item_id", "user_mark"]]
        user_all_results = user_all_results.set_index("item_id")
        user_all_results = user_all_results.transpose()
        user_all_results["user_id"] = user_id

        # add an empty cell to the score if there's no score recorded for a particular assignment.
        for item_id in my_columns:
            if item_id not in user_all_results.keys():
                user_all_results[item_id] = None

        # get a dictionary with the score for each assignment and the user_id
        user_all_results = user_all_results.to_dict(orient="index")
        user_all_results = user_all_results["user_mark"]
        all_users_results.append(user_all_results)

    # create a dataframe for all the results for all the users.
    all_users_results_df = pd.DataFrame(all_users_results)
    if all_users_results_df.empty:
        continue

    all_users_results_df = all_users_results_df.set_index("user_id")
    all_users_results_df = all_users_results_df[my_columns]
    # map the id numbers in the column headers and incex to human readable headers and usernames
    all_users_results_df = all_users_results_df.rename(mapper=posts_series, axis=1)
    all_users_results_df = all_users_results_df.rename(mapper=user_id_series, axis=0)

    # get the course name and set it as the result filename for a CSV file.
    course_name = posts_series.get(section_course_id)
    filename = course_name + ".csv"
    print(f"writing grades to {filename}")
    filepath = RESULT / filename
    all_users_results_df.to_csv(filepath, sep="\t", encoding="utf-16")