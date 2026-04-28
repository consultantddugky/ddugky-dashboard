from flask import Flask, render_template, request, redirect, session , url_for , jsonify
from flask_mysqldb import MySQL
import pandas as pd
import json
from datetime import datetime , timedelta

app = Flask(__name__)

# MySQL config
import os


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234567890'


app.config['MYSQL_DB'] = 'kaushal_dashboard'
mysql = MySQL(app)


#  LOGIN

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()

        if user:
            session['loggedin'] = True
            return redirect('/dashboard')
        else:
            return "Invalid credentials"

    return render_template('login.html')



# DASHBOARD

from flask import Flask, render_template, request
from datetime import date

@app.route('/dashboard')
def dashboard():
    pia_prn = request.args.get('pia_prn')
    cur = mysql.connection.cursor()

    # ✅ DEFAULTS (prevents undefined errors)
    block_labels, block_values = [], []
    eligibility_labels, eligibility_counts = [], []
    taluka_labels, taluka_counts = [], []

    def get_value():
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else 0

    # ================= BASIC =================
    cur.execute("SELECT COUNT(*) FROM pia")
    total_pias = get_value()

    cur.execute("SELECT prn, pia_name FROM pia")
    pia_list = cur.fetchall()

    # ================= KPI =================
    if pia_prn:
        cur.execute("SELECT COUNT(*) FROM batch WHERE pia_prn=%s", (pia_prn,))
        total_batches = get_value()

        cur.execute("SELECT COUNT(*) FROM batch WHERE pia_prn=%s AND CURDATE() > freeze_date", (pia_prn,))
        freezed_batches = get_value()

        cur.execute("SELECT COALESCE(SUM(total_enrolled),0) FROM batch WHERE pia_prn=%s", (pia_prn,))
        total_enrolled = get_value()

        cur.execute("SELECT COALESCE(SUM(placements),0) FROM sanction_order WHERE pia_prn=%s", (pia_prn,))
        total_placed = get_value()

        cur.execute("SELECT COALESCE(SUM(ojt_ongoing_candidates),0) FROM batch WHERE pia_prn=%s", (pia_prn,))
        on_ojt = get_value()

    else:
        cur.execute("SELECT COUNT(*) FROM batch")
        total_batches = get_value()

        cur.execute("SELECT COUNT(*) FROM batch WHERE CURDATE() > freeze_date")
        freezed_batches = get_value()

        cur.execute("SELECT COALESCE(SUM(total_enrolled),0) FROM batch")
        total_enrolled = get_value()

        cur.execute("SELECT COALESCE(SUM(placements),0) FROM sanction_order")
        total_placed = get_value()

        cur.execute("SELECT COALESCE(SUM(ojt_ongoing_candidates),0) FROM batch")
        on_ojt = get_value()

    # ================= BAR =================
    if pia_prn:
        cur.execute("""
            SELECT batch_code, COALESCE(total_enrolled,0)
            FROM batch WHERE pia_prn=%s
        """, (pia_prn,))
    else:
        cur.execute("""
            SELECT p.pia_name, COALESCE(SUM(b.total_enrolled),0)
            FROM pia p
            LEFT JOIN batch b ON p.prn = b.pia_prn
            GROUP BY p.prn, p.pia_name
        """)

    bar = cur.fetchall()
    bar_labels = [row[0] for row in bar]
    bar_enrolled = [int(row[1] or 0) for row in bar]

    # ================= CATEGORY =================

    if pia_prn:
        cur.execute("""
            SELECT 
                SUM(CASE WHEN LOWER(category)='sc' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(category)='st' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(category) NOT IN ('sc','st') THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(gender)='female' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(pwd_status)='yes' THEN 1 ELSE 0 END)
            FROM candidates c
            JOIN batch b ON c.batch_code = b.batch_code
            WHERE b.pia_prn = %s
        """, (pia_prn,))
    else:
        cur.execute("""
            SELECT 
                SUM(CASE WHEN LOWER(category)='sc' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(category)='st' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(category) NOT IN ('sc','st') THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(gender)='female' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(pwd_status)='yes' THEN 1 ELSE 0 END)
            FROM candidates
        """)

    cat = cur.fetchone() or (0,0,0,0,0)

    sc_total     = int(cat[0] or 0)
    st_total     = int(cat[1] or 0)
    others_total = int(cat[2] or 0)
    women_total  = int(cat[3] or 0)
    pwd_total    = int(cat[4] or 0)
    
    # ================= GENDER =================
    
    if pia_prn:
        cur.execute("""
            SELECT 
                SUM(CASE WHEN LOWER(gender)='male' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(gender)='female' THEN 1 ELSE 0 END)
            FROM candidates c
            JOIN batch b ON c.batch_code = b.batch_code
            WHERE b.pia_prn = %s
        """, (pia_prn,))
    else:
        cur.execute("""
            SELECT 
                SUM(CASE WHEN LOWER(gender)='male' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(gender)='female' THEN 1 ELSE 0 END)
            FROM candidates
        """)

    gender = cur.fetchone() or (0,0)

    male_total = int(gender[0] or 0)
    female_total = int(gender[1] or 0)

    # ================= ELIGIBILITY =================
    cur.execute("""
        SELECT eligibility, COUNT(*)
        FROM candidates
        WHERE eligibility IS NOT NULL
        GROUP BY eligibility
    """)
    eligibility = cur.fetchall()
    eligibility_labels = [row[0] for row in eligibility]
    eligibility_counts = [int(row[1]) for row in eligibility]

    # ================= TALUKA (ALL 12 TALUKAS) =================
    if pia_prn:
        cur.execute("""
            SELECT 
                UPPER(TRIM(c.taluka)) AS taluka,
                COUNT(*) AS total_candidates
            FROM candidates c
            JOIN batch b 
                ON c.batch_code = b.batch_code
            WHERE b.pia_prn = %s
            GROUP BY taluka
        """, (pia_prn,))
    else:
        cur.execute("""
            SELECT 
                UPPER(TRIM(taluka)) AS taluka,
                COUNT(*) AS total_candidates
            FROM candidates
            GROUP BY taluka
        """)

    data = cur.fetchall()

    # Convert DB result to dictionary
    db_counts = {row[0]: int(row[1]) for row in data}

    # Fixed 12 talukas
    ALL_TALUKAS = [
        "BARDEZ", "BICHOLIM", "CANACONA", "DHARBANDORA",
        "MORMUGAO", "PERNEM", "PONDA", "QUEPEM",
        "SALCETE", "SANGUEM", "SATTARI", "TISWADI"
    ]

    taluka_labels = ALL_TALUKAS
    taluka_counts = [db_counts.get(t, 0) for t in ALL_TALUKAS]

    
    if pia_prn:
        cur.execute("""
            SELECT sector, COUNT(DISTINCT pia_prn)
            FROM sanction_order
            WHERE pia_prn = %s
            GROUP BY sector
        """, (pia_prn,))
    else:
        # Overall → how many PIAs in each sector
        cur.execute("""
            SELECT sector, COUNT(DISTINCT pia_prn)
            FROM sanction_order
            WHERE sector IS NOT NULL AND TRIM(sector) != ''
            GROUP BY sector
            ORDER BY COUNT(DISTINCT pia_prn) DESC
        """)

    sector_data = cur.fetchall()

    sector_labels = [row[0] for row in sector_data]
    sector_values = [int(row[1] or 0) for row in sector_data]
    cur.close()
    return render_template(
        'dashboard.html',
        pia_list=pia_list,
        selected_pia=pia_prn,
        total_pias=total_pias,
        total_batches=total_batches,
        freezed_batches=freezed_batches,
        total_enrolled=total_enrolled,
        on_ojt=on_ojt,
        sector_labels=sector_labels,
        sector_values=sector_values,

        bar_labels=bar_labels,
        bar_enrolled=bar_enrolled,

        male_total=male_total,
        female_total=female_total,

        sc_total=cat[0],
        st_total=cat[1],
        others_total=cat[2],
        women_total=cat[3],
        pwd_total=cat[4],

        eligibility_labels=eligibility_labels,
        eligibility_counts=eligibility_counts,

        taluka_labels=taluka_labels,
        taluka_counts=taluka_counts
    )

