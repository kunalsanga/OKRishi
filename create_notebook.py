import json

# Read the extract_answer function from run_extractor.py
with open('run_extractor.py', 'r', encoding='utf-8') as f:
    extractor_code = f.read()

# Extract just the extract_answer function and its dependencies
lines = extractor_code.split('\n')
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'def extract_answer(' in line:
        start_idx = i
    elif start_idx and line.strip() == '' and i > start_idx + 10:
        # Look for end of function (empty line after some content)
        end_idx = i
        break

if start_idx is None:
    # Fallback: include the whole file
    extract_answer_code = extractor_code
else:
    extract_answer_code = '\n'.join(lines[start_idx:end_idx])

# Create the notebook structure
notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Kunal Solution Notebook\n\n",
                "This notebook is self-contained and includes all code needed to reproduce the results.\n\n",
                "## Task Overview\n",
                "You are given:\n",
                "- A CSV file (`claims.csv`) containing **fictional entities** and a type of claim to verify.\n",
                "- A folder of HTML pages (`webpages/`) containing the information needed to answer those claims.\n\n",
                "Your job:\n",
                "1. Implement the function `extract_answer(entity, claim_type, webpages)`.\n",
                "2. For **each claim**, find the correct value from the webpages.\n",
                "3. Assign a confidence score (0–100) for your answer.\n",
                "4. Provide a short evidence snippet from the text supporting your answer.\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "from pathlib import Path\n",
                "import re\n",
                "from typing import Tuple, Optional, List, Dict, Any\n",
                "\n",
                "# Load the claims CSV\n",
                "claims_df = pd.read_csv(\"claims.csv\")\n",
                "\n",
                "print(f\"Loaded {len(claims_df)} claims\")\n",
                "claims_df.head()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Load all HTML pages into a dictionary {filename: content}\n",
                "webpages_dir = Path(\"webpages\")\n",
                "webpages = {}\n",
                "\n",
                "for html_file in webpages_dir.glob(\"*.html\"):\n",
                "    with open(html_file, \"r\", encoding=\"utf-8\") as f:\n",
                "        webpages[html_file.name] = f.read()\n",
                "\n",
                "print(f\"Loaded {len(webpages)} webpages\")\n",
                "list(webpages.keys())[:5]"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Complete extract_answer implementation\n",
                extract_answer_code
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "results = []\n",
                "\n",
                "for _, row in claims_df.iterrows():\n",
                "    claim_id = row[\"id\"]\n",
                "    entity = row[\"entity\"]\n",
                "    claim_type = row[\"claim_type\"]\n",
                "\n",
                "    found_value, confidence_score, evidence_snippet = extract_answer(entity, claim_type, webpages)\n",
                "\n",
                "    results.append({\n",
                "        \"id\": claim_id,\n",
                "        \"found_value\": found_value,\n",
                "        \"confidence_score\": confidence_score,\n",
                "        \"evidence_snippet\": evidence_snippet\n",
                "    })\n",
                "\n",
                "results_df = pd.DataFrame(results)\n",
                "results_df.to_csv(\"results.csv\", index=False)\n",
                "\n",
                "# Also save a submission-named copy\n",
                "first_name = \"Kunal\"\n",
                "results_df.to_csv(f\"{first_name}_results.csv\", index=False)\n",
                "\n",
                "print(\"Saved results.csv with\", len(results_df), \"rows\")\n",
                "results_df.head()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Submission\n",
                "- Submit **both** your completed `.ipynb` notebook **and** the `results.csv` file.\n",
                "- **IMPORTANT:** Name your results file exactly as follows:  \n",
                "  `[FirstName]_results.csv`  \n",
                "  Example: `John_results.csv`\n",
                "- Do not modify the output CSV format or column names.\n",
                "- Ensure your code runs from start to finish without errors.\n",
                "\n",
                "Good luck!\n"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.8.5"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

# Write the notebook
with open('Kunal_solution.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=2)

print("Created Kunal_solution.ipynb with complete implementation")
