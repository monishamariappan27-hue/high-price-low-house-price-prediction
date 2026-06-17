import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import time
from datetime import datetime

st.set_page_config(page_title="Placement Prediction", layout="wide")

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")  # shared data folder (one level up)
os.makedirs(DATA, exist_ok=True)

students_path   = os.path.join(DATA, "students.csv")
scores_path     = os.path.join(DATA, "scores.csv")

if not os.path.exists(students_path):
    pd.DataFrame(columns=["student_id","name","email","department","year","password","role"]).to_csv(students_path, index=False)
if not os.path.exists(scores_path):
    pd.DataFrame(columns=["student_id","game","score","total","difficulty","time","date"]).to_csv(scores_path, index=False)

# ── Read CSVs fresh on every page load ────────────────────────────
students   = pd.read_csv(students_path)
scores     = pd.read_csv(scores_path)

# Ensure backward-compatible columns exist
if "role" not in students.columns:
    students["role"] = "student"
if "total" not in scores.columns:
    scores["total"] = 10
if "difficulty" not in scores.columns:
    scores["difficulty"] = "Medium"

# ── Initialize session state ──────────────────────────────────────
if "user" not in st.session_state:
    st.session_state["user"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None

ADMIN_ID = "admin"
ADMIN_PASSWORD = "admin123"

# ── Sidebar ───────────────────────────────────────────────────────
st.sidebar.title("🎓 Placement Prediction")

if st.session_state["user"]:
    if st.session_state["role"] == "admin":
        st.sidebar.success("Logged in as **Admin / Faculty**")
    else:
        matched = students[students["student_id"].astype(str) == str(st.session_state["user"])]
        display_name = matched.iloc[0]["name"] if not matched.empty else st.session_state["user"]
        st.sidebar.success(f"Logged in as **{display_name}**")

    if st.sidebar.button("Logout"):
        st.session_state["user"] = None
        st.session_state["role"] = None
        st.rerun()

if st.session_state["role"] == "admin":
    menu_options = ["Home", "Login", "Admin Dashboard", "Leaderboard", "About"]
else:
    menu_options = ["Home", "Register", "Login", "Games", "Profile", "Results",
                     "Analytics", "Leaderboard", "Placement Prediction", "Students", "About"]

page = st.sidebar.radio("Menu", menu_options)

def require_login():
    if not st.session_state["user"]:
        st.warning("⚠️ Please log in first.")
        st.stop()

def require_admin():
    if st.session_state["role"] != "admin":
        st.warning("⚠️ Admin/Faculty access only.")
        st.stop()

def get_student_test_pct(student_scores, test_keyword):
    """Returns the average percentage for a test type, or None if not taken."""
    rows = student_scores[student_scores["game"].str.contains(test_keyword, case=False, na=False)]
    if rows.empty:
        return None
    pct_values = (rows["score"].astype(float) / rows["total"].replace(0, 10).astype(float)) * 100
    return float(pct_values.mean())

# ══════════════════════════════════════════════════════════════════
if page == "Home":
    st.title("🎓 Placement Prediction")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Students", len(students))
    c2.metric("Games Played", len(scores))
    c3.metric("Average Score", round(scores["score"].mean(), 2) if not scores.empty else 0)
    c4.metric("Highest Score", round(scores["score"].max(), 2) if not scores.empty else 0)

    st.info("Use the sidebar to register, login, play games, view analytics and predict placement.")

elif page == "Register":
    st.header("👤 Student Registration")
    with st.form("reg"):
        sid  = st.text_input("Student ID")
        name = st.text_input("Name")
        email= st.text_input("Email")
        dept = st.text_input("Department")
        year = st.text_input("Year")
        pwd  = st.text_input("Password", type="password")
        if st.form_submit_button("Register"):
            if sid in students["student_id"].astype(str).values:
                st.error("Student ID already exists. Please choose a different one.")
            elif not sid or not name or not pwd:
                st.error("Student ID, Name and Password are required.")
            else:
                row = pd.DataFrame([{
                    "student_id": sid, "name": name, "email": email,
                    "department": dept, "year": year, "password": pwd
                }])
                pd.concat([students, row], ignore_index=True).to_csv(students_path, index=False)
                st.success("✅ Registered successfully! You can now log in.")

elif page == "Login":
    if st.session_state["user"]:
        if st.session_state["role"] == "admin":
            st.success("✅ You are logged in as **Admin / Faculty**.")
        else:
            matched = students[students["student_id"].astype(str) == str(st.session_state["user"])]
            name = matched.iloc[0]["name"] if not matched.empty else st.session_state["user"]
            st.success(f"✅ You are already logged in as **{name}**.")
        st.info("Use the sidebar menu to navigate, or click **Logout** in the sidebar.")
    else:
        st.header("🔐 Login")

        tab_student, tab_admin = st.tabs(["🎓 Student Login", "🛡️ Admin / Faculty Login"])

        with tab_student:
            sid = st.text_input("Student ID", key="login_sid")
            pwd = st.text_input("Password", type="password", key="login_pwd")
            if st.button("Login", key="student_login_btn"):
                students_fresh = pd.read_csv(students_path)
                u = students_fresh[
                    (students_fresh["student_id"].astype(str).str.strip() == str(sid).strip()) &
                    (students_fresh["password"].astype(str).str.strip() == str(pwd).strip())
                ]
                if len(u):
                    st.session_state["user"] = sid
                    st.session_state["role"] = "student"
                    st.rerun()
                else:
                    st.error("❌ Invalid Student ID or Password.")

        with tab_admin:
            aid = st.text_input("Admin ID", key="login_aid")
            apwd = st.text_input("Admin Password", type="password", key="login_apwd")
            if st.button("Login", key="admin_login_btn"):
                if aid.strip() == ADMIN_ID and apwd.strip() == ADMIN_PASSWORD:
                    st.session_state["user"] = ADMIN_ID
                    st.session_state["role"] = "admin"
                    st.rerun()
                else:
                    st.error("❌ Invalid Admin credentials.")

elif page == "Games":
    require_login()
    st.header("🧠 Placement Tests")

    sid = str(st.session_state["user"])

    def save_score(game_name, score_val, total_val, difficulty, time_val):
        row = pd.DataFrame([{
            "student_id": sid,
            "game": game_name,
            "score": score_val,
            "total": total_val,
            "difficulty": difficulty,
            "time": time_val,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        existing = pd.read_csv(scores_path)
        pd.concat([existing, row], ignore_index=True).to_csv(scores_path, index=False)

    # ════════════════════ APTITUDE QUESTION SETS ════════════════════
    APTITUDE_EASY = [
        {"q": "What is 15% of 200?", "opts": ["20", "30", "25", "35"], "a": "30"},
        {"q": "Find the next number: 2, 4, 6, 8, ?", "opts": ["9", "10", "12", "11"], "a": "10"},
        {"q": "If a pen costs ₹10 and a book costs ₹50, what is the total cost of 2 pens and 1 book?", "opts": ["₹60", "₹70", "₹65", "₹75"], "a": "₹70"},
        {"q": "Which word is the odd one out: Apple, Banana, Carrot, Mango?", "opts": ["Apple", "Banana", "Carrot", "Mango"], "a": "Carrot"},
        {"q": "A clock shows 3:00. What angle do the hour and minute hands make?", "opts": ["45°", "90°", "60°", "120°"], "a": "90°"},
        {"q": "If today is Monday, what day will it be after 3 days?", "opts": ["Wednesday", "Thursday", "Friday", "Tuesday"], "a": "Thursday"},
        {"q": "What is the average of 10, 20, and 30?", "opts": ["15", "20", "25", "30"], "a": "20"},
        {"q": "Find the missing number: 5, 10, ?, 20, 25", "opts": ["12", "14", "15", "18"], "a": "15"},
        {"q": "If A=1, B=2, C=3, what does D represent?", "opts": ["4", "5", "3", "2"], "a": "4"},
        {"q": "Which shape has 3 sides?", "opts": ["Square", "Triangle", "Circle", "Pentagon"], "a": "Triangle"},
    ]

    APTITUDE_MEDIUM = [
        {"q": "If a train travels 60 km in 45 minutes, what is its speed in km/h?", "opts": ["75 km/h", "80 km/h", "70 km/h", "90 km/h"], "a": "80 km/h"},
        {"q": "Find the next number in the series: 2, 6, 12, 20, 30, ?", "opts": ["40", "42", "44", "36"], "a": "42"},
        {"q": "A is twice as old as B. 5 years ago, A was 3 times as old as B. What is B's current age?", "opts": ["5", "10", "15", "20"], "a": "10"},
        {"q": "If CODING is written as DPEJOH, how is FLOWER written?", "opts": ["GMPXFS", "GMQXFS", "GNPXFS", "GMPXES"], "a": "GMPXFS"},
        {"q": "A sum of money doubles itself in 8 years at simple interest. What is the rate of interest?", "opts": ["10%", "12.5%", "8%", "15%"], "a": "12.5%"},
        {"q": "Pointing to a photo, Ravi said, 'She is the daughter of my grandfather's only son.' How is the girl related to Ravi?", "opts": ["Sister", "Cousin", "Mother", "Aunt"], "a": "Sister"},
        {"q": "Which number does not belong: 4, 9, 16, 26, 36, 49?", "opts": ["9", "16", "26", "49"], "a": "26"},
        {"q": "If 5 workers can complete a task in 12 days, how many days will 10 workers take?", "opts": ["3 days", "6 days", "12 days", "24 days"], "a": "6 days"},
        {"q": "What is the missing letter pattern: A, C, F, J, ?", "opts": ["N", "O", "M", "P"], "a": "O"},
        {"q": "A shopkeeper sells an item for ₹450 at a 10% profit. What was the cost price?", "opts": ["₹400", "₹405", "₹409", "₹495"], "a": "₹409"},
    ]

    APTITUDE_HARD = [
        {"q": "Two trains start from stations A and B, 300 km apart, towards each other at 50 km/h and 70 km/h. After how many hours do they meet?", "opts": ["2 hours", "2.5 hours", "3 hours", "2.25 hours"], "a": "2.5 hours"},
        {"q": "A can do a piece of work in 12 days, B in 15 days. They work together for 4 days, then A leaves. In how many more days will B finish the remaining work?", "opts": ["6 days", "7 days", "7.4 days", "8 days"], "a": "7.4 days"},
        {"q": "If the radius of a circle is increased by 50%, by what percentage does its area increase?", "opts": ["50%", "100%", "125%", "150%"], "a": "125%"},
        {"q": "In a class, 60% are boys. If 20% of boys and 30% of girls failed, what percentage of the whole class passed?", "opts": ["72%", "74%", "76%", "78%"], "a": "76%"},
        {"q": "A sum becomes ₹2420 in 2 years and ₹2662 in 3 years at compound interest. What is the rate of interest?", "opts": ["8%", "9%", "10%", "12%"], "a": "10%"},
        {"q": "Statement: All cats are animals. Some animals are pets. Conclusion: Some cats are pets. Is this conclusion valid?", "opts": ["Valid", "Invalid — cannot be determined", "Always false", "Always true"], "a": "Invalid — cannot be determined"},
        {"q": "Five friends sit in a row. P is to the right of Q, Q is to the right of R. If R is at position 2, where could P be?", "opts": ["Position 1", "Position 3, 4, or 5", "Position 2", "Cannot be determined"], "a": "Position 3, 4, or 5"},
        {"q": "A boat goes 30 km downstream in 2 hours and returns in 3 hours. What is the speed of the boat in still water?", "opts": ["10 km/h", "11 km/h", "12.5 km/h", "12 km/h"], "a": "12.5 km/h"},
        {"q": "In a code, MONDAY is written as XLMVAZ. How is TUESDAY written using the same logic (reverse alphabet substitution)?", "opts": ["GFVHWXZ", "GFVDHWB", "GFVHDWB", "GVFHDWB"], "a": "GFVHDWB"},
        {"q": "If the probability of an event A is 0.4 and event B is 0.5, and A and B are independent, what is P(A and B)?", "opts": ["0.1", "0.2", "0.45", "0.9"], "a": "0.2"},
    ]

    # ════════════════════ DSA QUESTION SETS ════════════════════
    DSA_EASY = [
        {"q": "Which data structure stores elements in a linear sequence?", "opts": ["Array", "Graph", "Tree", "Hash Map"], "a": "Array"},
        {"q": "What does FIFO stand for?", "opts": ["First In First Out", "First In Final Out", "Fast In Fast Out", "Final In First Out"], "a": "First In First Out"},
        {"q": "Which operation adds an element to the end of a Stack?", "opts": ["Pop", "Push", "Peek", "Enqueue"], "a": "Push"},
        {"q": "What is the index of the first element in most array-based languages?", "opts": ["1", "0", "-1", "Depends"], "a": "0"},
        {"q": "Which of these is a non-linear data structure?", "opts": ["Array", "Stack", "Tree", "Queue"], "a": "Tree"},
        {"q": "Which loop is guaranteed to execute at least once?", "opts": ["for", "while", "do-while", "foreach"], "a": "do-while"},
        {"q": "What is the time complexity of accessing an array element by index?", "opts": ["O(n)", "O(1)", "O(log n)", "O(n^2)"], "a": "O(1)"},
        {"q": "Which keyword is used to define a class in Python?", "opts": ["class", "def", "struct", "object"], "a": "class"},
        {"q": "A Linked List node typically contains data and?", "opts": ["An index", "A pointer/reference to next node", "A key only", "A hash"], "a": "A pointer/reference to next node"},
        {"q": "Which of these is used to remove the top element of a stack?", "opts": ["Push", "Pop", "Peek", "Insert"], "a": "Pop"},
    ]

    DSA_MEDIUM = [
        {"q": "What is the time complexity of binary search?", "opts": ["O(n)", "O(log n)", "O(n log n)", "O(1)"], "a": "O(log n)"},
        {"q": "Which data structure uses LIFO order?", "opts": ["Queue", "Stack", "Array", "Linked List"], "a": "Stack"},
        {"q": "What is the worst-case time complexity of QuickSort?", "opts": ["O(n log n)", "O(n^2)", "O(log n)", "O(n)"], "a": "O(n^2)"},
        {"q": "Which traversal of a Binary Search Tree gives sorted order?", "opts": ["Pre-order", "Post-order", "In-order", "Level-order"], "a": "In-order"},
        {"q": "What does a hash table provide on average for lookup?", "opts": ["O(n)", "O(log n)", "O(1)", "O(n^2)"], "a": "O(1)"},
        {"q": "Which data structure is used for BFS traversal?", "opts": ["Stack", "Queue", "Heap", "Array"], "a": "Queue"},
        {"q": "What is the space complexity of an iterative algorithm using O(1) extra space?", "opts": ["O(1)", "O(n)", "O(log n)", "O(n^2)"], "a": "O(1)"},
        {"q": "Which sorting algorithm is stable and has O(n log n) time complexity?", "opts": ["QuickSort", "Heapsort", "Merge Sort", "Selection Sort"], "a": "Merge Sort"},
        {"q": "A complete binary tree with n nodes has a height of approximately?", "opts": ["O(n)", "O(log n)", "O(n^2)", "O(sqrt n)"], "a": "O(log n)"},
        {"q": "Which data structure is best suited for implementing recursion internally?", "opts": ["Queue", "Stack", "Array", "Graph"], "a": "Stack"},
    ]

    DSA_HARD = [
        {"q": "What is the time complexity of building a heap from n elements?", "opts": ["O(n log n)", "O(n)", "O(log n)", "O(n^2)"], "a": "O(n)"},
        {"q": "In a Trie with average word length L and n words, what is the time complexity of a search operation?", "opts": ["O(n)", "O(L)", "O(n*L)", "O(log n)"], "a": "O(L)"},
        {"q": "Which algorithm finds the shortest path in a graph with negative edge weights but no negative cycles?", "opts": ["Dijkstra's", "Bellman-Ford", "BFS", "Prim's"], "a": "Bellman-Ford"},
        {"q": "What is the amortized time complexity of insertion in a dynamic array (like Python list append)?", "opts": ["O(n)", "O(1)", "O(log n)", "O(n^2)"], "a": "O(1)"},
        {"q": "Which technique is used to solve problems by breaking them into overlapping subproblems and storing results?", "opts": ["Greedy", "Dynamic Programming", "Backtracking", "Divide and Conquer"], "a": "Dynamic Programming"},
        {"q": "What is the time complexity of Floyd-Warshall algorithm for all-pairs shortest paths?", "opts": ["O(V^2)", "O(V^3)", "O(V log V)", "O(E log V)"], "a": "O(V^3)"},
        {"q": "In a balanced AVL tree, what is the maximum difference in height between left and right subtrees of any node?", "opts": ["0", "1", "2", "log n"], "a": "1"},
        {"q": "Which data structure is most efficient for implementing a priority queue?", "opts": ["Array", "Linked List", "Heap", "Stack"], "a": "Heap"},
        {"q": "What is the time complexity of finding strongly connected components using Kosaraju's algorithm?", "opts": ["O(V+E)", "O(V*E)", "O(V^2)", "O(E log V)"], "a": "O(V+E)"},
        {"q": "Which technique does the KMP algorithm use to achieve O(n+m) string matching?", "opts": ["Suffix arrays", "Failure function / prefix table", "Hashing", "Tries"], "a": "Failure function / prefix table"},
    ]

    APTITUDE_SETS = {"Easy": APTITUDE_EASY, "Medium": APTITUDE_MEDIUM, "Hard": APTITUDE_HARD}
    DSA_SETS = {"Easy": DSA_EASY, "Medium": DSA_MEDIUM, "Hard": DSA_HARD}

    def run_quiz(test_name, question_sets, prefix):
        diff_key = f"{prefix}_difficulty"
        idx_key   = f"{prefix}_idx"
        score_key = f"{prefix}_score"
        wrong_key = f"{prefix}_wrong"
        done_key  = f"{prefix}_done"
        start_key = f"{prefix}_start_time"

        if diff_key not in st.session_state:
            st.session_state[diff_key] = None

        if st.session_state[diff_key] is None:
            st.write("**Select Difficulty Level:**")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🟢 Easy", key=f"{prefix}_easy_btn", use_container_width=True):
                    st.session_state[diff_key] = "Easy"
                    st.session_state[idx_key] = 0
                    st.session_state[score_key] = 0
                    st.session_state[wrong_key] = []
                    st.session_state[done_key] = False
                    st.session_state[start_key] = time.time()
                    st.rerun()
            with c2:
                if st.button("🟡 Medium", key=f"{prefix}_medium_btn", use_container_width=True):
                    st.session_state[diff_key] = "Medium"
                    st.session_state[idx_key] = 0
                    st.session_state[score_key] = 0
                    st.session_state[wrong_key] = []
                    st.session_state[done_key] = False
                    st.session_state[start_key] = time.time()
                    st.rerun()
            with c3:
                if st.button("🔴 Hard", key=f"{prefix}_hard_btn", use_container_width=True):
                    st.session_state[diff_key] = "Hard"
                    st.session_state[idx_key] = 0
                    st.session_state[score_key] = 0
                    st.session_state[wrong_key] = []
                    st.session_state[done_key] = False
                    st.session_state[start_key] = time.time()
                    st.rerun()
            return

        difficulty = st.session_state[diff_key]
        questions = question_sets[difficulty]
        total = len(questions)

        st.write(f"**Difficulty:** {difficulty}")
        if st.button("🔄 Restart / Change Difficulty", key=f"{prefix}_reset_btn"):
            st.session_state[diff_key] = None
            st.session_state[idx_key] = 0
            st.session_state[score_key] = 0
            st.session_state[wrong_key] = []
            st.session_state[done_key] = False
            st.rerun()

        if st.session_state[done_key]:
            elapsed = time.time() - st.session_state[start_key]
            pct = st.session_state[score_key] / total * 100
            status = "PASS" if pct >= 50 else "FAIL"
            rating = ("Excellent" if pct >= 90 else "Very Good" if pct >= 75
                      else "Good" if pct >= 60 else "Average" if pct >= 50 else "Needs Improvement")

            st.success(f"**Score:** {st.session_state[score_key]}/{total}  |  "
                       f"**Percentage:** {pct:.1f}%  |  **Status:** {status}  |  "
                       f"**Rating:** {rating}  |  **Time taken:** {elapsed:.1f}s")

            if st.session_state[wrong_key]:
                st.write("**Review — Incorrect Answers:**")
                for qa, ua, ca in st.session_state[wrong_key]:
                    st.write(f"- **{qa}**")
                    st.write(f"   Your answer: *{ua}*  |  Correct answer: *{ca}*")

        elif st.session_state[idx_key] < total:
            q = questions[st.session_state[idx_key]]
            st.progress((st.session_state[idx_key]) / total)
            st.write(f"**Question {st.session_state[idx_key] + 1} of {total}**")
            st.write(f"**{q['q']}**")
            choice = st.radio("Select an answer:", q["opts"], key=f"{prefix}_{difficulty}_q{st.session_state[idx_key]}", index=None)

            if st.button("Submit Answer", key=f"{prefix}_{difficulty}_submit_{st.session_state[idx_key]}"):
                if choice is None:
                    st.warning("Please select an answer.")
                else:
                    if choice == q["a"]:
                        st.session_state[score_key] += 1
                    else:
                        st.session_state[wrong_key].append((q["q"], choice, q["a"]))
                    st.session_state[idx_key] += 1
                    if st.session_state[idx_key] == total:
                        st.session_state[done_key] = True
                        elapsed = time.time() - st.session_state[start_key]
                        save_score(test_name, st.session_state[score_key], total, difficulty, round(elapsed, 2))
                    st.rerun()

    tab1, tab2 = st.tabs(["🧮 Aptitude & Reasoning", "💻 Coding / DSA MCQ"])

    with tab1:
        st.subheader("Aptitude & Logical Reasoning Test")
        st.write("10 questions covering quantitative aptitude, logical reasoning, and verbal ability — common in placement screening rounds.")
        run_quiz("Aptitude Test", APTITUDE_SETS, "apt")

    with tab2:
        st.subheader("Coding / DSA MCQ Test")
        st.write("10 questions covering core Data Structures & Algorithms concepts — frequently asked in technical interviews.")
        run_quiz("DSA Quiz", DSA_SETS, "dsa")


elif page == "Analytics":
    require_login()
    st.header("📊 Analytics")
    if scores.empty:
        st.warning("No scores available yet.")
    else:
        st.write(scores)
        st.subheader("Statistics")
        st.write({
            "Mean":   float(np.mean(scores["score"])),
            "Median": float(np.median(scores["score"])),
            "Std":    float(np.std(scores["score"]))
        })
        fig, ax = plt.subplots()
        ax.hist(scores["score"], bins=8)
        ax.set_title("Score Distribution")
        st.pyplot(fig)

        fig2, ax2 = plt.subplots()
        counts = scores["game"].value_counts()
        ax2.pie(counts.values, labels=counts.index, autopct="%1.1f%%")
        ax2.set_title("Games Played")
        st.pyplot(fig2)

elif page == "Leaderboard":
    st.header("🏆 Leaderboard")
    if scores.empty:
        st.info("No scores yet.")
    else:
        lb = (scores.groupby("student_id")["score"]
              .mean()
              .reset_index()
              .sort_values("score", ascending=False))
        st.dataframe(lb, use_container_width=True)

elif page == "Placement Prediction":
    require_login()
    st.header("🔮 Placement Prediction")

    sid = str(st.session_state["user"])
    matched = students[students["student_id"].astype(str) == sid]
    student_name = matched.iloc[0]["name"] if not matched.empty else sid

    student_scores = scores[scores["student_id"].astype(str) == sid]

    if student_scores.empty:
        st.warning("⚠️ You haven't taken any tests yet. Take the **Aptitude & Reasoning** and "
                    "**Coding/DSA MCQ** tests from the Games page so we can predict your placement chances.")
    else:
        # ── Extract each test's performance ──────────────────────────
        apt_pct = get_student_test_pct(student_scores, "Aptitude")
        dsa_pct = get_student_test_pct(student_scores, "DSA")

        st.subheader(f"Performance Summary — {student_name}")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Aptitude & Reasoning", f"{apt_pct:.1f}%" if apt_pct is not None else "Not taken")
        with c2:
            st.metric("Coding / DSA MCQ", f"{dsa_pct:.1f}%" if dsa_pct is not None else "Not taken")

        # ── Combine into overall score (only available tests count) ──
        available = [p for p in [apt_pct, dsa_pct] if p is not None]

        if len(available) < 1:
            st.warning("⚠️ Take at least one test to get a placement prediction.")
        else:
            overall = sum(available) / len(available)

            st.subheader("Overall Performance Score")
            st.progress(min(max(overall / 100, 0.0), 1.0))
            st.write(f"**{overall:.1f} / 100**")

            # ── Rule-based prediction ────────────────────────────────
            if overall >= 60:
                st.success(f"✅ **PLACED** — Based on your test performance ({overall:.1f}%), "
                            f"you are likely to get placed!")
            else:
                st.error(f"❌ **NOT PLACED** — Based on your test performance ({overall:.1f}%), "
                         f"you need to improve. Keep practicing!")

            # ── Chart ─────────────────────────────────────────────────
            fig, ax = plt.subplots()
            labels = ["Aptitude & Reasoning", "Coding / DSA MCQ"]
            values = [apt_pct or 0, dsa_pct or 0]
            colors = ["#3498db", "#9b59b6"]
            ax.bar(labels, values, color=colors)
            ax.axhline(y=60, color="green", linestyle="--", label="Placement Threshold (60%)")
            ax.set_ylim(0, 100)
            ax.set_ylabel("Score (%)")
            ax.set_title("Your Test Performance")
            ax.legend()
            st.pyplot(fig)

            st.caption("Placement prediction is based on a 60% overall score threshold "
                       "across the Aptitude & Reasoning and Coding/DSA MCQ tests.")

elif page == "Students":
    require_login()
    st.header("📋 Students")
    q  = st.text_input("Search by ID")
    df = students.drop(columns=["password"], errors="ignore")
    if q:
        df = df[df["student_id"].astype(str).str.contains(q, case=False)]
    st.dataframe(df, use_container_width=True)

elif page == "Profile":
    require_login()
    st.header("👤 My Profile")

    sid = str(st.session_state["user"])
    matched = students[students["student_id"].astype(str) == sid]

    if matched.empty:
        st.error("Profile not found.")
    else:
        info = matched.iloc[0]
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Student ID", value=str(info["student_id"]), disabled=True)
            st.text_input("Name", value=str(info["name"]), disabled=True)
            st.text_input("Email", value=str(info.get("email", "")), disabled=True)
        with c2:
            st.text_input("Department", value=str(info.get("department", "")), disabled=True)
            st.text_input("Year", value=str(info.get("year", "")), disabled=True)
            st.text_input("Role", value=str(info.get("role", "student")), disabled=True)

        st.divider()
        st.subheader("📈 Test Activity Summary")

        student_scores = scores[scores["student_id"].astype(str) == sid]
        if student_scores.empty:
            st.info("No tests attempted yet. Head to **Games** to take a test.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tests Attempted", len(student_scores))
            c2.metric("Average Score", f"{student_scores['score'].mean():.1f}")
            c3.metric("Best Score", f"{student_scores['score'].max():.0f}")

            st.write("**Recent Attempts:**")
            st.dataframe(
                student_scores.sort_values("date", ascending=False).head(10),
                use_container_width=True
            )

elif page == "Results":
    require_login()
    st.header("📄 My Results")

    sid = str(st.session_state["user"])
    student_scores = scores[scores["student_id"].astype(str) == sid]

    if student_scores.empty:
        st.info("You haven't taken any tests yet. Go to **Games** to attempt the Aptitude or DSA tests.")
    else:
        for test_name in ["Aptitude Test", "DSA Quiz"]:
            test_rows = student_scores[student_scores["game"] == test_name]
            st.subheader(test_name)

            if test_rows.empty:
                st.write("Not attempted yet.")
                continue

            # Latest attempt
            latest = test_rows.sort_values("date", ascending=False).iloc[0]
            best = test_rows.loc[test_rows["score"].idxmax()]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Latest Score", f"{latest['score']:.0f} / {latest.get('total', 10):.0f}")
            c2.metric("Best Score", f"{best['score']:.0f} / {best.get('total', 10):.0f}")
            c3.metric("Difficulty (Latest)", str(latest.get("difficulty", "Medium")))
            c4.metric("Attempts", len(test_rows))

            with st.expander("View all attempts"):
                st.dataframe(
                    test_rows.sort_values("date", ascending=False)
                    [["difficulty", "score", "total", "time", "date"]],
                    use_container_width=True
                )

            st.divider()

elif page == "Admin Dashboard":
    require_login()
    require_admin()
    st.header("🛡️ Admin / Faculty Dashboard")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Students", len(students))
    c2.metric("Total Test Attempts", len(scores))
    c3.metric("Tests Available", 2)

    st.divider()
    st.subheader("📊 All Students — Placement Prediction Overview")

    overview_rows = []
    for _, srow in students.iterrows():
        sid = str(srow["student_id"])
        s_scores = scores[scores["student_id"].astype(str) == sid]

        apt_pct = get_student_test_pct(s_scores, "Aptitude")
        dsa_pct = get_student_test_pct(s_scores, "DSA")

        available = [p for p in [apt_pct, dsa_pct] if p is not None]
        overall = sum(available) / len(available) if available else None

        if overall is None:
            verdict = "No tests taken"
        elif overall >= 60:
            verdict = "✅ PLACED"
        else:
            verdict = "❌ NOT PLACED"

        overview_rows.append({
            "Student ID": sid,
            "Name": srow.get("name", ""),
            "Department": srow.get("department", ""),
            "Aptitude %": f"{apt_pct:.1f}" if apt_pct is not None else "—",
            "DSA %": f"{dsa_pct:.1f}" if dsa_pct is not None else "—",
            "Overall %": f"{overall:.1f}" if overall is not None else "—",
            "Prediction": verdict,
        })

    overview_df = pd.DataFrame(overview_rows)
    st.dataframe(overview_df, use_container_width=True)

    # Summary chart
    placed_count = sum(1 for r in overview_rows if r["Prediction"] == "✅ PLACED")
    not_placed_count = sum(1 for r in overview_rows if r["Prediction"] == "❌ NOT PLACED")
    no_test_count = sum(1 for r in overview_rows if r["Prediction"] == "No tests taken")

    st.subheader("Placement Distribution")
    fig, ax = plt.subplots()
    ax.bar(["Placed", "Not Placed", "No Tests Taken"],
           [placed_count, not_placed_count, no_test_count],
           color=["#2ecc71", "#e74c3c", "#95a5a6"])
    ax.set_ylabel("Number of Students")
    ax.set_title("Overall Placement Prediction Summary")
    st.pyplot(fig)

    st.divider()
    st.subheader("📋 Raw Test Scores")
    st.dataframe(scores.sort_values("date", ascending=False), use_container_width=True)

elif page == "About":
    st.header("ℹ About")
    st.markdown("""
**Placement Prediction**

Built with:
- Python
- Streamlit
- Pandas
- NumPy
- Matplotlib
- Scikit-learn
- Pygame
""")