#Taluka wise candidates details
@app.route('/candidates')
def candidates():
    taluka = request.args.get('taluka')
    pia_prn = request.args.get('pia_prn')

    cur = mysql.connection.cursor()

    if pia_prn:
        cur.execute("""
            SELECT 
                v.village_panchayat AS village,
                COUNT(c.village) AS total_candidates
            FROM village_panchayat_master v
            LEFT JOIN candidates c 
                ON LOWER(TRIM(v.village_panchayat)) = LOWER(TRIM(c.village))
            LEFT JOIN batch b 
                ON c.batch_code = b.batch_code
                AND b.pia_prn = %s
            WHERE LOWER(TRIM(v.taluka)) = LOWER(TRIM(%s))
            GROUP BY v.village_panchayat
            ORDER BY v.village_panchayat
        """, (pia_prn, taluka))

    else:
        cur.execute("""
            SELECT 
                v.village_panchayat AS village,
                COUNT(c.village) AS total_candidates
            FROM village_panchayat_master v
            LEFT JOIN candidates c 
                ON LOWER(TRIM(v.village_panchayat)) = LOWER(TRIM(c.village))
            WHERE LOWER(TRIM(v.taluka)) = LOWER(TRIM(%s))
            GROUP BY v.village_panchayat
            ORDER BY v.village_panchayat
        """, (taluka,))

    data = cur.fetchall()
    cur.close()

    return render_template(
        "candidates.html",
        data=data,
        taluka=taluka,
        selected_pia=pia_prn
    )


