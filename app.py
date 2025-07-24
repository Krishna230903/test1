# app.py
# Complete code for the MediRepo Streamlit Application by Friday

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import uuid
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    conn = sqlite3.connect('medirepo.db')
    c = conn.cursor()
    
    # Patients Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            unique_id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            dob TEXT,
            location TEXT,
            height_cm REAL,
            diet_pref TEXT,
            gender TEXT
        )
    ''')
    
    # Doctors Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            speciality TEXT NOT NULL
        )
    ''')

    # Vitals Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vitals (
            vital_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            record_date TEXT NOT NULL,
            weight_kg REAL,
            bp_systolic INTEGER,
            bp_diastolic INTEGER,
            heart_rate INTEGER,
            sugar_level REAL,
            FOREIGN KEY (patient_id) REFERENCES patients(unique_id)
        )
    ''')

    # Prescriptions Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            rx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            doctor_name TEXT,
            visit_date TEXT NOT NULL,
            summary TEXT,
            medicine TEXT NOT NULL,
            frequency TEXT,
            timing TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(unique_id)
        )
    ''')

    conn.commit()
    conn.close()

# --- HELPER FUNCTIONS (DATABASE INTERACTIONS) ---
def db_execute(query, params=()):
    """A helper function to execute database queries."""
    conn = sqlite3.connect('medirepo.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def db_query(query, params=()):
    """A helper function to fetch data from the database."""
    conn = sqlite3.connect('medirepo.db')
    c = conn.cursor()
    c.execute(query, params)
    data = c.fetchall()
    conn.close()
    return data

# --- PATIENT SPECIFIC FUNCTIONS ---
def get_patient_vitals(patient_id):
    """Fetches all vitals for a given patient and returns a DataFrame."""
    vitals_data = db_query("SELECT record_date, weight_kg, bp_systolic, bp_diastolic, heart_rate, sugar_level FROM vitals WHERE patient_id = ? ORDER BY record_date ASC", (patient_id,))
    if not vitals_data:
        return pd.DataFrame()
    df = pd.DataFrame(vitals_data, columns=['Date', 'Weight (kg)', 'BP Systolic', 'BP Diastolic', 'Heart Rate (BPM)', 'Sugar Level'])
    df['Date'] = pd.to_datetime(df['Date'])
    return df

def get_patient_prescriptions(patient_id):
    """Fetches all prescriptions for a patient."""
    rx_data = db_query("SELECT visit_date, doctor_name, summary, medicine, frequency, timing FROM prescriptions WHERE patient_id = ? ORDER BY visit_date DESC", (patient_id,))
    if not rx_data:
        return pd.DataFrame()
    df = pd.DataFrame(rx_data, columns=['Visit Date', 'Doctor', 'Summary', 'Medicine', 'Frequency', 'Timing'])
    return df

# --- UI & LOGIC FUNCTIONS ---

def patient_dashboard():
    """The main dashboard view for a logged-in patient."""
    user = st.session_state.user_info
    full_name = f"{user['first_name']} {user.get('last_name', '')}".strip()
    st.header(f"Hi, {full_name} 👋")

    # --- SIDEBAR FOR PROFILE ---
    with st.sidebar:
        st.title("My Profile")
        st.write(f"**Name:** {full_name}")
        st.write(f"**Unique ID:** {user['unique_id']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Phone:** {user['phone']}")
        st.divider()

        with st.form("profile_form"):
            st.subheader("Update Your Info")
            height = st.number_input("Height (cm)", value=float(user.get('height_cm') or 0), format="%.1f")
            dob = st.date_input("Date of Birth", value=datetime.strptime(user.get('dob') or '2000-01-01', '%Y-%m-%d'))
            gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"], index=0 if not user.get('gender') else ["Male", "Female", "Other", "Prefer not to say"].index(user.get('gender')))
            diet = st.selectbox("Dietary Preference", ["Vegetarian", "Non-Vegetarian", "Ovo-Vegetarian", "Jain"], index=0 if not user.get('diet_pref') else ["Vegetarian", "Non-Vegetarian", "Ovo-Vegetarian", "Jain"].index(user.get('diet_pref')))
            location = st.text_input("Location", value=user.get('location', ''))

            if st.form_submit_button("Save Profile"):
                db_execute("UPDATE patients SET height_cm=?, dob=?, gender=?, diet_pref=?, location=? WHERE unique_id=?", 
                           (height, dob.strftime('%Y-%m-%d'), gender, diet, location, user['unique_id']))
                # Update session state
                st.session_state.user_info['height_cm'] = height
                st.session_state.user_info['dob'] = dob.strftime('%Y-%m-%d')
                st.success("Profile Updated!")
                st.experimental_rerun()
        
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.experimental_rerun()

    # --- MAIN DASHBOARD TABS ---
    vitals_df = get_patient_vitals(user['unique_id'])
    prescriptions_df = get_patient_prescriptions(user['unique_id'])
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Health Vitals", "💊 My Prescriptions", "🏋️ Fitness Hub", "➕ Add New Data"])

    with tab1:
        st.subheader("Your Health Journey Over Time")
        if vitals_df.empty:
            st.info("No vitals data found. Add some data to see your charts!")
        else:
            # Weight Chart
            if 'Weight (kg)' in vitals_df.columns and vitals_df['Weight (kg)'].notna().any():
                fig_weight = px.line(vitals_df, x='Date', y='Weight (kg)', title='Weight Journey', markers=True)
                st.plotly_chart(fig_weight)
            
            # BP Chart
            if 'BP Systolic' in vitals_df.columns and vitals_df['BP Systolic'].notna().any():
                fig_bp = px.line(vitals_df, x='Date', y=['BP Systolic', 'BP Diastolic'], title='Blood Pressure Trends', markers=True)
                st.plotly_chart(fig_bp)
            
            # Heart Rate Chart
            if 'Heart Rate (BPM)' in vitals_df.columns and vitals_df['Heart Rate (BPM)'].notna().any():
                fig_hr = px.line(vitals_df, x='Date', y='Heart Rate (BPM)', title='Heart Rate Trends', markers=True)
                st.plotly_chart(fig_hr)

            # Sugar Chart
            if 'Sugar Level' in vitals_df.columns and vitals_df['Sugar Level'].notna().any():
                fig_sugar = px.line(vitals_df, x='Date', y='Sugar Level', title='Blood Sugar Trends', markers=True)
                st.plotly_chart(fig_sugar)

    with tab2:
        st.subheader("Your Prescription History")
        if prescriptions_df.empty:
            st.info("No prescriptions recorded.")
        else:
            # Group by visit to show a clean record
            for visit_date, group in prescriptions_df.groupby('Visit Date'):
                with st.expander(f"**Visit on {visit_date}** with Dr. {group['Doctor'].iloc[0]}"):
                    st.write(f"**Diagnosis:** {group['Summary'].iloc[0]}")
                    st.dataframe(group[['Medicine', 'Frequency', 'Timing']].reset_index(drop=True))

    with tab3:
        st.subheader("Your Fitness & Wellness Hub")
        if user.get('height_cm') and not vitals_df.empty and vitals_df['Weight (kg)'].notna().any():
            latest_weight = vitals_df.dropna(subset=['Weight (kg)'])['Weight (kg)'].iloc[-1]
            height_m = user['height_cm'] / 100
            bmi = latest_weight / (height_m ** 2)
            
            bmi_category = "Unknown"
            if bmi < 18.5: bmi_category = "Underweight"
            elif 18.5 <= bmi < 24.9: bmi_category = "Healthy Weight"
            elif 25 <= bmi < 29.9: bmi_category = "Overweight"
            else: bmi_category = "Obesity"

            st.metric(label="Your Current BMI", value=f"{bmi:.2f}", help=f"Your current BMI category is {bmi_category}. Formula: $BMI = \\frac{{weight (kg)}}{{height (m)^2}}$")
        else:
            st.warning("Please add your height in the profile and at least one weight entry to calculate BMI.")
        
        st.divider()
        if st.button("How can I get fitter?"):
            st.session_state.show_fitness_form = True

        if st.session_state.get("show_fitness_form"):
            with st.form("fitness_form"):
                goal_weight = st.number_input("What is your goal weight (kg)?", min_value=30.0, step=1.0)
                
                submitted = st.form_submit_button("Calculate My Plan")
                if submitted and goal_weight > 0 and user.get('dob') and not vitals_df.empty:
                    # Basic BMR and Calorie suggestion
                    age = datetime.now().year - datetime.strptime(user['dob'], '%Y-%m-%d').year
                    latest_weight = vitals_df.dropna(subset=['Weight (kg)'])['Weight (kg)'].iloc[-1]
                    height_cm = user['height_cm']
                    
                    if user['gender'] == 'Male':
                        bmr = 88.362 + (13.397 * latest_weight) + (4.799 * height_cm) - (5.677 * age)
                    else: # Female
                        bmr = 447.593 + (9.247 * latest_weight) + (3.098 * height_cm) - (4.330 * age)
                    
                    tdee = bmr * 1.2 # Sedentary assumption
                    target_calories = tdee - 500 # For ~0.5kg/week loss

                    st.info(f"To reach your goal of **{goal_weight} kg**, a good starting point is to aim for around **{int(target_calories)} calories** per day. This creates a healthy deficit.")
                    st.write("#### Suggested Basic Exercises:")
                    st.markdown("""
                    - **Cardio:** 30 minutes of brisk walking, jogging, or cycling, 3-5 times a week.
                    - **Strength:** Bodyweight exercises like squats, push-ups, and planks, 2-3 times a week.
                    - **Flexibility:** Basic yoga or stretching daily to improve mobility.
                    
                    *Disclaimer: This is a basic suggestion. Please consult a healthcare professional before starting any new diet or exercise regimen.*
                    """)
                elif submitted:
                    st.error("Please ensure your profile (height, DoB) and weight records are up to date.")

    with tab4:
        st.subheader("Add a New Health Record")
        with st.form("vitals_form"):
            record_date = st.date_input("Date of Record", datetime.now())
            weight = st.number_input("Weight (kg)", min_value=0.0, format="%.1f", help="Leave as 0 if not recording")
            bp_s = st.number_input("Blood Pressure - Systolic (e.g., 120)", min_value=0, help="Leave as 0 if not recording")
            bp_d = st.number_input("Blood Pressure - Diastolic (e.g., 80)", min_value=0, help="Leave as 0 if not recording")
            hr = st.number_input("Heart Rate (BPM)", min_value=0, help="Leave as 0 if not recording")
            sugar = st.number_input("Blood Sugar (mg/dL)", min_value=0.0, format="%.1f", help="Leave as 0 if not recording")
            
            if st.form_submit_button("Save Record"):
                db_execute("INSERT INTO vitals (patient_id, record_date, weight_kg, bp_systolic, bp_diastolic, heart_rate, sugar_level) VALUES (?,?,?,?,?,?,?)",
                           (user['unique_id'], record_date.strftime('%Y-%m-%d %H:%M:%S'), 
                            weight if weight > 0 else None,
                            bp_s if bp_s > 0 else None,
                            bp_d if bp_d > 0 else None,
                            hr if hr > 0 else None,
                            sugar if sugar > 0 else None))
                st.success("New record added!")
                # Could add a rerun here if you want the charts to update instantly
                st.experimental_rerun()


def patient_journey():
    """Handles the entire flow for a patient, from login to dashboard."""
    auth_choice = st.radio("Choose Action", ["Login", "Register"], horizontal=True)

    if auth_choice == "Register":
        with st.form("register_patient"):
            st.subheader("Patient Registration")
            fname = st.text_input("First Name*")
            lname = st.text_input("Last Name (Optional)")
            email = st.text_input("Email*")
            phone = st.text_input("Phone Number*")
            
            if st.form_submit_button("Register"):
                if not (fname and email and phone):
                    st.error("Please fill all mandatory fields.")
                else:
                    try:
                        unique_id = str(uuid.uuid4())[:8].upper()
                        db_execute("INSERT INTO patients (unique_id, first_name, last_name, email, phone) VALUES (?,?,?,?,?)",
                                   (unique_id, fname, lname, email, phone))
                        st.success(f"Registration Successful! Your Unique ID is: **{unique_id}**")
                        st.info("Please save this ID securely for future logins.")
                    except sqlite3.IntegrityError:
                        st.error("An account with this email or phone number already exists.")

    else: # Login
        with st.form("login_patient"):
            st.subheader("Patient Login")
            fname = st.text_input("First Name*")
            unique_id = st.text_input("Unique ID*")
            # Last name is not used for login to simplify it as it's optional
            
            if st.form_submit_button("Login"):
                user_data = db_query("SELECT * FROM patients WHERE first_name=? AND unique_id=?", (fname, unique_id))
                if user_data:
                    user_details = user_data[0]
                    st.session_state.logged_in = True
                    st.session_state.role = 'Patient'
                    # Store user info in a dictionary for easy access
                    st.session_state.user_info = {
                        'unique_id': user_details[0], 'first_name': user_details[1], 'last_name': user_details[2],
                        'email': user_details[3], 'phone': user_details[4], 'dob': user_details[5],
                        'location': user_details[6], 'height_cm': user_details[7], 'diet_pref': user_details[8],
                        'gender': user_details[9]
                    }
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials. Please check your First Name and Unique ID.")

def doctor_portal():
    """The main portal for a logged-in doctor."""
    user = st.session_state.user_info
    full_name = f"Dr. {user['first_name']} {user.get('last_name', '')}".strip()
    st.header(f"Welcome, {full_name}")
    st.write(f"Speciality: {user['speciality']}")

    st.divider()

    # Form to enter prescription
    with st.form("prescription_form"):
        st.subheader("Create New Prescription")
        patient_id = st.text_input("Enter Patient's Unique ID*")
        visit_date = st.date_input("Date of Visit", datetime.now())
        summary = st.text_area("Diagnosis Summary")
        
        st.markdown("---")
        st.markdown("**Medicines**")

        # Dynamic medicine entry
        if 'medicines' not in st.session_state:
            st.session_state.medicines = [{'name': '', 'freq': 'Once a day', 'timing': 'After Breakfast'}]

        for i, med in enumerate(st.session_state.medicines):
            cols = st.columns([3, 2, 2])
            med['name'] = cols[0].text_input(f"Medicine Name {i+1}", med['name'], key=f"med_name_{i}")
            med['freq'] = cols[1].selectbox(f"Frequency", ["Once a day", "Twice a day", "Thrice a day"], key=f"med_freq_{i}", index=["Once a day", "Twice a day", "Thrice a day"].index(med['freq']))
            med['timing'] = cols[2].selectbox(f"Timing", ["Empty Stomach", "After Breakfast", "After Lunch", "After Dinner", "Before Sleep"], key=f"med_time_{i}", index=["Empty Stomach", "After Breakfast", "After Lunch", "After Dinner", "Before Sleep"].index(med['timing']))
        
        if st.form_submit_button("Add Another Medicine"):
             st.session_state.medicines.append({'name': '', 'freq': 'Once a day', 'timing': 'After Breakfast'})
             st.experimental_rerun()

        st.markdown("---")

        if st.form_submit_button("Save Prescription"):
            if not patient_id:
                st.error("Patient Unique ID is required.")
            else:
                # Check if patient exists
                patient_exists = db_query("SELECT 1 FROM patients WHERE unique_id=?", (patient_id,))
                if not patient_exists:
                    st.error(f"No patient found with ID: {patient_id}")
                else:
                    # Save each medicine as a separate row
                    for med in st.session_state.medicines:
                        if med['name']: # Only save if medicine name is entered
                            db_execute("INSERT INTO prescriptions (patient_id, doctor_name, visit_date, summary, medicine, frequency, timing) VALUES (?,?,?,?,?,?,?)",
                                       (patient_id, full_name, visit_date.strftime('%Y-%m-%d'), summary, med['name'], med['freq'], med['timing']))
                    st.success("Prescription saved successfully!")
                    # Clear medicines for the next entry
                    del st.session_state.medicines

    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()


def doctor_journey():
    """Handles the entire flow for a doctor."""
    auth_choice = st.radio("Choose Action", ["Login", "Register"], horizontal=True)

    if auth_choice == "Register":
        with st.form("register_doctor"):
            st.subheader("Doctor Registration")
            fname = st.text_input("First Name*")
            lname = st.text_input("Last Name*")
            email = st.text_input("Email*")
            phone = st.text_input("Phone Number*")
            speciality = st.text_input("Speciality*")
            
            if st.form_submit_button("Register"):
                if not all([fname, lname, email, phone, speciality]):
                    st.error("Please fill all fields.")
                else:
                    try:
                        db_execute("INSERT INTO doctors (first_name, last_name, email, phone, speciality) VALUES (?,?,?,?,?)",
                                   (fname, lname, email, phone, speciality))
                        st.success("Doctor registered successfully! Please login.")
                    except sqlite3.IntegrityError:
                        st.error("A doctor with this email or phone already exists.")

    else: # Login
        with st.form("login_doctor"):
            st.subheader("Doctor Login")
            fname = st.text_input("First Name*")
            lname = st.text_input("Last Name*")
            phone = st.text_input("Phone Number*")
            
            if st.form_submit_button("Login"):
                user_data = db_query("SELECT * FROM doctors WHERE first_name=? AND last_name=? AND phone=?", (fname, lname, phone))
                if user_data:
                    user_details = user_data[0]
                    st.session_state.logged_in = True
                    st.session_state.role = 'Doctor'
                    st.session_state.user_info = {
                        'id': user_details[0], 'first_name': user_details[1], 'last_name': user_details[2],
                        'email': user_details[3], 'phone': user_details[4], 'speciality': user_details[5]
                    }
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials.")

# --- MAIN APPLICATION ---
def main():
    """The main function that orchestrates the app's flow."""
    st.set_page_config(page_title="MediRepo", layout="wide")
    st.title("Welcome to MediRepo 🩺")

    # Initialize the database
    init_db()

    # Initialize session state variables
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_info = None

    # Routing logic
    if st.session_state.logged_in:
        if st.session_state.role == 'Patient':
            patient_dashboard()
        elif st.session_state.role == 'Doctor':
            doctor_portal()
    else:
        # Main selection for non-logged-in users
        role = st.selectbox("I am a:", ["--Select--", "Patient", "Doctor"])
        if role == "Patient":
            patient_journey()
        elif role == "Doctor":
            doctor_journey()

if __name__ == "__main__":
    main()
