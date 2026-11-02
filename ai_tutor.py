import os
from database import get_topics, get_journal

def ask_tutor(user_id, question):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return 'The AI tutor is not enabled yet. Set OPENAI_API_KEY and restart the app. Your tracker features work without it.'
    from openai import OpenAI
    topics = get_topics(user_id)
    journal = get_journal(user_id)
    topic_context = '\n'.join(f"- {t['title']} ({t['status']}): {t['description']}" for t in topics) or 'No topics added.'
    journal_context = '\n'.join(f"- {j['title']}: {j['content'][:500]}" for j in journal[:5]) or 'No journal notes yet.'
    prompt = f'''You are a patient, encouraging Python tutor for a beginner who wants to become a Python developer.
Explain in simple steps, use short code examples, point out common mistakes, and suggest a small practice task.
Learner's topics:\n{topic_context}\nRecent journal notes:\n{journal_context}\nQuestion: {question}'''
    client = OpenAI(api_key=api_key)
    result = client.responses.create(model='gpt-4.1-mini', input=prompt)
    return result.output_text