import pandas as pd
from flask import send_file
from io import BytesIO

@app.route('/download_candidates')
def download_candidates_talukawise():
    taluka = request.args.get('taluka')
    pia_prn = request.args.get('pia_prn')

    cur = mysql.connection.cursor()

    if pia_prn:
        cur.execute("""
            SELECT name, district, taluka, present_address
            FROM candidates c
            JOIN batch b ON c.batch_code = b.batch_code
            WHERE TRIM(c.taluka)=TRIM(%s)
              AND TRIM(b.pia_prn)=TRIM(%s)
        """, (taluka, pia_prn))
    else:
        cur.execute("""
            SELECT name, district, taluka, present_address
            FROM candidates
            WHERE TRIM(taluka)=TRIM(%s)
        """, (taluka,))

    data = cur.fetchall()
    cur.close()

    # Convert to DataFrame
    df = pd.DataFrame(data, columns=["Name","District","Taluka","Address"])

    # Save to memory
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(
        output,
        download_name=f"{taluka}_candidates.xlsx",
        as_attachment=True
    )

# ADD PIA
@app.route('/add_pia', methods=['GET', 'POST'])
def add_pia():
    if request.method == 'POST':
        prn = request.form['prn']
        name = request.form['pia_name']
        state = request.form['state']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO pia VALUES (%s,%s,%s)", (prn, name, state))
        mysql.connection.commit()
        return redirect('/dashboard')
        

    return render_template('pia_form.html')

#Add sanction order details
@app.route('/add_sanction_order', methods=['GET', 'POST'])
def add_sanction():
    cur = mysql.connection.cursor()

    # Fetch PIA list
    cur.execute("SELECT prn, pia_name FROM pia")
    pias = cur.fetchall()

    if request.method == 'POST':
        data = request.form

        try:
            cur.execute("""
                INSERT INTO sanction_order 
                (sanction_order_no, pia_prn, sector, job_role, total_duration, ojt_duration, placements, total_target,
                 sc_target, st_target, others_target,
                 women_target, pwd_target, r_nr)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                data['sanction_order_no'],
                data['pia_prn'],
                data['sector'],
                data['job_role'],
                data['total_duration'],
                data['ojt_duration'],
                data['placements'],
                data['total_target'],
                data.get('sc_target') or 0,
                data.get('st_target') or 0,
                data.get('others_target') or 0,
                data.get('women_target') or 0,
                data.get('pwd_target') or 0,
                data['r_nr']
            ))

            mysql.connection.commit()

            return render_template(
                'sanction_form.html',
                pias=pias,
                success="Sanction saved successfully!"
            )

        except Exception as e:
            print("ERROR:", e)
            return render_template(
                'sanction_form.html',
                pias=pias,
                error=str(e)
            )

    
    return render_template('sanction_form.html', pias=pias)

#View Sanction Order Details
@app.route('/view_sanction_orders')
def view_sanction_orders():
    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT so.*, pia.pia_name 
        FROM sanction_order so
        JOIN pia ON so.pia_prn = pia.prn
    """)

    orders = cursor.fetchall()
    print("DATA:", orders)   # 👈 DEBUG LINE

    return render_template('view_sanction_orders.html', orders=orders)

@app.route('/edit_sanction_order/', methods=['GET', 'POST'])
def edit_sanction_order(order_no):
    cursor = mysql.connection.cursor()

    if request.method == 'POST':
        data = request.form

        cursor.execute("""
            UPDATE sanction_order
            SET job_role=%s, total_target=%s
            WHERE sanction_order_no=%s
        """, (data['job_role'], data['total_target'], order_no))

        mysql.connection.commit()
        return redirect('/view_sanction_orders')

    cursor.execute("SELECT * FROM sanction_order WHERE sanction_order_no=%s", (order_no,))
    order = cursor.fetchone()

    return render_template('edit_sanction_order.html', order=order)

@app.route('/delete_sanction_order/<order_no>')
def delete_sanction_order(order_no):
    cursor = mysql.connection.cursor()

    cursor.execute("DELETE FROM sanction_order WHERE sanction_order_no=%s", (order_no,))
    mysql.connection.commit()

    return redirect('/view_sanction_orders')


