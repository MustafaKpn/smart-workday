# smart-workday 🚀

[![GitHub Actions Workflow Status](https://github.com/MustafaKpn/smart-workday/actions/workflows/scrape.yml/badge.svg)](https://github.com/MustafaKpn/smart-workday/actions/workflows/scrape.yml)

`smart-workday` is an intelligent job scraping and notification system designed to streamline your job search on Workday platforms. Leveraging Python, AI-powered parsing (Groq), and automated workflows (GitHub Actions), it efficiently scrapes job postings, extracts relevant information, and notifies you directly via Telegram about new opportunities matching your criteria.

## ✨ Key Features & Benefits

*   **Automated Workday Scraping**: Periodically scrapes job listings from specified Workday career pages.
*   **AI-Powered Job Parsing**: Utilizes Groq (LLM) for intelligent parsing and matching of job descriptions against predefined preferences.
*   **Telegram Notifications**: Delivers real-time alerts for new job postings directly to your Telegram chat.
*   **Configurable Targets**: Easily define and manage target Workday URLs and job criteria.
*   **Persistent Storage**: Stores scraped job data in a local SQLite database (`jobs.db`) for historical tracking and analysis.
*   **CI/CD Integration**: Automated scraping and processing via GitHub Actions, ensuring up-to-date job data with minimal manual intervention.
*   **Pythonic & Extensible**: Built with Python, making it easy to extend, customize, and integrate with other services.

## 🛠️ Prerequisites & Dependencies

Before you begin, ensure you have the following installed:

*   **Python 3.8+**: The project is built using Python.
*   **Git**: For cloning the repository.
*   **pip**: Python package installer (usually comes with Python).


To install all dependencies (assuming you created `requirements.txt`):

```bash
pip install -r requirements.txt
```

## 🚀 Installation & Setup Instructions

Follow these steps to get `smart-workday` up and running on your local machine:

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/MustafaKpn/smart-workday.git
    cd smart-workday
    ```

2.  **Create a Virtual Environment**:
    It's highly recommended to use a virtual environment to manage project dependencies.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    Install the necessary Python packages.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the root of your project directory to store sensitive information and configurations.
    ```ini
    # .env
    GROQ_API_KEY="YOUR_GROQ_API_KEY"
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID" # Your user ID or a group chat ID
    ```
    *   **`GROQ_API_KEY`**: Obtain this from the [Groq console](https://console.groq.com/). This is crucial for the `GroqMatcher` to function.
    *   **`TELEGRAM_BOT_TOKEN`**: Create a new bot using [@BotFather](https://t.me/botfather) on Telegram to get your unique token.
    *   **`TELEGRAM_CHAT_ID`**: After you obtain your bot token, send a message to the bot first, then open this URL in a browser https://api.telegram.org/bot{our_bot_token}/getUpdates
   You will get a JSON response. You can find the chat ID there.

5.  **Define Scraping Targets**:
    The system needs to know which Workday URLs to scrape and what criteria to use. Based on `app.utils.config_loader.load_active_targets`, you will need to provide a configuration file (e.g., `targets.json`).
    *Example `targets.json` (hypothetical structure):*
    ```json
    [
      {
        "name": "Company A Software Engineering",
        "url": "https://companyA.workday.com/recruiting/companyA/jobs/HTML/jobs",
        "keywords": ["Software Engineer", "Python", "Backend", "Remote"],
        "min_salary": 90000,
        "location": "Any"
      },
      {
        "name": "Company B Data Science",
        "url": "https://companyB.workday.com/recruiting/companyB/careers/jobs",
        "keywords": ["Data Scientist", "Machine Learning", "AI"],
        "location": "New York"
      }
    ]
    ```
    *Note: The exact format and location of this `targets` file depend on the implementation of `load_active_targets`. This is a suggested structure.*

## ➡️ Usage Examples

### Running the Scraper Manually

To execute the job scraping, parsing, and notification process on demand:

```bash
python app/main.py
```

This command performs the following actions:
1.  **Loads Targets**: Reads your configured Workday scraping targets.
2.  **Scrapes Jobs**: Fetches new job postings from the specified Workday URLs.
3.  **Parses with LLM**: Utilizes the `GroqMatcher` (an LLM-powered parser) to analyze job descriptions and extract relevant information.
4.  **Stores Data**: Saves unique and relevant job details into the `jobs.db` SQLite database.
5.  **Notifies**: Sends Telegram notifications for newly discovered job postings that match your defined criteria.

### Automated Scraping with GitHub Actions

This repository includes a GitHub Actions workflow (`.github/workflows/scrape.yml`) designed to automate the scraping process. This enables continuous monitoring of job postings without manual intervention.

To utilize the automated workflow:

1.  **Add GitHub Secrets**: Store your sensitive environment variables (`GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) as [GitHub Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets) in your repository settings (`Settings > Secrets > Actions`).
2.  **Trigger Workflow**: The `scrape.yml` workflow can be configured to run on a schedule (e.g., daily, hourly) or triggered manually via the GitHub Actions tab.

## ⚙️ Configuration Options

The `smart-workday` project offers several configuration points, primarily through environment variables:

*   **`DATABASE_URL`**:
    *   **Description**: Specifies the database connection string.
    *   **Default**: `sqlite:///jobs.db` (a SQLite database file located in the project root).
    *   **Location**: Can be set in `.env` file or as a GitHub Secret.
    *   **Example**: `postgresql://user:password@host:port/dbname`
*   **`GROQ_API_KEY`**:
    *   **Description**: Your API key for authentication with the Groq LLM service.
    *   **Location**: Must be set in `.env` file or as a GitHub Secret.
*   **`TELEGRAM_BOT_TOKEN`**:
    *   **Description**: The unique token for your Telegram Bot, obtained from BotFather.
    *   **Location**: Must be set in `.env` file or as a GitHub Secret.
*   **`TELEGRAM_CHAT_ID`**:
    *   **Description**: The Telegram user ID or group chat ID where job notifications will be sent.
    *   **Location**: Must be set in `.env` file or as a GitHub Secret.
*   **Scraping Targets Configuration**:
    *   **Description**: A file (e.g., `targets.json`) that defines the Workday URLs to scrape, along with keywords, desired salary ranges, locations, and other criteria for job matching.
    *   **Location**: Typically placed in the project root or a `config` directory. The exact path is determined by the `load_active_targets` implementation.

## 🤝 Contributing Guidelines

We welcome contributions to `smart-workday`! If you have suggestions for improvements, new features, or bug fixes, please follow these guidelines:

1.  **Fork the repository** on GitHub.
2.  **Clone your forked repository** to your local development environment.
    ```bash
    git clone https://github.com/YourUsername/smart-workday.git
    cd smart-workday
    ```
3.  **Create a new branch** for your specific feature or bug fix:
    ```bash
    git checkout -b feature/your-feature-name
    # or for a bug fix:
    git checkout -b bugfix/issue-description
    ```
4.  **Make your changes**, ensuring they adhere to the project's overall code style and structure.
5.  **Test your changes** thoroughly to ensure they don't introduce new issues.
6.  **Commit your changes** with a clear, concise, and descriptive commit message.
    ```bash
    git commit -m "feat: Add new feature for X"
    # or:
    git commit -m "fix: Resolve issue with Y"
    ```
7.  **Push your branch** to your forked repository:
    ```bash
    git push origin feature/your-feature-name
    ```
8.  **Open a Pull Request (PR)** against the `main` branch of the original `smart-workday` repository. Provide a detailed description of your changes and their purpose.

## 📜 License Information

This project is currently **unlicensed**. The owner, MustafaKpn, has not specified a license for this repository.

This means that, by default, all rights are reserved under copyright law. Users may not use, distribute, or modify this code without explicit permission from the copyright holder.

It is strongly recommended that the repository owner chooses an appropriate [open-source license](https://choosealicense.com/) (e.g., MIT, Apache 2.0, GPL) to clarify terms of use and encourage community contributions.

## 🙏 Acknowledgments

*   Built with the versatility and power of **Python**.
*   Leverages **Groq** for high-performance large language model inference, enabling intelligent job parsing.
*   Integrates with the **Telegram Bot API** for efficient and real-time job notifications.
*   Inspired by the need for smarter and more automated job search solutions.
*   Gratitude to the open-source community for providing invaluable tools and resources that make projects like this possible.
