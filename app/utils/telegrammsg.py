#app/utils/telegram_message.py


def clean(text):
    return str(text).replace("<", "&lt;").replace(">", "&gt;")

def build_telegram_message(job_info, processed):
    reasoning = processed.get("reasoning", "No reasoning provided")
    message = (
        f"🔥 <b>New Job Match</b>\n\n"
        f"<b>{clean(job_info.get('title', 'No title'))}</b>\n"
        f"{clean(job_info.get('company', 'No company'))}\n\n"
        f"<b>Score:</b> {processed.get('score', 0)}/10\n\n"
        f"<b>Why:</b> {reasoning}\n\n"
        f"🔗 {clean(job_info.get('url', 'No URL'))}")
    
    return message