from pathlib import Path
from tkinter import Tk, filedialog
from nltk.tokenize import sent_tokenize, word_tokenize
import spacy
from cefrpy import CEFRSpaCyAnalyzer
import openai
import json
import matplotlib.pyplot as plt
from scipy.stats import linregress
import numpy as np
import config
from rich import print
import streamlit as st
import plotly.graph_objects as go
import os

nlp = spacy.load("en_core_web_sm")
CLIENT = openai.OpenAI(api_key="abc123")

def interpolate_score(value, x1, y1, x2, y2):
    return y1 + (value - x1) * (y2 - y1) / (x2 - x1)

def get_response_format(filepath):
        return json.loads(Path(filepath).read_text(encoding="utf-8"))

class Essay:
    ABBREVIATION_MAPPING = {
        "'m": "am", "'s": "is", "'re": "are", "'ve": "have", "'d": "had", "n't": "not", "'ll": "will"
    }
    ENTITY_TYPES_TO_SKIP_CEFR = {'QUANTITY', 'MONEY', 'LANGUAGE', 'LAW', 'WORK_OF_ART', 'PRODUCT', 'GPE', 'ORG', 'FAC', 'PERSON'}

    def __init__(self, student_name, essay_number, text: None, revised_text: None, errors: None, raw_coherence_score):
        self.student_name = student_name
        self.essay_number = essay_number
        self.id = student_name + "_" + essay_number
        self.text = text
        self.revised_text = revised_text

        # Dimension 1: Appropriate length
        self.total_word_count = None
        self.average_word_count = None
        self.deviation = None
        self.total_word_count_score = None
        
        # Dimension 2: Vocabulary range
        self.cefr_word_counts = {}
        self.wordy_penalty = None
        self.b2_count = None
        self.c1c2_count = None
        self.vocabulary_range_score = None

         # Dimension 3: Accuracy
        self.errors = errors
        self.error_penalty = None
        self.accuracy_score = None
        if self.errors:
            self.accuracy_score = self.get_accuracy_score()

        # Dimension 4: Coherence and cohesion
        self.raw_coherence_score = raw_coherence_score
        self.coherence_score = None
        if self.raw_coherence_score:
            self.coherence_score = self.get_coherence_score(self.raw_coherence_score)

        # Dimension 5: Mr. Lambson's score
        self.teacher_score = None  
        
        # Composite
        self.composite_score = None

    # ------------- word count score ------------------------------------------#

    def get_word_counts(self):
        sentences = sent_tokenize(self.text)
        total_word_count = sum(len([word for word in word_tokenize(sentence)]) for sentence in sentences)
        average_word_count = total_word_count / len(sentences) if sentences else 0
        word_counts = [len(word_tokenize(sentence)) for sentence in sentences]
        deviation = max(word_counts) - min(word_counts) if word_counts else 0
        self.total_word_count = total_word_count
        self.average_word_count = average_word_count
        self.deviation = deviation

    def get_total_word_count_score(self):
        total_word_count_score = None
        if 200 <= self.total_word_count <= 300:
            total_word_count_score = 100
        elif self.total_word_count < 200:
            total_word_count_score = interpolate_score(self.total_word_count, 150, 80, 200, 100)
        elif self.total_word_count > 300:
            total_word_count_score = interpolate_score(self.total_word_count, 300, 100, 350, 90)
        return total_word_count_score

    #--------------- vocabulary range score --------------------------------#

    def get_cefr_word_counts(self):
        doc = nlp(self.text)
        text_analyzer = CEFRSpaCyAnalyzer(entity_types_to_skip=self.ENTITY_TYPES_TO_SKIP_CEFR, abbreviation_mapping=self.ABBREVIATION_MAPPING)
        tokens = text_analyzer.analyze_doc(doc)
        
        processed_word_pos_set = set()
        difficulty_levels_count = [0] * 6
        
        for token in tokens:
            level = token[3]
            if not level:
                continue
            to_check_tuple = (token[0], token[1])
            if to_check_tuple not in processed_word_pos_set:
                level_round = round(level)
                difficulty_levels_count[level_round - 1] += 1
                processed_word_pos_set.add(to_check_tuple)
        
        self.cefr_word_counts = {f'CEFRLevel_{i}': count for i, count in enumerate(difficulty_levels_count, start=1)}
        self.cefr_word_counts['cefr_total_word_count'] = sum(difficulty_levels_count)

    def get_vocabulary_range_score(self):
        a1_ratio = self.cefr_word_counts.get('CEFRLevel_1', 0) / self.total_word_count
        a2_ratio = self.cefr_word_counts.get('CEFRLevel_2', 0) / self.total_word_count
        b1_ratio = self.cefr_word_counts.get('CEFRLevel_3', 0) / self.total_word_count

        self.wordy_penalty = (a1_ratio * 0.5) + (a2_ratio * 0.325) + (b1_ratio * 0.175)
        self.b2_count = self.cefr_word_counts.get('CEFRLevel_4', 0)
        self.c1c2_count = self.cefr_word_counts.get('CEFRLevel_5', 0) + self.cefr_word_counts.get('CEFRLevel_6', 0)

        self.conciseness_score = min(interpolate_score(self.wordy_penalty, 0.18, 100, 0.24, 70), 100)
        self.b2_score = min(interpolate_score(self.b2_count, 4, 70, 13, 100), 100)
        self.c1c2_score = min(interpolate_score(self.c1c2_count, 1, 70, 10, 100), 100)
        return self.conciseness_score * .2 + self.b2_score * .35 + self.c1c2_score * .45
    
    # ------------------- Cohesion Score --------------------------------------------#

    def check_coherence(self):
        print(f"Checking coherence score for {self.id}...")
        messages = [{"role": "system", "content": config.check_coherence_system_prompt}, {"role": "user", "content": self.text}]
        completion = CLIENT.chat.completions.create(model="gpt-4.1-mini", messages=messages)
        response = json.loads(completion.choices[0].message.content)
        self.raw_coherence_score = int(response)
        self.coherence_score = self.get_coherence_score(self.raw_coherence_score)

    def get_coherence_score(self, raw_coherence_score):
        return min(interpolate_score(raw_coherence_score, 95, 100, 71, 80), 100)
    
     #------------- Accuracy Score ------------------------------------------------------------#

    def check_errors(self):
        response_format_filepath = Path(__file__).parent / "error_check_response_format.json"
        response_format = get_response_format(response_format_filepath)
        messages = [{"role": "system", "content": config.check_errors_system_prompt}, {"role": "user", "content": self.text}]
        completion = CLIENT.chat.completions.create(model="gpt-4.1-mini", messages=messages, response_format=response_format)
        response = json.loads(completion.choices[0].message.content)
        self.errors = response["errors"]

    def get_accuracy_score(self):
        severity_penalty = {'major': 2, 'minor': 1, 'neutral': 0.5}
        error_penalty =  sum(severity_penalty.get(error.get('severity', ''), 0) for error in self.errors)
        return min(interpolate_score(error_penalty, 0, 100, 36, 70), 100)
    
    def process_essay(self):
        print(f"Starting the processing of essay {self.essay_number} for student {self.student_name}.")
        
        # Dimension 1: Appropriate length
        self.get_word_counts()
        self.total_word_count_score = self.get_total_word_count_score()

        # Dimension 2: Vocabulary range
        self.get_cefr_word_counts()
        self.vocabulary_range_score = self.get_vocabulary_range_score()
        
        # Dimension 3: Accuracy
        if not self.errors:
            print(f"Checking errors using gpt for {self.id}...")
            self.check_errors()
        self.accuracy_score = self.get_accuracy_score()

        # Dimension 4: Coherence and cohesion
        if not self.raw_coherence_score:
            print(f"Checking coherence using gpt for {self.id}...")
            self.check_coherence()
        self.coherence_score = self.get_coherence_score(self.raw_coherence_score)
        
        # Dimension 5: Mr. Lambson's score
        self.teacher_score = np.mean([self.total_word_count_score, self.vocabulary_range_score, self.accuracy_score, self.coherence_score])

        self.composite_score = (
            self.total_word_count_score * 0.15 +
            self.vocabulary_range_score * 0.25 +
            self.accuracy_score * 0.25 +
            self.coherence_score * 0.15 +
            self.teacher_score * 0.20
        )

    def generate_radar_chart(self):
        categories = ['Total Word Count', 'Vocabulary Range', 'Accuracy', 'Coherence', 'Teacher']
        scores = [
            self.total_word_count_score,
            self.vocabulary_range_score,
            self.accuracy_score,
            self.coherence_score,
            self.teacher_score
        ]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=categories,
            fill='toself'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[65, 100]
                )),
            showlegend=False
        )
        return fig
    
    def display_scale(self):
        color = 'red'
        if self.composite_score > 90:
            color = 'green'
        elif self.composite_score > 80:
            color = 'yellow'
        elif self.composite_score > 70:
            color = 'orange'
        st.markdown(f"<div style='width: 100%; height: 30px; background-color: {color}; text-align: center;'>{self.composite_score}</div>", unsafe_allow_html=True)
        
        
