import smtplib
from email.mime.text import MIMEText

# --- FUNKCJA WYSYŁANIA MAILOWEJ (Dodaj ją na początku kodu) ---
def send_email(user_msg, user_contact):
    msg_content = f"New message from FlashCalc user!\n\nContact: {user_contact}\n\nMessage:\n{user_msg}"
    msg = MIMEText(msg_content)
    msg['Subject'] = "⚡ FlashCalc Feedback"
    msg['From'] = st.secrets["EMAIL_USER"]
    msg['To'] = "flashcalc1x2@gmail.com"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
        return True
    except Exception as e:
        return False

# --- SEKCJA W SIDEBARZE ---
with st.sidebar.expander("📬 Contact & Feedback"):
    with st.form("contact_form", clear_on_submit=True):
        st.write("Found a bug? Have a suggestion?")
        user_contact = st.text_input("Your email/nick (optional):", placeholder="so I can reply...")
        user_message = st.text_area("Message:", placeholder="What's on your mind?")
        
        submit_button = st.form_submit_button("Send to FlashCalc", use_container_width=True)
        
        if submit_button:
            if user_message.strip():
                with st.spinner("Sending..."):
                    success = send_email(user_message, user_contact)
                    if success:
                        st.success("Message sent! Thanks for the feedback. ⚡")
                    else:
                        st.error("Oops! Something went wrong. Try again later.")
            else:
                st.warning("Please enter a message before sending.")
    
    st.caption("FlashCalc v1.2.1")