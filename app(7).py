import json
import os
import sqlite3
from io import BytesIO

import pandas as pd
import streamlit as st
from openai import OpenAI

DB_NAME = "obe_lesson_planner.db"
TEACHING_METHODS = [
    "Interactive Lecture", "Discussion", "Guided Practice", "Think-Pair-Share",
    "Collaborative Learning", "Problem-Based Learning", "Case-Based Learning",
    "Project-Based Learning", "Flipped Learning",
]
ASSESSMENT_METHODS = [
    "Quiz", "Worksheet", "Class Activity", "Presentation", "Written Task",
    "Reflection", "Peer Assessment", "Group Task", "Exit Ticket", "Project",
]

ACTIVITY_OPTIONS = [
    "AI to generate based on my selections",
    "Think-Pair-Share",
    "Small-group discussion",
    "Guided practice",
    "Case-study analysis",
    "Problem-solving task",
    "Collaborative worksheet",
    "Peer review / peer feedback",
    "Individual practice",
    "Mini presentation",
    "Reflection activity",
    "Custom / I will type my own",
]

ASSESSMENT_TASK_OPTIONS = [
    "AI to generate based on my selections",
    "Short quiz",
    "Worksheet / guided task",
    "Exit ticket",
    "Written response",
    "Case/problem solution",
    "Group task output",
    "Mini presentation",
    "Reflection response",
    "Peer-assessment task",
    "Project / product",
    "Custom / I will type my own",
]

SUCCESS_CRITERION_OPTIONS = [
    "AI to generate a measurable criterion",
    "At least 80% of students achieve 70% or above",
    "At least 75% of students meet all task requirements",
    "Students correctly complete at least 4 out of 5 items",
    "Students demonstrate the target skill with at least 70% accuracy",
    "Students meet at least 3 out of 4 rubric criteria",
    "All groups produce an acceptable task outcome",
    "Custom / I will type my own",
]

EVALUATION_OPTIONS = [
    "AI to generate an evaluation/improvement plan",
    "Review assessment results and reteach weak areas",
    "Use exit-ticket evidence to adjust the next lesson",
    "Identify common errors and provide targeted follow-up practice",
    "Compare student performance with the success criterion and revise instruction",
    "Collect student feedback and refine the activity",
    "Provide additional support to students below the success criterion",
    "Custom / I will type my own",
]
BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            programme TEXT NOT NULL,
            course_code TEXT NOT NULL,
            course_title TEXT NOT NULL,
            credit_hours INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS plos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            programme TEXT NOT NULL,
            plo_code TEXT NOT NULL,
            description TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            clo_code TEXT NOT NULL,
            description TEXT NOT NULL,
            bloom_level TEXT NOT NULL,
            plo_id INTEGER,
            FOREIGN KEY (course_id) REFERENCES courses(id),
            FOREIGN KEY (plo_id) REFERENCES plos(id)
        );
        CREATE TABLE IF NOT EXISTS lesson_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            clo_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            duration INTEGER,
            lesson_outcome TEXT NOT NULL,
            teaching_method TEXT,
            activity TEXT,
            assessment_method TEXT,
            assessment_task TEXT,
            success_criterion TEXT,
            evaluation TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id),
            FOREIGN KEY (clo_id) REFERENCES clos(id)
        );
        """)


def rows(query, params=()):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def execute(query, params=()):
    with get_conn() as conn:
        conn.execute(query, params)
        conn.commit()


def get_courses():
    return rows("SELECT * FROM courses ORDER BY programme, course_title")


def get_plos():
    return rows("SELECT * FROM plos ORDER BY programme, plo_code")


def get_clos():
    return rows("""
        SELECT clos.id, clos.course_id, clos.clo_code, clos.description, clos.bloom_level,
               clos.plo_id, courses.course_title, courses.course_code, plos.plo_code
        FROM clos JOIN courses ON clos.course_id = courses.id
        LEFT JOIN plos ON clos.plo_id = plos.id
        ORDER BY courses.course_title, clos.clo_code
    """)


def get_plans():
    return rows("""
        SELECT lesson_plans.*, courses.course_code, courses.course_title,
               clos.clo_code, clos.description AS clo_description, clos.bloom_level
        FROM lesson_plans
        JOIN courses ON lesson_plans.course_id = courses.id
        JOIN clos ON lesson_plans.clo_id = clos.id
        ORDER BY lesson_plans.id DESC
    """)


st.set_page_config(page_title="OBEvolve", page_icon="✨", layout="wide")
create_tables()

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1180px;}
.hero {padding: 2.7rem 2rem; border-radius: 0 0 28px 28px; color: white; text-align:center;
       background: linear-gradient(135deg,#4338ca 0%,#7c3aed 48%,#db2777 100%);
       box-shadow:0 10px 30px rgba(79,70,229,.18); margin-bottom:1.5rem;}
.hero h1 {font-size:2.55rem; margin:.2rem 0;}
.hero h2 {font-size:1.55rem; margin:.25rem 0 .7rem 0;}
.flow {background:linear-gradient(90deg,#f8fafc,#f5f3ff); border:1px solid #ede9fe;
       border-radius:20px; padding:1.2rem; text-align:center; font-weight:700; margin:1rem 0 1.4rem;}
.card {border-radius:18px; padding:1.1rem 1.2rem; border:1px solid #e5e7eb; background:white;
       min-height:170px; box-shadow:0 3px 12px rgba(0,0,0,.04);}
.small {color:#6b7280;}
div[data-testid="stMetric"] {background:#fafafa; border:1px solid #eee; padding:12px; border-radius:14px;}
</style>
""", unsafe_allow_html=True)