#Project Timeline Details
@app.route('/add_project_timeline', methods=['GET', 'POST'])
def add_project_timeline():
    cur = mysql.connection.cursor()

    # Get all PIAs for dropdown
    cur.execute("SELECT prn, pia_name FROM pia")
    pias = cur.fetchall()

    if request.method == 'POST':
        pia_prn = request.form['pia_prn']
        mou_signing_date = request.form['mou_signing_date']
        pco_date = request.form['pco_date']

        try:
            cur.execute("""
                INSERT INTO project_timeline (pia_prn, mou_signing_date, pco_date)
                VALUES (%s, %s, %s)
            """, (pia_prn, mou_signing_date, pco_date))

            mysql.connection.commit()

            return render_template(
                'project_timeline_form.html',
                pias=pias,
                success="Project timeline saved successfully!"
            )

        except Exception as e:
            return render_template(
                'project_timeline_form.html',
                pias=pias,
                error="Error saving project timeline!"
            )

    return render_template('project_timeline_form.html', pias=pias)

#Training Centre Form
@app.route('/add_training_centre', methods=['GET', 'POST'])
def add_training_centre():
    cur = mysql.connection.cursor()

    # Fetch PIA list for dropdown
    cur.execute("SELECT prn, pia_name FROM pia")
    pias = cur.fetchall()

    if request.method == 'POST':
        data = request.form

        try:
            cur.execute("""
                INSERT INTO training_centres 
                (pia_prn, centre_name, district, state, male_capacity, female_capacity, 
                 total_capacity, r_nr, training_centre_capacity)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                data['pia_prn'],
                data['centre_name'],
                data['district'],
                data['state'],
                data['male_capacity'],
                data['female_capacity'],
                data['total_capacity'],
                data['r_nr'],
                data['training_centre_capacity']
            ))

            mysql.connection.commit()

            return render_template(
                'training_centre_form.html',
                pias=pias,
                success="Training Centre added successfully!"
            )

        except Exception as e:
            return render_template(
                'training_centre_form.html',
                pias=pias,
                error="Error adding training centre!"
            )

    return render_template('training_centre_form.html', pias=pias)

#Residential Facility
@app.route('/add_residential_facility', methods=['GET', 'POST'])
def add_residential_facility():
    cur = mysql.connection.cursor()

    # Fetch training centres for dropdown
    cur.execute("SELECT id, centre_name FROM training_centres")
    centres = cur.fetchall()

    if request.method == 'POST':
        data = request.form

        try:
            male = int(data['male_capacity'])
            female = int(data['female_capacity'])
            total = male + female  # auto-calculate

            cur.execute("""
                INSERT INTO residential_facility 
                (centre_id, male_capacity, female_capacity, total_capacity)
                VALUES (%s, %s, %s, %s)
            """, (
                data['centre_id'],
                male,
                female,
                total
            ))

            mysql.connection.commit()

            return render_template(
                'residential_facility_form.html',
                centres=centres,
                success="Residential facility added successfully!"
            )

        except Exception as e:
            return render_template(
                'residential_facility_form.html',
                centres=centres,
                error="Error adding residential facility (maybe already exists for this centre)."
            )

    return render_template('residential_facility_form.html', centres=centres)

#PIA Staff
@app.route('/add_pia_staff', methods=['GET', 'POST'])
def add_pia_staff():
    cur = mysql.connection.cursor()

    # Fetch PIA list for dropdown
    cur.execute("SELECT prn, pia_name FROM pia")
    pias = cur.fetchall()

    if request.method == 'POST':
        data = request.form

        try:
            cur.execute("""
                INSERT INTO pia_staff (pia_prn, role, name, contact)
                VALUES (%s, %s, %s, %s)
            """, (
                data['pia_prn'],
                data['role'],
                data['name'],
                data['contact']
            ))

            mysql.connection.commit()

            return render_template(
                'pia_staff_form.html',
                pias=pias,
                success="PIA staff added successfully!"
            )

        except Exception as e:
            return render_template(
                'pia_staff_form.html',
                pias=pias,
                error="Error adding staff!"
            )

    return render_template('pia_staff_form.html', pias=pias)

#Centre Staff
@app.route('/add_centre_staff', methods=['GET', 'POST'])
def add_centre_staff():
    cur = mysql.connection.cursor()

    # Fetch centres for dropdown
    cur.execute("SELECT id, centre_name FROM training_centres")
    centres = cur.fetchall()

    if request.method == 'POST':
        data = request.form

        try:
            cur.execute("""
                INSERT INTO centre_staff (centre_id, role, name, contact)
                VALUES (%s, %s, %s, %s)
            """, (
                data['centre_id'],
                data['role'],
                data['name'],
                data['contact']
            ))

            mysql.connection.commit()

            return render_template(
                'centre_staff_form.html',
                centres=centres,
                success="Centre staff added successfully!"
            )

        except Exception as e:
            return render_template(
                'centre_staff_form.html',
                centres=centres,
                error="Error adding centre staff!"
            )

    return render_template('centre_staff_form.html', centres=centres)

@app.route('/pia_details/<pia_prn>')
def pia_details(pia_prn):
    cur = mysql.connection.cursor()

    # 🔹 PIA Info
    cur.execute("SELECT pia_name, state FROM pia WHERE prn=%s", (pia_prn,))
    pia = cur.fetchone()

    # 🔹 Centres
    cur.execute("SELECT COUNT(*) FROM training_centres WHERE pia_prn=%s", (pia_prn,))
    centres = cur.fetchone()[0]

    # 🔹 Total Batches
    cur.execute("""
        SELECT COUNT(*) 
        FROM batch
        WHERE pia_prn=%s
    """, (pia_prn,))
    total_batches = cur.fetchone()[0]

    # 🔹 Active Batches
    cur.execute("""
        SELECT COUNT(*) 
        FROM batch
        WHERE pia_prn=%s AND CURDATE() <= freeze_date
    """, (pia_prn,))
    active_batches = cur.fetchone()[0]

    # 🔹 Freezed Batches
    cur.execute("""
        SELECT COUNT(*) 
        FROM batch
        WHERE pia_prn=%s AND CURDATE() > freeze_date
    """, (pia_prn,))
    freezed_batches = cur.fetchone()[0]

    # 🔹 Candidates
    # 🔹 Total Enrolled (SUM of all batches)
    cur.execute("""
        SELECT COALESCE(SUM(total_enrolled), 0)
        FROM batch
        WHERE pia_prn=%s
    """, (pia_prn,))
    total_enrolled = cur.fetchone()[0]

    # 🔹 Batch List
    cur.execute("""
        SELECT batch_code, start_date, freeze_date, ojt_start_date, ojt_end_date, total_enrolled, candidates_ongoing, ojt_ongoing_candidates, ojt_completed_candidates
        FROM batch
        WHERE pia_prn=%s
    """, (pia_prn,))
    batches = cur.fetchall()

    return render_template(
        'pia_details.html',
        pia=pia,
        centres=centres,
        total_batches=total_batches,
        active_batches=active_batches,
        freezed_batches=freezed_batches,
        total_enrolled=total_enrolled,
        batches=batches
    )

#Add location
@app.route('/add_location', methods=['GET', 'POST'])
def add_location():
    cur = mysql.connection.cursor()

    cur.execute("SELECT prn, pia_name FROM pia")
    pias = cur.fetchall()

    if request.method == 'POST':
        data = request.form

        # 🔹 Clean data before saving
        state = data['state'].strip().title()
        district = data['district'].strip().title()
        block = data['block_name'].strip().title()

        cur.execute("""
        INSERT INTO location_data 
        (pia_prn, batch_code, state, district, block_name, candidates)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data['pia_prn'],
        data['batch_code'],
        state,
        district,
        block,
        data['candidates']
    ))

        mysql.connection.commit()
        return redirect('/dashboard')

    return render_template('add_location.html', pias=pias)

