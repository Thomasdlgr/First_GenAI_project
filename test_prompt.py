import os
from openai import OpenAI
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer la clé API depuis la variable d'environnement
api_key = os.getenv("OPENAI_API_KEY")
# Initialiser le client OpenAI
client = OpenAI(api_key=api_key)

def chat_with_gpt(message):
    """
    Envoie un message à ChatGPT et retourne la réponse
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # ou "gpt-4" pour une version plus récente
            messages=[
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur: {str(e)}"

if __name__ == "__main__":
    # Envoyer "Hello world" à ChatGPT
    message = "Hello world"
    print(f"Envoi du message: {message}")
    print("-" * 50)
    
    response = chat_with_gpt(message)
    print(f"Réponse de ChatGPT:\n{response}")

