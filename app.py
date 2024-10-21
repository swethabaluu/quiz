import streamlit as st
import random
import pandas as pd
import time
from pymongo import MongoClient
from googletrans import Translator
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# MongoDB Connection (Replace with your MongoDB Atlas URI)
client = MongoClient("your_mongodb_atlas_uri")
db = client['quiz_app']

# Initialize session state for user login
if 'user' not in st.session_state:
    st.session_state.user = None
if 'score' not in st.session_state:
    st.session_state.score = 0

# Email function
def send_email(recipient, score):
    msg = MIMEText(f"Your final score is {score}!")
    msg["Subject"] = "Quiz Results"
    msg["From"] = "youremail@example.com"
    msg["To"] = recipient
    with smtplib.SMTP("smtp.example.com", 587) as server:
        server.starttls()
        server.login("youremail@example.com", "yourpassword")
        server.sendmail(msg["From"], recipient, msg.as_string())

# Function to authenticate users
def login():
    st.session_state.user = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = db['users'].find_one({"username": st.session_state.user, "password": password})
        if user:
            st.session_state.user = user['username']
            st.success(f"Welcome {st.session_state.user}!")
        else:
            st.error("Invalid username or password")

# Function to register a new user
def register():
    username = st.text_input("New Username")
    password = st.text_input("New Password", type="password")
    if st.button("Register"):
        if db['users'].find_one({"username": username}):
            st.error("Username already exists!")
        else:
            db['users'].insert_one({"username": username, "password": password})
            st.success("Registration successful!")

# Function to add new questions (Admin Panel)
def add_question():
    if st.session_state.user == "admin":  # Only allow admin to add questions
        question = st.text_input("Enter the question:")
        options = st.text_area("Enter options (comma-separated):").split(",")
        answer = st.text_input("Enter the correct answer:")
        explanation = st.text_area("Enter an explanation:")
        category = st.selectbox("Select category:", ["General", "Science", "History", "Math"])
        difficulty = st.selectbox("Select difficulty:", ["Easy", "Medium", "Hard"])

        if st.button("Submit Question"):
            db['questions'].insert_one({
                "question": question,
                "options": options,
                "answer": answer,
                "explanation": explanation,
                "category": category,
                "difficulty": difficulty
            })
            st.success("Question added!")

# Function to get questions from the database
def get_questions(category, difficulty):
    questions = list(db['questions'].find({"category": category, "difficulty": difficulty}))
    random.shuffle(questions)  # Randomize question order
    return questions

# Quiz timer
def start_timer():
    time_left = 10  # Set time per question
    for t in range(time_left, 0, -1):
        st.write(f"Time left: {t} seconds")
        time.sleep(1)

# Multilingual support
def translate_text(text, lang="en"):
    translator = Translator()
    return translator.translate(text, dest=lang).text

# Main function
def main():
    st.title("Interactive Quiz App")

    # Login / Registration
    menu = ["Login", "Register"]
    choice = st.sidebar.selectbox("Select an option", menu)

    if choice == "Login":
        login()
    else:
        register()

    # Once logged in
    if st.session_state.user:
        st.sidebar.write(f"Logged in as: {st.session_state.user}")
        
        # Admin Panel to add questions
        if st.session_state.user == "admin":
            add_question()
        
        # Category and Difficulty Selection
        category = st.selectbox("Select category:", ["General", "Science", "History", "Math"])
        difficulty = st.selectbox("Select difficulty:", ["Easy", "Medium", "Hard"])
        
        # Start quiz
        if st.button("Start Quiz"):
            questions = get_questions(category, difficulty)
            total_questions = len(questions)
            score = 0
            progress = st.progress(0)

            for i, question_data in enumerate(questions):
                question = question_data["question"]
                options = random.sample(question_data["options"], len(question_data["options"]))  # Randomize options
                
                # Show question and options
                st.subheader(translate_text(question))
                for idx, option in enumerate(options):
                    st.radio(f"Option {idx + 1}: {option}", options=options, key=f"q{idx}")

                # Timer for each question
                start_timer()

                # Check answer
                selected_answer = st.radio("Select answer", options)
                if selected_answer == question_data["answer"]:
                    score += 1
                
                # Progress bar
                progress.progress((i + 1) / total_questions)

            # Final score and email notification
            st.write(f"Your final score is {score}/{total_questions}")
            send_email(st.session_state.user, score)

            # Feedback section
            user_feedback = st.text_area("Your feedback:")
            if st.button("Submit Feedback"):
                db['feedback'].insert_one({"username": st.session_state.user, "feedback": user_feedback})
                st.success("Thank you for your feedback!")

            # Leaderboard
            leaderboard = db['leaderboard'].find().sort("score", -1).limit(5)
            st.subheader("Leaderboard")
            for record in leaderboard:
                st.write(f"{record['username']} - {record['score']}")

            # Export Results
            if st.button("Export Results to CSV"):
                results = pd.DataFrame([{"question": q["question"], "selected_answer": selected_answer} for q in questions])
                results.to_csv("quiz_results.csv", index=False)
                st.success("Results exported!")

# Run the app
if __name__ == '__main__':
    main()