#Add Batch 
@app.route('/add_batch', methods=['GET', 'POST'])
def add_batch():
    cur = mysql.connection.cursor()

    # Fetch PIA list
    cur.execute("SELECT prn, pia_name FROM pia")
    pias = cur.fetchall()

    if request.method == 'POST':
        data = request.form

        try:
            # ===============================
            # ✅ Dates
            # ===============================
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
            freeze_date = start_date + timedelta(days=9)

            # ===============================
            # ✅ Duration
            # ===============================
            HOURS_PER_DAY = 8

            total_duration = int(data.get('total_duration') or 0)
            ojt_duration = int(data.get('ojt_duration') or 0)

            total_days = total_duration // HOURS_PER_DAY
            ojt_days = ojt_duration // HOURS_PER_DAY

            if ojt_days > total_days:
                return render_template(
                    'batch_form.html',
                    error="OJT duration cannot be greater than total duration",
                    pias=pias
                )

            # ===============================
            # ✅ OJT Dates
            # ===============================
            ojt_start_date = None
            ojt_end_date = None

            if total_days > 0:
                ojt_start_date = start_date + timedelta(days=(total_days - ojt_days))
                ojt_end_date = start_date + timedelta(days=total_days)

            # ===============================
            # ✅ Candidate Counts
            # ===============================
            male = int(data.get('male_count') or 0)
            female = int(data.get('female_count') or 0)

            # NEW: Category counts
            sc = int(data.get('sc_count') or 0)
            st = int(data.get('st_count') or 0)
            obc = int(data.get('obc_count') or 0)

            total_enrolled = male + female  

            today = datetime.today().date()

            candidates_ongoing = 0
            ojt_ongoing_candidates = 0
            ojt_completed_candidates = 0

            if ojt_start_date and ojt_end_date:

                if today < ojt_start_date.date():
                    candidates_ongoing = total_enrolled

                elif ojt_start_date.date() <= today <= ojt_end_date.date():
                    candidates_ongoing = total_enrolled
                    ojt_ongoing_candidates = total_enrolled

                else:
                    ojt_completed_candidates = total_enrolled

            # ===============================
            # ✅ INSERT (FIXED)
            # ===============================
            cur.execute("""
                INSERT INTO batch 
                (pia_prn, batch_code, job_role, male_count, female_count, 
                 sc_count, st_count, obc_count,
                 start_date, freeze_date,
                 ojt_start_date, ojt_end_date,
                 total_enrolled, candidates_ongoing, 
                 ojt_ongoing_candidates, ojt_completed_candidates,
                 total_duration, ojt_duration)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                data['pia_prn'],
                data['batch_code'],
                data.get('job_role'),
                male,
                female,
                sc,
                st,
                obc,
                start_date,
                freeze_date,
                ojt_start_date,
                ojt_end_date,
                total_enrolled,
                candidates_ongoing,
                ojt_ongoing_candidates,
                ojt_completed_candidates,
                total_duration,
                ojt_duration
            ))

            mysql.connection.commit()

            return render_template(
                'batch_form.html',
                success="Batch added successfully!",
                pias=pias
            )

        except Exception as e:
            return render_template(
                'batch_form.html',
                error=str(e),
                pias=pias
            )

    return render_template('batch_form.html', pias=pias)

@app.route('/add-batch')
def add_batch_page():
    pia_id = request.args.get('pia_id')
    return render_template('add_batch.html', pia_id=pia_id)

@app.route('/save-batch', methods=['POST'])
def save_batch():
    pia_id = request.form['pia_id']
    batch_number = request.form['batch_number']
    state = request.form['state']
    registration_date = request.form['registration_date']
    training_duration = request.form['training_duration']

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO batch (pia_id, batch_number, state, registration_date, training_duration)
        VALUES (%s, %s, %s, %s, %s)
    """, (pia_id, batch_number, state, registration_date, training_duration))

    mysql.connection.commit()

    return redirect(f"/pia-details?pia_id={pia_id}")

