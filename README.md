# Philippines Jurisprudence Scraper

This is a Python-based web scraper that collects jurisprudence data from lawphil.net and stores it in a MySQL database.

## Prerequisites

- Python 3.8+
- MySQL Server
- Chrome Browser (for Selenium WebDriver)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ph-jurisprudence-scraper
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
- Create a new MySQL database named `jurisprudence`
- Copy `.env.example` to `.env` and update the database credentials:
```bash
cp .env.example .env
```

## Usage

Run the scraper:
```bash
python scraper.py
```

The scraper will:
1. Visit https://lawphil.net/judjuris/judjuris.html
2. Navigate through years and months
3. Extract case information
4. Save data to the MySQL database

## Data Structure

The scraped data is stored in a `cases` table with the following structure:
- id (INT, AUTO_INCREMENT)
- title (VARCHAR)
- case_date (DATE)
- content (TEXT)
- year (INT)
- month (VARCHAR)
- url (VARCHAR)
- created_at (TIMESTAMP)

## Logging

The scraper logs its activity to both:
- Console output
- `scraper.log` file

## Error Handling

The scraper includes error handling for:
- Database connection issues
- Web scraping failures
- Network timeouts

## Note

Please be mindful of the website's terms of service and implement appropriate delays between requests to avoid overwhelming the server. 