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
- Make the activity realistic for the stated duration and clearly describe teacher and student actions.
- Make the assessment task directly measure the lesson learning outcome.
- Give a measurable success criterion.
- Give a concise evaluation/improvement plan.
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
    st.text_area("8. Teaching / Learning Activity (optional idea)", key="lp_activity", height=130,
                 placeholder="Add your activity idea, or leave blank for AI.")
    st.text_area("9. Assessment Task (optional idea)", key="lp_assessment_task", height=100,
                 placeholder="Add your assessment task, or leave blank for AI.")
    st.text_input("10. Success Criterion (optional)", key="lp_success_criterion",
                  placeholder="e.g. 80% of students achieve at least 70%, or leave blank for AI.")
    st.text_area("11. Evaluation / Improvement Plan (optional)", key="lp_evaluation", height=100,
                 placeholder="Add your improvement idea, or leave blank for AI.")

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
                        st.session_state.get("lp_activity", ""),
                        st.session_state.get("lp_assessment_task", ""),
                        st.session_state.get("lp_success_criterion", ""),
                        st.session_state.get("lp_evaluation", ""),
                    )
                # Keep the teacher's two dropdown choices; populate/refine the text fields.
                for key in ["lesson_outcome", "activity", "assessment_task", "success_criterion", "evaluation"]:
                    st.session_state[f"lp_{key}"] = p.get(key, "")
                st.success("✨ AI lesson plan generated from your choices. Review the completed fields below, then check alignment and save.")
                st.rerun()
            except Exception as e:
                st.error(f"AI generation error: {e}")

    st.markdown("### Generated Lesson Plan — Detailed Table")
    st.caption("The table below summarizes the complete OBE-aligned lesson plan using the teacher's selections and the AI-developed details.")

    if st.session_state.get("lp_lesson_outcome"):
        lesson_table = pd.DataFrame([
            {"Lesson Plan Component": "Course", "Detailed Plan": f"{course['course_code']} - {course['course_title']}"},
            {"Lesson Plan Component": "Course Learning Outcome (CLO)", "Detailed Plan": f"{clo['clo_code']}: {clo['description']}"},
            {"Lesson Plan Component": "Bloom's Taxonomy Level", "Detailed Plan": clo['bloom_level']},
            {"Lesson Plan Component": "Lesson Topic", "Detailed Plan": topic},
            {"Lesson Plan Component": "Duration", "Detailed Plan": f"{int(duration)} minutes"},
            {"Lesson Plan Component": "Lesson Learning Outcome", "Detailed Plan": st.session_state.get("lp_lesson_outcome", "")},
            {"Lesson Plan Component": "Teaching Method", "Detailed Plan": teaching_method},
            {"Lesson Plan Component": "Teaching / Learning Activity", "Detailed Plan": st.session_state.get("lp_activity", "")},
            {"Lesson Plan Component": "Assessment Method", "Detailed Plan": assessment_method},
            {"Lesson Plan Component": "Assessment Task", "Detailed Plan": st.session_state.get("lp_assessment_task", "")},
            {"Lesson Plan Component": "Success Criterion", "Detailed Plan": st.session_state.get("lp_success_criterion", "")},
            {"Lesson Plan Component": "Evaluation / Improvement Plan", "Detailed Plan": st.session_state.get("lp_evaluation", "")},
        ])
        st.dataframe(
            lesson_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Lesson Plan Component": st.column_config.TextColumn("Lesson Plan Component", width="medium"),
                "Detailed Plan": st.column_config.TextColumn("Detailed Plan", width="large"),
            },
        )
        st.info("✏️ To revise the generated lesson, edit the fields above. The table will update automatically.")
    else:
        st.info("Complete your choices and click **Generate AI-Aligned Lesson Plan** to display the detailed lesson plan table here.")

    st.markdown("### Review & Finalize")
    st.caption("Review or edit the generated fields above, then check OBE alignment and save the lesson plan.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Check OBE Alignment", use_container_width=True):
            fields = [
                st.session_state.get("lp_lesson_outcome"),
                st.session_state.get("lp_activity"),
                st.session_state.get("lp_assessment_task"),
                st.session_state.get("lp_success_criterion"),
                st.session_state.get("lp_evaluation"),
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
            outcome = st.session_state.get("lp_lesson_outcome", "").strip()
            if not topic or not outcome:
                st.warning("Generate/review the lesson plan first. Lesson topic and learning outcome are required.")
            else:
                execute("""INSERT INTO lesson_plans(course_id,clo_id,topic,duration,lesson_outcome,teaching_method,activity,assessment_method,assessment_task,success_criterion,evaluation)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (course['id'], clo['id'], topic, int(duration), outcome,
                         teaching_method, st.session_state.get("lp_activity", ""),
                         assessment_method, st.session_state.get("lp_assessment_task", ""),
                         st.session_state.get("lp_success_criterion", ""), st.session_state.get("lp_evaluation", "")))
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