class EssayGrader:
    def __init__(self):
        self.essays = []
        self.folder_path = None
        self.json_path = None

    def plot_metrics(self, metric_name, title, ylabel, color):
        essay_names = [essay.essay_id for essay in self.essays]
        metrics = [getattr(essay, metric_name) for essay in self.essays]
        plt.figure(figsize=(10, 6))
        plt.bar(essay_names, metrics, color=color)
        plt.xlabel('Essay Name')
        plt.ylabel(ylabel)
        plt.title(title)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()

    def plot_score_dimensions(self):
        essay_names = [essay.id for essay in self.essays]
        
        score_dimensions = {key: [getattr(essay, key) for essay in self.essays] for key in 
                            ['final_score', 'x_score', 'y_score', 'slope_score', 'error_penalty', 'kudos_score']}

        x = np.arange(len(essay_names))
        width = 0.1  # Width of each bar

        plt.figure(figsize=(14, 8))
        
        for i, (label, scores) in enumerate(score_dimensions.items()):
            plt.bar(x + i * width, scores, width=width, label=label)
        
        plt.xlabel('Essay Names')
        plt.ylabel('Scores')
        plt.title('Score Dimensions for Each Essay')
        plt.xticks(x + width * (len(score_dimensions) - 1) / 2, essay_names, rotation=45, ha='right')
        plt.ylim(60, 100)
        plt.yticks(np.arange(60, 101, 5))  # Add horizontal grid lines every 5 points
        plt.grid(axis='y', linestyle='--', linewidth=0.7)
        plt.legend(title='Score Dimension')
        plt.tight_layout()
        plt.show()

    def print_reports(self, essay1: Essay, essay2: Essay):
       

        st.title(essay1.student_name)

        col1, col2 = st.columns(2)

        if essay1:
            essay1: Essay
            with col1:
                st.plotly_chart(essay1.generate_radar_chart())
                st.write(essay1.text)
                st.write(essay1.revised_text)
                st.table(essay1.errors)
                essay1.display_scale()

        if essay2:
            essay2: Essay
            with col2:
                st.plotly_chart(essay2.generate_radar_chart())
                st.write(essay2.text)
                st.write(essay2.revised_text)
                st.table(essay2.errors)
                essay2.display_scale()

        if essay1 and essay2:
            average_score = (essay1.composite_score + essay2.composite_score) / 2
            st.markdown(f"<h2 style='text-align: center;'>Average Score: {average_score}</h2>", unsafe_allow_html=True)

    def plot_histograms(self):
        values_to_plot = [
                        #   'error_penalty', 
                        #   'coherence_score', 
                        #   'total_word_count', 
                        #   'average_word_count', 
                        #   'deviation', 
                        #   'wordy_penalty', 
                        #   'b2_count', 
                        #   'c1c2_count',
                        #   'total_word_count',
                        #   'accuracy_score',
                        #   'coherence_score'
                        #   'vocabulary_range_score',
                        #   'total_word_count_score'
                            'composite_score'
                          ]
        
        for value in values_to_plot:
            data = [getattr(essay, value) for essay in self.essays if getattr(essay, value) is not None]
            plt.figure(figsize=(10, 6))
            plt.hist(data, bins=10, edgecolor='black')
            plt.xlabel(f'{value.replace("_", " ").title()}')
            plt.ylabel('Frequency')
            plt.title(f'Distribution of {value.replace("_", " ").title()}')
            plt.grid(axis='y', linestyle='--', linewidth=0.7)
            plt.tight_layout()
            plt.show()
        
    def load_existing_results(self):
        input_file_path = Path(filedialog.askopenfilename(title="Select JSON file", filetypes=[("JSON files", "*.json")], initialdir=Path(__file__).parent.parent, initialfile='result.json'))
        with open(input_file_path, 'r', encoding='utf-8') as json_file:
            saved_results = json.load(json_file)
            for data in saved_results:
                student_name = data.get('student_name', '')
                essay_number = data.get('essay_number', '')
                text = data.get('text', '')
                revised_text = data.get('revised_text', '')
                errors = data.get('errors', [])
                raw_coherence_score = data.get('raw_coherence_score', '')
                essay = Essay(student_name, essay_number, text, revised_text, errors, raw_coherence_score)
                essay.process_essay()
                self.essays.append(essay)
        self.save_results()

    def read_folder_contents(self):
        folder_path = Path(filedialog.askdirectory(title="Choose folder"))
        for file_path in folder_path.glob('*.txt'):
            student_name, essay_number = file_path.stem.split('_')
            text = file_path.read_text(encoding="utf-8")
            essay = Essay(student_name, essay_number, text, None, None)
            essay.process_essay()
            self.essays.append(essay)
        self.save_results()

    def save_results(self):
        output_file_path = Path(filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], title="Choose output JSON file"))
        results = [vars(essay) for essay in self.essays]
        with open(output_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(results, json_file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    grader = EssayGrader()
    grader.load_existing_results()
    # grader.plot_histograms()
    harriet1, harriet2 = [essay for essay in grader.essays if essay.student_name == "Harriet"]

    grader.print_reports(harriet1, harriet2)
