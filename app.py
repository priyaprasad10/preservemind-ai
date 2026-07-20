import streamlit as st
from backend import fetch_user_issues, find_user_by_email, analyze_with_ai

st.set_page_config(page_title="PreserveMind AI", page_icon="🧠", layout="centered")

st.title("🧠 PreserveMind AI")
st.subheader("Employee Exit Intelligence — Knowledge Transfer POC")
st.markdown("---")

email = st.text_input("Enter the departing employee's Jira email:", placeholder="e.g. john.doe@gmail.com")

if st.button("Analyze", use_container_width=True):
    if not email:
        st.warning("Please enter an email address.")
    else:
        with st.spinner("Fetching Jira data..."):
            user, err = find_user_by_email(email)
            if err:
                st.error(f"User lookup failed: {err}")
            else:
                st.success(f"Found user: **{user['displayName']}**")
                issues, err2 = fetch_user_issues(user['accountId'])
                if err2:
                    st.error(f"Failed to fetch issues: {err2}")
                else:
                    st.markdown(f"**Total issues found:** {len(issues)}")

                    with st.expander("View Raw Jira Issues"):
                        for issue in issues:
                            f = issue['fields']
                            st.markdown(
                                f"**{issue['key']}** | {f['issuetype']['name']} | "
                                f"{f['summary']} | `{f['status']['name']}`"
                            )

        with st.spinner("Analyzing with AI..."):
            if 'user' in dir() and user and 'issues' in dir() and issues is not None:
                analysis = analyze_with_ai(user['displayName'], issues)
                st.markdown("---")
                st.markdown("## AI Analysis")
                st.markdown(analysis)
