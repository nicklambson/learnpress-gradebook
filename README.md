# Overview
 Calculate grades from LearnPress quizzes and assignments. This script intends to overcome limitations with the LearnPress Gradebook plugin UI and csv export, which doesn't even display the scores for all the students enrolled in the class.

 # Prerequisites
 Python 3.6 or higher  
 `pip install pandas`  
 or  
 `pip -r install requirements.txt`

# Tested on
The calculate.py script has been tested using the below versions of software:  
- LearnPress version 4.2.2.4
- LearnPress Assignments version 4.0.4
- LearnPress Gradebook version 4.0.3
- WP phpMyAdmin version 5.2.1.02.


 # Procedure
 1. Enter phpMyAdmin for your WordPress site and Export all the tables as JSON, one file for each table.
 2. Extract the JSON files from the zip archive to a convenient folder.  
 3. Run the calculate.py script.
 4. When prompted, select your folder of JSON files.  

 
 The script will output one CSV file for each course. Each CSV file will be populated with the username of each student who has a score for at least one of the assignments or quizzes. The CSV file headers consist of the names of the assignments and quizzes.




