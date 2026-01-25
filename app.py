import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import pandas as pd
from datetime import datetime
import io

# PDF/Excel Libraries
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, Border, Side, PatternFill
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ================= CONFIGURATION =================
st.set_page_config(page_title="Interview Scheduler", layout="wide", page_icon="📅")

# --- Load secrets from environment variables ---
creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
sheet_id = os.getenv("GOOGLE_SHEET_ID")

if not creds_json:
    st.error("❌ Missing GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable.")
    st.stop()
if not sheet_id:
    st.error("❌ Missing GOOGLE_SHEET_ID environment variable.")
    st.stop()

# --- Connect to Google Sheets ---
try:
    creds_dict = json.loads(creds_json)
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).sheet1
except Exception as e:
    st.error(f"❌ Google Sheets connection failed: {str(e)}")
    st.stop()

# ================= TIME SLOT GENERATOR =================
TIME_SLOTS = []
for h in range(11, 22):
    for m in (0, 30):
        if h == 21 and m == 30:
            continue
        TIME_SLOTS.append(f"{h:02d}:{m:02d}")

# ================= DATA FUNCTIONS =================

def clean_dataframe(df):
    """Ensure consistent string format and valid date/time"""
    df = df.astype(str)
    for col in df.columns:
        df[col] = df[col].replace(['NaT', 'nan', 'None', '<NA>'], '')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:00', errors='coerce').fillna(
        pd.to_datetime(df['Time'], format='%H:%M', errors='coerce')
    ).dt.strftime('%H:%M')
    return df.fillna("")

def load_sheet_as_df():
    """Load entire sheet as DataFrame"""
    try:
        records = sheet.get_all_records()
        if not records:
            return pd.DataFrame(columns=["Name", "ID", "Date", "Time", "Notes"])
        df = pd.DataFrame(records)
        return clean_dataframe(df)
    except Exception as e:
        st.error(f"Failed to read sheet: {e}")
        return pd.DataFrame(columns=["Name", "ID", "Date", "Time", "Notes"])

def overwrite_sheet_with_df(df):
    """Replace entire sheet content"""
    try:
        clean_df = clean_dataframe(df)
        values = [clean_df.columns.tolist()] + clean_df.values.tolist()
        sheet.clear()
        sheet.update(values)
        return True
    except Exception as e:
        st.error(f"Write failed: {e}")
        return False

def append_rows_to_sheet(df_new):
    """Append new rows only"""
    try:
        clean_df = clean_dataframe(df_new)
        for _, row in clean_df.iterrows():
            sheet.append_row(row.tolist())
        return True
    except Exception as e:
        st.error(f"Append failed: {e}")
        return False

# ================= SESSION STATE & REFRESH =================

def initialize_session():
    if 'data' not in st.session_state:
        with st.spinner("🔄 Loading data from Google Sheets..."):
            st.session_state.data = load_sheet_as_df()
        st.rerun()
    if 'form_id' not in st.session_state:
        st.session_state.form_id = 0
    if 'data_revision' not in st.session_state:
        st.session_state.data_revision = 0

def refresh_data():
    st.session_state.data = load_sheet_as_df()
    st.session_state.data_revision += 1
    st.toast("✅ Data synced!", icon="🔄")

# ================= MAIN APP =================

initialize_session()
df = st.session_state.data

st.title("☁️ 雲端面試預約系統")

if st.button("🔄 Sync Latest Data", type="primary"):
    refresh_data()
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📅 Calendar", "📝 Add/Edit", "⚙️ Export"])

# --- TAB 1: CALENDAR ---
with tab1:
    if not df.empty:
        events = []
        for idx, row in df.iterrows():
            date_str = str(row.get('Date', ''))
            time_str = str(row.get('Time', ''))
            if len(date_str) == 10 and len(time_str) == 5:
                try:
                    start_iso = f"{date_str}T{time_str}"
                    events.append({
                        "id": str(idx),
                        "title": row.get('Name', ''),
                        "start": start_iso,
                        "extendedProps": {
                            "description": f"ID: {row.get('ID', '')} | Notes: {row.get('Notes', '')}"
                        }
                    })
                except:
                    continue

        from streamlit_calendar import calendar
        calendar_key = f"cal_{st.session_state.data_revision}"
        calendar(
            events=events,
            options={
                "initialView": "dayGridMonth",
                "height": "750px",
                "headerToolbar": {
                    "left": "prev,next today",
                    "center": "title",
                    "right": "dayGridMonth,listMonth"
                },
                "eventTimeFormat": {"hour": "2-digit", "minute": "2-digit", "hour12": False},
            },
            key=calendar_key
        )
    else:
        st.info("No data yet.")