PAGES = ["Dashboard", "Course Setup", "PLOs & CLOs", "Lesson Planner", "Saved Plans"]
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

def go_to(page_name):
    st.session_state.page = page_name

with st.sidebar:
    st.title("OBEvolve")
    st.caption("Evolving Outcomes into Learning")
    st.markdown("### Navigate")
    for nav_page in PAGES:
        if st.button(
            nav_page,
            key=f"nav_{nav_page}",
            use_container_width=True,
            type="primary" if st.session_state.page == nav_page else "secondary",
        ):
            st.session_state.page = nav_page
            st.rerun()



def back_to_dashboard():
    """Show a prominent return-to-dashboard control on every non-dashboard page."""
    st.markdown(
        """
        <style>
        div[data-testid="stButton"]:has(button[kind="primary"]) button {
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    left, spacer = st.columns([1.7, 5])
    with left:
        if st.button(
            "🏠  BACK TO DASHBOARD",
            key=f"back_dashboard_{st.session_state.page}",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.page = "Dashboard"
            st.rerun()
    st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)

def dashboard():
    st.markdown("""<div class='hero'><div style='font-size:3rem'>✨</div><h1>OBEvolve</h1>
    <h2>Evolving Outcomes into Learning</h2><p>Transform PLOs and CLOs into meaningful, aligned and measurable classroom experiences.</p></div>""", unsafe_allow_html=True)
    st.header("Build Your OBE Lesson")
    st.write("Follow the OBE journey from programme outcomes to classroom assessment, evaluation and improvement.")
    st.markdown("<div class='flow'>PLO &nbsp; → &nbsp; CLO &nbsp; → &nbsp; Learning Activity &nbsp; → &nbsp; Assessment &nbsp; → &nbsp; Evaluation</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1,"🎓","Course Setup","Create programmes, courses and academic information."),
        (c2,"🌳","PLOs & CLOs","Define outcomes and create meaningful PLO–CLO alignment."),
        (c3,"📝","Lesson Planner","Design constructively aligned teaching, learning and assessment."),
        (c4,"📂","Saved Plans","Access and review previously created lesson plans."),
    ]
    button_labels = {
        "Course Setup": "Open Course Setup",
        "PLOs & CLOs": "Manage Outcomes",
        "Lesson Planner": "Create Lesson Plan",
        "Saved Plans": "View Saved Plans",
    }
    for col, icon, title, text in cards:
        with col:
            st.markdown(f"<div class='card'><div style='font-size:2.2rem'>{icon}</div><h3>{title}</h3><p class='small'>{text}</p></div>", unsafe_allow_html=True)
            if st.button(button_labels[title], key=f"dashboard_{title}", use_container_width=True,
                         type="primary" if title == "Lesson Planner" else "secondary"):
                go_to(title)
                st.rerun()
    st.info("💡 OBE is more than mapping outcomes. Effective lesson planning connects what students should achieve, what they do in class, how learning is assessed, and how teaching is continuously improved.")


def course_setup():
    back_to_dashboard()
    st.header("Course Setup")
    st.write("Create programmes and courses for OBE lesson planning.")
    with st.form("course_form", clear_on_submit=True):
        programme = st.text_input("Programme Name", placeholder="e.g. BS Computer Science")
        code = st.text_input("Course Code", placeholder="e.g. SS1001")
        title = st.text_input("Course Title", placeholder="e.g. Functional English")
        credits = st.number_input("Credit Hours", 1, 6, 3)
        if st.form_submit_button("💾 Save Course", type="primary"):
            if programme and code and title:
                execute("INSERT INTO courses(programme,course_code,course_title,credit_hours) VALUES(?,?,?,?)", (programme, code, title, int(credits)))
                st.success("Course saved successfully!")
            else:
                st.warning("Please complete programme, course code, and course title.")
    courses = get_courses()
    st.subheader("Saved Courses")
    if courses:
        st.dataframe(pd.DataFrame(courses)[["programme","course_code","course_title","credit_hours"]], use_container_width=True, hide_index=True)
    else:
        st.caption("No courses saved yet.")


def outcomes():
    back_to_dashboard()
    st.header("PLOs & CLOs")
    st.write("Define Programme Learning Outcomes, Course Learning Outcomes and their alignment.")
    tab1, tab2 = st.tabs(["Programme Learning Outcomes", "Course Learning Outcomes"])
    with tab1:
        with st.form("plo_form", clear_on_submit=True):
            programme = st.text_input("Programme", placeholder="e.g. BS Computer Science")
            code = st.text_input("PLO Code", placeholder="e.g. PLO 1")
            desc = st.text_area("PLO Description")
            if st.form_submit_button("➕ Add PLO", type="primary"):
                if programme and code and desc:
                    execute("INSERT INTO plos(programme,plo_code,description) VALUES(?,?,?)", (programme, code, desc))
                    st.success("PLO saved successfully!")
                else:
                    st.warning("Please complete all PLO fields.")
        plos = get_plos()
        if plos:
            st.dataframe(pd.DataFrame(plos)[["programme","plo_code","description"]], use_container_width=True, hide_index=True)
    with tab2:
        courses, plos = get_courses(), get_plos()
        if not courses or not plos:
            st.info("Add at least one course and one PLO before creating a CLO.")
        else:
            course_map = {f"{c['course_code']} - {c['course_title']}": c['id'] for c in courses}
            plo_map = {f"{p['plo_code']} - {p['description']}": p['id'] for p in plos}
            with st.form("clo_form", clear_on_submit=True):
                course_label = st.selectbox("Select Course", list(course_map))
                code = st.text_input("CLO Code", placeholder="e.g. CLO 1")
                desc = st.text_area("CLO Description")
                bloom = st.selectbox("Bloom's Taxonomy Level", BLOOM_LEVELS)
                plo_label = st.selectbox("Map CLO to PLO", list(plo_map))
                if st.form_submit_button("➕ Add CLO", type="primary"):
                    if code and desc:
                        execute("INSERT INTO clos(course_id,clo_code,description,bloom_level,plo_id) VALUES(?,?,?,?,?)", (course_map[course_label], code, desc, bloom, plo_map[plo_label]))
                        st.success("CLO saved successfully!")
                    else:
                        st.warning("Please complete CLO code and description.")
        clos = get_clos()
        if clos:
            df = pd.DataFrame(clos).rename(columns={"course_title":"Course","clo_code":"CLO","description":"Description","bloom_level":"Bloom's Level","plo_code":"Mapped PLO"})
            st.dataframe(df[["Course","CLO","Description","Bloom's Level","Mapped PLO"]], use_container_width=True, hide_index=True)


def api_key_value():
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    return os.getenv("OPENAI_API_KEY")


def generate_plan(course, clo, topic, duration, teaching_method, assessment_method,
                  lesson_outcome="", activity="", assessment_task="",
                  success_criterion="", evaluation=""):
    """Generate/refine an OBE-aligned lesson plan from the teacher's selected inputs."""
    prompt = f"""You are an expert university teacher and Outcome-Based Education (OBE) lesson-planning specialist.

Create a practical, constructively aligned university lesson plan using the teacher's choices below.

COURSE: {course['course_code']} - {course['course_title']}
COURSE LEARNING OUTCOME: {clo['clo_code']}: {clo['description']}
BLOOM'S TAXONOMY LEVEL: {clo['bloom_level']}
LESSON TOPIC: {topic}
LESSON DURATION: {duration} minutes
TEACHER-SELECTED TEACHING METHOD: {teaching_method}
TEACHER-SELECTED ASSESSMENT METHOD: {assessment_method}

OPTIONAL TEACHER DRAFTS / PREFERENCES:
Lesson Learning Outcome: {lesson_outcome or 'Not provided'}
Teaching/Learning Activity: {activity or 'Not provided'}
Assessment Task: {assessment_task or 'Not provided'}
Success Criterion: {success_criterion or 'Not provided'}
Evaluation/Improvement Plan: {evaluation or 'Not provided'}

Use this alignment chain:
CLO → Lesson Learning Outcome → Teaching Method → Teaching/Learning Activity → Assessment → Success Criterion → Evaluation/Improvement.

Requirements:
- Preserve the teacher-selected teaching method and assessment method exactly.
- If the teacher supplied draft text, improve and align it rather than ignoring it.
- If a text field is blank, generate an appropriate entry.
- Keep the lesson learning outcome measurable and aligned with the CLO and Bloom's level.
- Make the activity detailed and realistic for the stated duration. Break it into timed lesson stages and clearly describe teacher actions, student actions, resources/materials, and expected student output.
- Make the assessment task directly measure the lesson learning outcome. Explain what students will do, what evidence will be collected, and how it will be judged.
- Give a specific, measurable success criterion with a clear threshold.
- Give a detailed evaluation/improvement plan explaining what evidence the teacher will review, what will count as a weakness, and what instructional adjustment will follow.
- Write sufficiently detailed entries for practical classroom use rather than short labels or one-sentence summaries.
- Return ONLY a valid JSON object with no markdown or commentary.

Use exactly these keys:
{{"lesson_outcome":"","teaching_method":"","activity":"","assessment_method":"","assessment_task":"","success_criterion":"","evaluation":""}}"""

    client = OpenAI(api_key=api_key_value())
    response = client.responses.create(model="gpt-5.6-luna", input=prompt)
    raw = response.output_text.strip().replace("```json", "").replace("```", "").strip()
    first, last = raw.find("{"), raw.rfind("}")
    if first == -1 or last == -1:
        raise ValueError("The AI response did not contain a valid lesson-plan JSON object.")
    plan = json.loads(raw[first:last + 1])
    required = ["lesson_outcome", "teaching_method", "activity", "assessment_method",
                "assessment_task", "success_criterion", "evaluation"]
    missing = [k for k in required if k not in plan]
    if missing:
        raise ValueError("The AI response was incomplete. Missing: " + ", ".join(missing))
    return plan


def lesson_planner():
    back_to_dashboard()
    st.header("OBE Lesson Planner")
    st.write("Choose the lesson requirements first. AI will then generate or refine the complete OBE-aligned lesson plan.")

    courses, clos = get_courses(), get_clos()
    if not courses or not clos:
        st.warning("Please create a course, PLO and CLO first.")
        return

    course_map = {f"{c['course_code']} - {c['course_title']}": c for c in courses}
    course_label = st.selectbox("1. Select Course", list(course_map), key="lp_course")
    course = course_map[course_label]

    filtered = [c for c in clos if c["course_id"] == course["id"]]
    if not filtered:
        st.warning("This course has no CLOs yet.")
        return

    clo_map = {f"{c['clo_code']} - {c['description']} [{c['bloom_level']}]": c for c in filtered}
    clo_label = st.selectbox("2. Select CLO", list(clo_map), key="lp_clo")
    clo = clo_map[clo_label]

    topic = st.text_input("3. Lesson Topic", key="lp_topic", placeholder="e.g. Paraphrasing")
    duration = st.number_input("4. Lesson Duration (minutes)", 10, 360, 60, key="lp_duration")

    st.markdown("### Choose Your Lesson Design")
    st.caption("Select your preferred teaching and assessment approaches. You may also add your own ideas in the text fields, or leave them blank for AI to develop.")

    teaching_method = st.selectbox("5. Teaching Method", TEACHING_METHODS, key="lp_teaching_method_select")
    assessment_method = st.selectbox("6. Assessment Method", ASSESSMENT_METHODS, key="lp_assessment_method_select")

    st.text_area("7. Lesson Learning Outcome (optional draft)", key="lp_lesson_outcome", height=90,
                 placeholder="Write your own outcome, or leave blank for AI.")
    activity_choice = st.selectbox(
        "8. Teaching / Learning Activity",
        ACTIVITY_OPTIONS,
        key="lp_activity_choice",
    )
    if activity_choice == "Custom / I will type my own":
        activity_pref = st.text_area(
            "Your Teaching / Learning Activity",
            key="lp_activity_custom",
            height=100,
            placeholder="Type your activity idea here.",
        )
    elif activity_choice == "AI to generate based on my selections":
        activity_pref = ""
    else:
        activity_pref = activity_choice

    assessment_task_choice = st.selectbox(
        "9. Assessment Task",
        ASSESSMENT_TASK_OPTIONS,
        key="lp_assessment_task_choice",
    )
    if assessment_task_choice == "Custom / I will type my own":
        assessment_task_pref = st.text_area(
            "Your Assessment Task",
            key="lp_assessment_task_custom",
            height=90,
            placeholder="Type your assessment task here.",
        )
    elif assessment_task_choice == "AI to generate based on my selections":
        assessment_task_pref = ""
    else:
        assessment_task_pref = assessment_task_choice

    success_choice = st.selectbox(
        "10. Success Criterion",
        SUCCESS_CRITERION_OPTIONS,
        key="lp_success_criterion_choice",
    )
    if success_choice == "Custom / I will type my own":
        success_pref = st.text_input(
            "Your Success Criterion",
            key="lp_success_criterion_custom",
            placeholder="Type a measurable success criterion.",
        )
    elif success_choice == "AI to generate a measurable criterion":
        success_pref = ""
    else:
        success_pref = success_choice

    evaluation_choice = st.selectbox(
        "11. Evaluation / Improvement Plan",
        EVALUATION_OPTIONS,
        key="lp_evaluation_choice",
    )
    if evaluation_choice == "Custom / I will type my own":
        evaluation_pref = st.text_area(
            "Your Evaluation / Improvement Plan",
            key="lp_evaluation_custom",
            height=90,
            placeholder="Type your evaluation or improvement idea.",
        )
    elif evaluation_choice == "AI to generate an evaluation/improvement plan":
        evaluation_pref = ""
    else:
        evaluation_pref = evaluation_choice

    st.markdown("---")
    if st.button("✨ GENERATE AI-ALIGNED LESSON PLAN", type="primary", use_container_width=True):
        if not topic:
            st.warning("Please enter the lesson topic.")
        elif not api_key_value():
            st.error("OPENAI_API_KEY is not configured. Add it to Streamlit Secrets or your environment variables.")
        else:
            try:
                with st.spinner("Generating your OBE-aligned lesson plan from the selected choices..."):
                    p = generate_plan(
                        course, clo, topic, int(duration),
                        teaching_method, assessment_method,
                        st.session_state.get("lp_lesson_outcome", ""),
                        activity_pref,
                        assessment_task_pref,
                        success_pref,
                        evaluation_pref,
                    )
                # Store AI output separately from teacher-input widget state.
                st.session_state["generated_plan"] = p
                st.session_state["generated_plan_ready"] = True
                st.session_state["generated_course_id"] = course["id"]
                st.session_state["generated_clo_id"] = clo["id"]
                st.session_state["generated_topic"] = topic
                st.session_state["generated_duration"] = int(duration)
                st.session_state["generated_teaching_method"] = teaching_method
                st.session_state["generated_assessment_method"] = assessment_method
                st.rerun()
            except Exception as e:
                st.error(f"AI generation error: {e}")

    # Show AI output only after the Generate button has completed successfully.
    if st.session_state.get("generated_plan_ready") and st.session_state.get("generated_plan"):
        p = st.session_state["generated_plan"]

        st.success("✨ AI lesson plan generated successfully from the teacher's choices.")
        st.markdown("### Generated Lesson Plan — Detailed Table")
        st.caption("This table appears only after generation and summarizes the complete OBE-aligned lesson plan.")

        table_rows = [
            ("Course", f"{course['course_code']} - {course['course_title']}"),
            ("Course Learning Outcome (CLO)", f"{clo['clo_code']}: {clo['description']}"),
            ("Bloom's Taxonomy Level", clo['bloom_level']),
            ("Lesson Topic", topic),
            ("Duration", f"{int(duration)} minutes"),
            ("Lesson Learning Outcome", p.get("lesson_outcome", "")),
            ("Teaching Method", teaching_method),
            ("Teaching / Learning Activity", p.get("activity", "")),
            ("Assessment Method", assessment_method),
            ("Assessment Task", p.get("assessment_task", "")),
            ("Success Criterion", p.get("success_criterion", "")),
            ("Evaluation / Improvement Plan", p.get("evaluation", "")),
        ]

        import html
        rows_html = "".join(
            f"<tr><td class='component'>{html.escape(str(component))}</td>"
            f"<td class='detail'>{html.escape(str(detail)).replace(chr(10), '<br>')}</td></tr>"
            for component, detail in table_rows
        )

        st.markdown(
            f"""
            <style>
            .lesson-table-wrap {{
                width: 100%;
                overflow: visible;
                margin: 0.5rem 0 1.5rem 0;
            }}
            .lesson-table {{
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
                font-size: 1rem;
                line-height: 1.55;
            }}
            .lesson-table th {{
                background: #f3f4f6;
                padding: 14px 16px;
                border: 1px solid #d1d5db;
                text-align: left;
                font-weight: 700;
            }}
            .lesson-table td {{
                padding: 14px 16px;
                border: 1px solid #d1d5db;
                vertical-align: top;
                white-space: normal !important;
                overflow-wrap: anywhere;
                word-break: normal;
            }}
            .lesson-table .component {{
                width: 24%;
                font-weight: 650;
                background: #fafafa;
            }}
            .lesson-table .detail {{
                width: 76%;
            }}
            </style>
            <div class="lesson-table-wrap">
                <table class="lesson-table">
                    <thead>
                        <tr>
                            <th style="width:24%">Lesson Plan Component</th>
                            <th style="width:76%">Detailed Plan</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Review & Finalize")
        c1, c2 = st.columns(2)

        with c1:
            if st.button("✅ Check OBE Alignment", use_container_width=True):
                fields = [
                    p.get("lesson_outcome"),
                    p.get("activity"),
                    p.get("assessment_task"),
                    p.get("success_criterion"),
                    p.get("evaluation"),
                ]
                score = sum(bool(x and str(x).strip()) for x in fields) * 20
                st.metric("Alignment Score", f"{score}%")
                if score >= 80:
                    st.success("This lesson demonstrates strong structural OBE alignment.")
                elif score >= 60:
                    st.warning("The lesson is partially aligned. Some elements should be strengthened.")
                else:
                    st.error("The lesson requires further OBE alignment.")
                st.caption("This is a completeness-based alignment check, not a substitute for academic review.")

        with c2:
            if st.button("💾 Save Lesson Plan", use_container_width=True):
                outcome = p.get("lesson_outcome", "").strip()
                if not topic or not outcome:
                    st.warning("A lesson topic and generated learning outcome are required.")
                else:
                    execute("""INSERT INTO lesson_plans(course_id,clo_id,topic,duration,lesson_outcome,teaching_method,activity,assessment_method,assessment_task,success_criterion,evaluation)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (course['id'], clo['id'], topic, int(duration), outcome,
                             teaching_method, p.get("activity", ""),
                             assessment_method, p.get("assessment_task", ""),
                             p.get("success_criterion", ""), p.get("evaluation", "")))
                    st.success("Lesson plan saved successfully!")


def saved_plans():
    back_to_dashboard()
    st.header("Saved Lesson Plans")
    plans = get_plans()
    if not plans:
        st.info("No lesson plans have been saved yet.")
        return
    for p in plans:
        with st.expander(f"{p['topic']} — {p['course_code']} {p['course_title']}", expanded=False):
            st.markdown(f"**CLO:** {p['clo_code']} [{p['bloom_level']}]  \n**Duration:** {p['duration'] or '-'} minutes  \n**Teaching Method:** {p['teaching_method'] or '-'}  \n**Assessment Method:** {p['assessment_method'] or '-'}")
            st.markdown("**Lesson Learning Outcome**")
            st.write(p['lesson_outcome'] or '-')
            st.markdown("**Teaching / Learning Activity**")
            st.write(p['activity'] or '-')
            st.markdown("**Assessment Task**")
            st.write(p['assessment_task'] or '-')
            st.markdown("**Success Criterion**")
            st.write(p['success_criterion'] or '-')
            st.markdown("**Evaluation / Improvement Plan**")
            st.write(p['evaluation'] or '-')
            if st.button("🗑️ Delete", key=f"del_{p['id']}"):
                execute("DELETE FROM lesson_plans WHERE id=?", (p['id'],))
                st.rerun()


page = st.session_state.page

if page == "Dashboard":
    dashboard()
elif page == "Course Setup":
    course_setup()
elif page == "PLOs & CLOs":
    outcomes()
elif page == "Lesson Planner":
    lesson_planner()
elif page == "Saved Plans":
    saved_plans()
