### Overview
A Yu-gi-Oh! card search Discord bot powered by semantic search technology via Supabase and PGVector.

### Tools Used
- **Replit** - Host site
- **Discord.py** - API for Discord bots
- **Flask** - Web server
- **Google Drive** - Image and files host
- **MiniLM** - Text vectorizer for user queries at runtime, checked against vectorized card name database upon request
- **Supabase** - Vectorstore for semantic search queries and general SQL searches

### Features
Searches cards using the `_ygo <query>` command semantically, making archetypal searches much easier and offers some typo resistance. For example, searching the card `Kashtira Ariseheart` correctly identifies the card `Kashtira Arise-heart` despite the hyphen throwing off string matches.