from MySQLdb.cursors import DictCursor


@app.route('/batch-details')
def batch_details():
    batch_id = request.args.get('batch_id')
    pia_id = request.args.get('pia_id')

    cur = mysql.connection.cursor(DictCursor)

    # ✅ Batch details with status
    cur.execute("""
        SELECT 
            id,
            batch_number,
            state,
            registration_date,

            DATEDIFF(CURDATE(), registration_date) AS days_passed,

            CASE 
                WHEN DATEDIFF(CURDATE(), registration_date) >= 10 THEN 'Freezed'
                WHEN DATEDIFF(CURDATE(), registration_date) = 9 THEN 'Freezing Tomorrow'
                ELSE 'Active'
            END AS status

        FROM batch
        WHERE id=%s
    """, (batch_id,))

    batch = cur.fetchone()

    # ✅ Candidates (FIXED: added days_passed + status)
    cur.execute("""
        SELECT 
            c.id, 
            c.name, 
            c.gender, 
            c.category,
            c.district,
            c.present_address,
            c.permanent_address,
            c.contact_details,
            c.alternate_contact,
            c.dob,
            c.pwd_status,

            DATEDIFF(CURDATE(), c.enrollment_date) AS days_passed,

            CASE 
                WHEN DATEDIFF(CURDATE(), b.registration_date) >= 10 THEN 'Freezed'
                ELSE 'Active'
            END AS status

        FROM candidates c
        JOIN batch b ON c.batch_id = b.id
        WHERE c.batch_id=%s
    """, (batch_id,))

    candidates = cur.fetchall()

    return render_template(
        'batch_details.html',
        batch=batch,
        candidates=candidates,
        batch_id=batch_id,
        pia_id=pia_id
    )

#Delete Batch
@app.route('/delete-batch')
def delete_batch():
    batch_id = request.args.get('batch_id')
    pia_id = request.args.get('pia_id')

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM candidates WHERE batch_id=%s", (batch_id,))

    cur.execute("DELETE FROM batch WHERE id=%s", (batch_id,))

    mysql.connection.commit()

    return redirect(url_for('pia_details', pia_id=pia_id))

#Edit Batch
@app.route('/edit-batch')
def edit_batch():
    batch_id = request.args.get('batch_id')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM batch WHERE id=%s", (batch_id,))
    batch = cur.fetchone()

    return render_template('edit_batch.html', batch=batch)

