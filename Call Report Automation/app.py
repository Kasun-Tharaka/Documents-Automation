import streamlit as st
import pandas as pd
from io import BytesIO

# Set page configurations
st.set_page_config(page_title="Call Report Automator", layout="wide")
st.title("📞 Call Center Report Generator")
st.write("Upload your raw Mobitel mcallcenter export to generate clean summaries instantly.")

# --- Hardcoded Agent Mapping ---
AGENT_MAPPING = {
    "706825248": "Manuranga",
    "706868865": "Aurora",
    "706868599": "Susanthaaiya",
    "706868499": "home",
    "706825249": "Anusha",
    "706868899": "Isuru",
    "706731126": "Akila",
    "706731127": "Amila",
    "706731130": "Udayanga",
    "706731128": "Thimila",
    "706731129": "Rasindu",
    "706156527": "Poojaya",
    "706116270": "Rajitha",
    "706974725": "JananiHR",
    "706134415": "Anupama",
    "706134416": "RasinduNew",
    "706924763": "null",
    "701087212": "Indika",
    "712545444": "Danwatte",
    "717378709": "Buddhika",
    "717686800": "Saranga",
    "711315482": "MDDivert",
    "716767922": "Rohan",
    "716767925": "Dilmi",
    "716767929": "Nilanthi",
    "711730057": "Dilki",
    "711730035": "Piyumi",
    "710425298": "Binara",
    "711348112": "Tharidu",
    "711348117": "Upul",
    "711348105": "Mihila"
}

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Global Filter Options - UPDATED with "ANY"
    st.subheader("Event Filter")
    selected_event = st.selectbox(
        "Select Event for Report Matrix", 
        ["ANY", "ABANDON", "CALL_COMPLETED"], 
        index=0
    )

    # Display the hardcoded list for reference safely
    with st.expander("View Agent Directory"):
        mapping_df = pd.DataFrame(list(AGENT_MAPPING.items()), columns=["Number", "Name"])
        st.table(mapping_df)

# --- Main App: File Upload & Report Processing ---
uploaded_file = st.file_uploader("Upload Raw System Export (.xlsx or .csv)", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        # Check file extension and load accordingly
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            raw_df = pd.read_excel(uploaded_file)
            
        raw_df.columns = raw_df.columns.str.strip() 
        
        # Standardize column naming variations if present
        raw_df.rename(columns={'Agent.': 'Agent', 'CallerId.': 'CallerId'}, inplace=True)
        
        # Data Validation check
        required_cols = ['Agent', 'CallerId', 'Start Time', 'Event']
        missing_cols = [col for col in required_cols if col not in raw_df.columns]
        
        if missing_cols:
            st.error(f"Missing required columns in upload file: {missing_cols}")
        else:
            # 1. Standardize text and map Agent Numbers to Names
            raw_df['Agent_Str'] = raw_df['Agent'].astype(str).str.split('.').str[0].str.strip()
            raw_df['Agent Name'] = raw_df['Agent_Str'].map(AGENT_MAPPING).fillna(raw_df['Agent_Str'])
            
            # Dynamic Agent Selection Filter
            unique_agents_in_file = sorted(raw_df['Agent Name'].dropna().unique().tolist())
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("🎯 Target Agents")
            selected_agents = st.sidebar.multiselect(
                "Select agents to include in the report:",
                options=unique_agents_in_file,
                default=unique_agents_in_file 
            )

            # 2. Process Dates
            raw_df['DateTime'] = pd.to_datetime(raw_df['Start Time'])
            raw_df['Date_Str'] = raw_df['DateTime'].dt.strftime('%d-%b') 
            
            # --- UPDATED: Filter logic to handle the "ANY" option ---
            if selected_event == "ANY":
                # Include all rows matching the agent filter regardless of event type
                filtered_df = raw_df[raw_df['Agent Name'].isin(selected_agents)]
                report_title = "All Combined Events"
            else:
                # Include only the specific event type selected
                filtered_df = raw_df[
                    (raw_df['Event'].astype(str).str.upper() == selected_event.upper()) &
                    (raw_df['Agent Name'].isin(selected_agents))
                ]
                report_title = f"{selected_event} Events"
            
            # Sort columns chronologically by date sequence
            unique_dates = sorted(raw_df['DateTime'].dt.date.unique())
            date_columns_order = [d.strftime('%d-%b') for d in unique_dates]

            # -------------------------------------------------------------
            # REPORT 1: Pivot Matrix Table
            # -------------------------------------------------------------
            st.subheader(f"📊 Table 1: {report_title} Call Report Matrix")
            
            if not filtered_df.empty:
                pivot_df = filtered_df.pivot_table(
                    index='Agent Name', 
                    columns='Date_Str', 
                    values='CallerId', 
                    aggfunc='count', 
                    fill_value=0
                )
                
                # Reindex columns to guarantee precise ascending date order
                pivot_df = pivot_df.reindex(columns=date_columns_order, fill_value=0)
                
                # Add Total Column
                pivot_df['Total'] = pivot_df.sum(axis=1)
                
                # Render clean HTML native layout table
                st.table(pivot_df)
            else:
                st.warning(f"No records found matching criteria for the selected agents.")
                pivot_df = pd.DataFrame()

            # -------------------------------------------------------------
            # REPORT 2: Caller ID Tracker List
            # -------------------------------------------------------------
            st.subheader(f"📞 Table 2: Customer CallerIds Tracker Group ({report_title})")
            
            if not filtered_df.empty:
                agent_lists = {}
                max_len = 0
                
                for agent in filtered_df['Agent Name'].unique():
                    c_ids = filtered_df[filtered_df['Agent Name'] == agent]['CallerId'].dropna().astype(str).tolist()
                    c_ids = [c.split('.')[0] for c in c_ids]
                    agent_lists[agent] = c_ids
                    if len(c_ids) > max_len:
                        max_len = len(c_ids)
                
                for agent in agent_lists:
                    agent_lists[agent] = agent_lists[agent] + [""] * (max_len - len(agent_lists[agent]))
                
                caller_id_df = pd.DataFrame(agent_lists)
                
                # Render as clean HTML table with scroll wrapper to fix graphics issues
                st.markdown(
                    f'<div style="overflow-x:auto; max-height:400px; overflow-y:auto;">'
                    f'{caller_id_df.to_html(index=False, classes="table table-striped")}'
                    f'</div>', 
                    unsafe_allow_html=True
                )
            else:
                caller_id_df = pd.DataFrame()

            # -------------------------------------------------------------
            # EXPORT BUTTONS
            # -------------------------------------------------------------
            st.markdown("---")
            st.subheader("📥 Export Outputs")
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                if not pivot_df.empty:
                    pivot_df.to_excel(writer, sheet_name="Call Count Summary")
                if not caller_id_df.empty:
                    caller_id_df.to_excel(writer, sheet_name="Target Caller ID Lists", index=False)
            
            processed_data = output.getvalue()
            
            if not pivot_df.empty or not caller_id_df.empty:
                st.download_button(
                    label="📥 Download Generated Reports as Excel",
                    data=processed_data,
                    file_name=f"Automated_{selected_event}_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
    except Exception as e:
        st.error(f"Error processing file: {e}")