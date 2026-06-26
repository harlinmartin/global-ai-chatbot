import json
from groq import AsyncGroq
from config import settings

async def extract_facts(user_message: str) -> list[str]:
    """
    Extract personal facts, preferences, or important context from the user's message.
    Returns a list of extracted facts. Returns an empty list if no facts are found.
    """
    # Only run extraction if Groq API key is available
    if not settings.groq_api_key:
        return []

    client = AsyncGroq(api_key=settings.groq_api_key)
    
    prompt = f"""
    You are a Memory Extraction Assistant.
    Analyze the user's message and extract any personal facts, preferences, or important context that would be useful to remember for future conversations.
    Focus on things like: names, locations, job titles, favorite things, coding preferences, languages, personal situations, formatting requests.
    If the message is just a general question or greeting with no personal facts, return an empty array.
    
    Format the output strictly as a JSON object with a single key "facts" containing an array of strings.
    Example: {{"facts": ["User's name is John", "User prefers Python"]}}
    If no facts: {{"facts": []}}
    
    User message: "{user_message}"
    """
    
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=256,
        )
        
        content = response.choices[0].message.content
        if content:
            data = json.loads(content)
            return data.get("facts", [])
    except Exception as e:
        print(f"Memory extraction failed: {e}")
        
    return []

async def background_process_memory(user_message: str, workspace_id):
    """
    Background task to extract and save memory facts.
    """
    facts = await extract_facts(user_message)
    if facts:
        from database import async_session_maker
        from chat.models import Memory
        try:
            async with async_session_maker() as session:
                for fact in facts:
                    new_memory = Memory(workspace_id=workspace_id, fact=fact)
                    session.add(new_memory)
                await session.commit()
        except Exception as e:
            print(f"Failed to save memories: {e}")