#Update Batch-Save
@app.route('/update-batch', methods=['POST'])
def update_batch():
    cur = mysql.connection.cursor()

    batch_id = request.form.get('batch_id')
    pia_id = request.form.get('pia_id')  

    batch_number = request.form.get('batch_number')
    state = request.form.get('state')
    registration_date = request.form.get('registration_date')
    training_duration = request.form.get('training_duration')

    cur.execute("""
        UPDATE batch
        SET batch_number=%s,
            state=%s,
            registration_date=%s,
            training_duration=%s
        WHERE id=%s
    """, (batch_number, state, registration_date, training_duration, batch_id))

    mysql.connection.commit()

    if not pia_id:
        cur.execute("SELECT pia_id FROM batch WHERE id=%s", (batch_id,))
        row = cur.fetchone()
        pia_id = row[0] if row else None

    return redirect(url_for('pia_details', pia_id=pia_id))

from MySQLdb.cursors import DictCursor

#Add Candidates
@app.route('/add_candidate', methods=['GET', 'POST'])
def add_candidate():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        data = request.form

        try:
            cur.execute("""
                INSERT INTO candidates (
                    batch_code, name, gender, identity_number,
                    father_name, mother_name, category, district,
                    present_address, permanent_address, pwd_status,
                    contact_details, alternate_contact, dob, enrollment_date,
                    eligibility, job_role
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['batch_code'], data['name'], data['gender'],
                data['identity_number'], data['father_name'], data['mother_name'],
                data['category'], data['district'], data['present_address'],
                data['permanent_address'], data['pwd_status'],
                data['contact_details'], data['alternate_contact'],
                data['dob'], data['enrollment_date'],
                data['eligibility'], data['job_role']
            ))

            mysql.connection.commit()

            success = "Candidate added successfully!"
            error = None

        except Exception as e:
            mysql.connection.rollback()
            success = None
            error = str(e)

    else:
        success = None
        error = None

    # 🔹 Load PIA list
    cur.execute("SELECT prn, pia_name FROM pia")
    pias = cur.fetchall()

    return render_template(
        "candidate_form.html",
        pias=pias,
        success=success,
        error=error
    )


# 🔹 Fetch Batches based on PIA
@app.route('/get_batches/<pia_prn>')
def get_batches(pia_prn):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT batch_code 
        FROM batch
        WHERE pia_prn = %s
    """, (pia_prn,))

    batches = cur.fetchall()

    # ✅ FIX: convert to JSON format
    batch_list = [{"batch_code": b[0]} for b in batches]

    return jsonify(batch_list)

@app.route('/get_sanction_by_pia/<pia_prn>')
def get_sanction_by_pia(pia_prn):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT job_role, total_duration, ojt_duration
        FROM sanction_order
        WHERE pia_prn = %s
        ORDER BY sanction_order_no DESC
        LIMIT 1
    """, (pia_prn,))

    row = cur.fetchone()

    if row:
        return jsonify({
            "job_role": row[0],
            "total_duration": row[1],
            "ojt_duration": row[2]
        })
    else:
        return jsonify({})
#Edit Candidate
@app.route('/edit-candidate', methods=['GET', 'POST'])
def edit_candidate():
    candidate_id = request.args.get('id')
    cur = mysql.connection.cursor(DictCursor)
    if request.method == 'POST':
        name = request.form['name']
        gender = request.form['gender']
        category = request.form['category']
        district = request.form['district']
        present_address = request.form['present_address']
        permanent_address = request.form['permanent_address']
        contact = request.form['contact']
        alternate_contact = request.form['alternate_contact']
        dob = request.form['dob']
        pwd = request.form['pwd']

        
        cur.execute("""
            UPDATE candidates 
            SET name=%s, gender=%s, category=%s, district=%s,
                present_address=%s, permanent_address=%s,
                contact_details=%s, alternate_contact=%s,
                dob=%s, pwd_status=%s
            WHERE id=%s
        """, (name, gender, category, district, present_address,
              permanent_address, contact, alternate_contact,
              dob, pwd, candidate_id))

        cur.commit()

        return redirect(request.referrer)

    # GET request → fetch data
    
    cur.execute("SELECT * FROM candidates WHERE id=%s", (candidate_id,))
    candidate = cur.fetchone()

    return render_template('edit_candidate.html', c=candidate)

#Delete Candidate 
@app.route('/delete-candidate')
def delete_candidate():
    candidate_id = request.args.get('id')
    cur = mysql.connection.cursor()
   
    cur.execute("DELETE FROM candidates WHERE id=%s", (candidate_id,))
    mysql.connection.commit()

    return redirect(request.referrer)
#All Candidates
@app.route('/all-candidates')
def all_candidates():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            id,              -- 0
            name,            -- 1
            gender,          -- 2
            category,        -- 3
            district,        -- 4
            contact_details, -- 5
            enrollment_date, -- 6
            DATEDIFF(CURDATE(), enrollment_date) AS days_passed -- 7 ✅
        FROM candidates
    """)

    candidates = cur.fetchall()

    return render_template('all_candidates.html', candidates=candidates)