# --- TAB 2: ADD / EDIT ---
with tab2:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("➕ Add Appointment")
        limit = st.number_input("Max per slot (0 = unlimited)", min_value=0, value=0)

        with st.form("add_form"):
            name = st.text_input("Name")
            c_id = st.text_input("ID")
            d = st.date_input("Date", min_value=datetime.today())
            t_str = st.selectbox("Time", TIME_SLOTS)
            notes = st.text_area("Notes")

            if st.form_submit_button("💾 Save to Cloud"):
                if not name:
                    st.error("Name is required")
                else:
                    if limit > 0:
                        date_key = d.strftime("%Y-%m-%d")
                        count = len(df[(df['Date'] == date_key) & (df['Time'] == t_str)])
                        if count >= limit:
                            st.error(f"Slot full ({count}/{limit})")
                        else:
                            new_row = pd.DataFrame([{
                                "Name": name,
                                "ID": c_id,
                                "Date": date_key,
                                "Time": t_str,
                                "Notes": notes
                            }])
                            if append_rows_to_sheet(new_row):
                                st.session_state.data = load_sheet_as_df()
                                st.session_state.data_revision += 1
                                st.toast("✅ Added!", icon="🎉")
                                st.rerun()
                    else:
                        new_row = pd.DataFrame([{
                            "Name": name,
                            "ID": c_id,
                            "Date": d.strftime("%Y-%m-%d"),
                            "Time": t_str,
                            "Notes": notes
                        }])
                        if append_rows_to_sheet(new_row):
                            st.session_state.data = load_sheet_as_df()
                            st.session_state.data_revision += 1
                            st.toast("✅ Added!", icon="🎉")
                            st.rerun()

    with c2:
        st.subheader("✏️ Edit Grid")
        st.warning("⚠️ Always sync before editing to avoid conflicts!")

        edit_df = df.copy()
        edit_df["Date"] = pd.to_datetime(edit_df["Date"], errors='coerce').dt.date
        edit_df["Time"] = pd.to_datetime(edit_df["Time"], format='%H:%M', errors='coerce').dt.time

        edited = st.data_editor(
            edit_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Time": st.column_config.TimeColumn("Time", format="HH:mm", step=1800),
                "Name": st.column_config.TextColumn("Name"),
                "ID": st.column_config.TextColumn("ID"),
                "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "Notes": st.column_config.TextColumn("Notes"),
            }
        )

        if st.button("💾 Save Changes (Overwrite)"):
            clean_edited = edited.copy()
            clean_edited['Date'] = clean_edited['Date'].apply(
                lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else ''
            )
            clean_edited['Time'] = clean_edited['Time'].apply(
                lambda x: x.strftime('%H:%M') if pd.notnull(x) else ''
            )
            if overwrite_sheet_with_df(clean_edited):
                st.session_state.data = clean_edited
                st.session_state.data_revision += 1
                st.toast("✅ Saved!", icon="💾")

# --- TAB 3: EXPORT ---
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 Visual Reports")
        if not df.empty:
            def generate_visual_pdf(df):
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
                elements = []
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16)
                cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, leading=11)

                df['dt'] = pd.to_datetime(df['Date'] + " " + df['Time'], errors='coerce')
                df = df.dropna(subset=['dt'])
                import calendar as py_cal
                cal = py_cal.Calendar(firstweekday=6)

                for period in sorted(df['dt'].dt.to_period('M').unique()):
                    year, month = period.year, period.month
                    elements.append(Paragraph(f"<b>{period.strftime('%B %Y')}</b>", title_style))
                    elements.append(Spacer(1, 10))

                    month_cal = cal.monthdayscalendar(year, month)
                    table_data = [["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]]
                    row_heights = [20]

                    for week in month_cal:
                        row_cells = []
                        max_entries = 0
                        for day in week:
                            if day == 0:
                                row_cells.append("")
                            else:
                                day_str = f"{year}-{month:02d}-{day:02d}"
                                day_data = df[df['Date'] == day_str].sort_values('Time')
                                cell_text = f"<b>{day}</b>"
                                if not day_data.empty:
                                    lines = [f"{r['Name']}\n{r['Time']}" for _, r in day_data.iterrows()]
                                    cell_text += "\n\n" + "\n".join(lines)
                                    max_entries = max(max_entries, len(day_data))
                                row_cells.append(Paragraph(cell_text.replace("\n", "<br/>"), cell_style))
                        table_data.append(row_cells)
                        row_heights.append(40 + (max_entries * 25))

                    table = Table(table_data, colWidths=[110]*7, rowHeights=row_heights)
                    table.setStyle(TableStyle([
                        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 20))

                doc.build(elements)
                buffer.seek(0)
                return buffer

            st.download_button(
                "📄 Download PDF Calendar",
                generate_visual_pdf(df),
                "interview_calendar.pdf",
                "application/pdf"
            )

    with col2:
        st.markdown("### 💾 Raw Data")
        if not df.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
            buffer.seek(0)
            st.download_button(
                "📥 Download Raw Data (.xlsx)",
                buffer,
                "raw_data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.divider()
        st.markdown("#### 📥 Import Excel (append only)")
        up = st.file_uploader("Upload .xlsx", type="xlsx")
        if up and st.button("Import"):
            try:
                imp_df = pd.read_excel(up, dtype=str).fillna("")
                if 'Name' in imp_df.columns:
                    if append_rows_to_sheet(imp_df):
                        st.success("✅ Imported!")
                        st.session_state.data = load_sheet_as_df()
                        st.session_state.data_revision += 1
                        st.rerun()
                else:
                    st.error("❌ Missing 'Name' column")
            except Exception as e:
                st.error(f"Import failed: {e}")
