# Join Our Discord Server

Join our Discord server: [https://discord.gg/mZzr5TV9gk](https://discord.gg/mZzr5TV9gk) to ask questions, contribute, or use the bot without setting it up yourself!

# Science Bowl Bot

Science Bowl Bot is a Discord bot built with Python that helps users practice answering Science Bowl questions in a fun and competitive way. By using a collection of commands, teams can be formed and compete in answering tossup and bonus questions sourced from the [SciBowlDB API](https://scibowldb.com/about).

## Features

- **Team Commands**
  - `!create [team name]` – Create a team (maximum of 2 teams).
  - `!join [team name]` – Join an existing team.
  - `!leave` – Leave your current team.
  - `!reset` – Reset all teams.
- **Game Commands**
  - `!start` – Start a game session with the current teams.
  - `!end` – End the game and display the final scores (with automatic team reset).
  - `!question` – Get a random Science Bowl question.
  - `!skip` – Skip the current question.
  - To answer a question, simply type `buzz` followed by your answer.
- **Category Commands**
  - `!astro`, `!es`, `!math`, `!energy`, `!bio`, `!chem`, `!physics`, `!gen` – Get questions from specific science categories.
- **Information Commands**
  - `!credits` – Displays credits and information about the bot’s creator.
  - `!altair` – Gives credit to Altair Maine as an inspiration for this bot.
  - `!about` – Provides an overview on how to use the bot along with a list of all available commands.

## How It Works

The bot fetches Science Bowl questions from the [SciBowlDB API](https://scibowldb.com/about). It randomly selects questions based on category (excluding certain categories, like "COMPUTER SCIENCE") and handles parsing of both multiple-choice and short answer formats. When a question is posted, a timer is set using an asynchronous countdown which updates via an embedded message on Discord. Points are tracked per team and additional mechanics such as streak tracking are also implemented.

## Flaws and Limitations

- The bot's answer validation is rudimentary; it only checks if at least one word in your answer matches the correct answer.
- For math questions, the method to determine the correct answer is particularly flawed.
- The Discord bot isn't hosted on a server, so it must always be run on my personal laptop to keep it online.
- Currently, the bot only pulls questions from the API database. There's potential for expansion (e.g., integrating a MongoDB database), but PDF parsing remains challenging.

## Installation

### Prerequisites

- Python 3.8 or higher
- A Discord Bot Token – Create your own bot from the [Discord Developer Portal](https://discord.com/developers/applications)
- [pip](https://pip.pypa.io/en/stable/installation/) for package installation

### Required Python Packages

Install the required packages with pip:

```bash
pip install discord.py python-dotenv requests nest_asyncio
```

### Setup

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/your-repo-name.git
   cd your-repo-name
   ```

2. **Create a `.env` File:**

   In the root of the repository, create a file called `.env` and add your Discord Bot Token:

   ```env
   TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
   ```

3. **Run the Bot:**

   Start the bot by running the main Python file:

   ```bash
   python altairbot_v1_0.py
   ```

   Ensure that your machine’s environment is configured properly and that the Discord intent permissions are set according to the bot’s requirements.

## How to Use the Bot on Discord

1. **Invite the Bot:**
   - Use the OAuth2 URL generated in the Discord Developer Portal to invite the bot to your server.

2. **Team Setup:**
   - Use `!create [team name]` to create a team.
   - Use `!join [team name]` to join a team.
   - You can use `!reset` to clear all teams if needed.

3. **Starting a Game:**
   - Use the `!start` command to begin a game. The bot will fetch a Science Bowl tossup question from the SciBowlDB API.
   - Answer questions by typing `buzz [your answer]`.
   - If a team answers correctly, points are awarded and subsequent bonus questions (if applicable) will be presented.

4. **Other Commands:**
   - The `!about` command displays detailed instructions and a full list of available commands.
   - Use various category commands like `!math`, `!astro`, etc., for questions from specific science categories.
   - Answers are validated either by exact matching or using a similarity metric.

## Code Structure

- **Command Handlers:**  
  The code is organized using Discord.py’s command handler decorators (e.g., `@bot.command`). Each command is responsible for a specific action, such as starting a game, joining teams, or fetching questions.

- **Question Fetching & Timer:**
  - The `fetch_question` function retrieves questions from the SciBowlDB API and sets up an asynchronous timer (via `run_timer`) that updates the remaining time in the question embed.
  - Answers are checked using helper functions like `parse_answer` and `validate_answer`.

- **Team Management & Score Tracking:**
  - Teams are managed using dictionaries to store team members and points.
  - Commands ensure that users can only answer if they belong to a team and track user streaks for consecutive correct answers.

## Credits

- **Question Source:**  
  This bot utilizes the [SciBowlDB API](https://scibowldb.com/about) to source high-quality, diverse Science Bowl questions. Please visit their website for more details.

## Contributing

Contributions are welcome! Feel free to fork the repository and open pull requests with improvements or fixes. When contributing, please follow standard Python coding practices and include clear documentation for any changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For questions, feedback, or support, please join the discord!.

Enjoy practicing Science Bowl and good luck with your competitions!