#Download candidate route
import csv
from flask import Response

@app.route('/download-candidates')
def download_candidates():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            id, name, gender, category, state, district,
            contact_details, enrollment_date
        FROM candidates
    """)

    data = cur.fetchall()

    def generate():
        yield 'ID,Name,Gender,Category,State,District,Contact,Enrollment Date\n'
        for row in data:
            yield ','.join(str(x) for x in row) + '\n'

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=candidates.csv"})

#Update Candidate
@app.route('/update-candidate', methods=['POST'])
def update_candidate():
    candidate_id = request.form.get('id')

    cur = mysql.connection.cursor()

    cur.execute("SELECT batch_id FROM candidates WHERE id=%s", (candidate_id,))
    result = cur.fetchone()
    batch_id = result[0]

    # form data
    name = request.form.get('name')
    gender = request.form.get('gender')
    category = request.form.get('category')
    district = request.form.get('district')
    present_address = request.form.get('present_address')
    permanent_address = request.form.get('permanent_address')
    contact = request.form.get('contact')
    alternate_contact = request.form.get('alternate_contact')
    dob = request.form.get('dob')
    pwd = request.form.get('pwd')

    # safety fallback
    if pwd not in ['Y', 'N']:
        pwd = 'N'

    # UPDATE
    cur.execute("""
        UPDATE candidates SET
            name=%s, gender=%s, category=%s, district=%s,
            present_address=%s, permanent_address=%s,
            contact_details=%s, alternate_contact=%s,
            dob=%s, pwd_status=%s
        WHERE id=%s
    """, (
        name, gender, category, district,
        present_address, permanent_address,
        contact, alternate_contact,
        dob, pwd, candidate_id
    ))

    mysql.connection.commit()
    cur.close()
    return redirect(url_for('batch_details', batch_id=batch_id))

@app.route('/view-candidates')
def view_candidates():
    batch_id = request.args.get('batch_id')

    cur = mysql.connection.cursor()

    if batch_id:
        #Candidates for specific batch
        cur.execute("""
            SELECT id, name, category, gender, pwd_status
            FROM candidates
            WHERE batch_id=%s
        """, (batch_id,))
    else:
        # 🔹 All candidates
        cur.execute("""
            SELECT id, name, category, gender, pwd_status
            FROM candidates
        """)

    candidates = cur.fetchall()

    return render_template('view_candidates.html', candidates=candidates)

# UPLOAD EXCEL
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        df = pd.read_excel(file)

        cur = mysql.connection.cursor()

        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO candidates
                (name, gender, category, pwd_status, state, enrollment_date, batch_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                row['Name'],
                row['Gender'],
                row['Category'],
                row['PwD'],
                row['State'],
                row['Enrollment_Date'],
                row['Batch_ID']
            ))

        mysql.connection.commit()
        return redirect('/dashboard')

    return render_template('upload.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_msg = request.json.get('message', '').lower()

        cur = mysql.connection.cursor()

        # 🔹 Fetch all FAQs
        cur.execute("SELECT question, answer FROM faqs")
        faqs = cur.fetchall()

        reply = None

        # 🔍 Match user question with DB FAQs
        for faq in faqs:
            question = faq[0].lower()
            answer = faq[1]

            if question in user_msg:
                reply = answer
                break

        # ==========================
        # 🔹 Optional Dynamic Data
        # ==========================
        if not reply:
            if "total batch" in user_msg:
                cur.execute("SELECT COUNT(*) FROM batch")
                total = cur.fetchone()[0]
                reply = f"Total batches are {total}"

            elif "active batch" in user_msg:
                cur.execute("""
                    SELECT COUNT(*) FROM batch
                    WHERE DATEDIFF(CURDATE(), registration_date) < 10
                """)
                active = cur.fetchone()[0]
                reply = f"Active batches are {active}"

            elif "freezed batch" in user_msg:
                cur.execute("""
                    SELECT COUNT(*) FROM batch
                    WHERE DATEDIFF(CURDATE(), registration_date) >= 10
                """)
                freezed = cur.fetchone()[0]
                reply = f"Freezed batches are {freezed}"

        # Default fallback
        if not reply:
            reply = "Sorry, I didn't understand. Please ask from available FAQs."

        return jsonify({"reply": reply})

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"reply": "⚠️ Server error"})

@app.route('/get-faqs')
def get_faqs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT question FROM faqs")
    faqs = [row[0] for row in cur.fetchall()]
    return jsonify(faqs)

#LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


#RUN

if __name__ == '__main__':
    app.run(debug=True)