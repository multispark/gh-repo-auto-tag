### Auto Tagging for [AI Agents Hackathon Issues](https://github.com/microsoft/AI_Agents_Hackathon/issues) (projects)

#### Components

- scrape: an issue scraper and classifier of project categories that gives a final output, the classified issues are present in final.json along with the count
- label: convert_json.ipynb converts final.json to a format that can be parsed by our bash scripts
- bash: contains bash scripts

#### Steps

- use scrape_combined.py, this produces final.json
- convert final.json to a format to use in bash using convert_json.ipynb (first block of code in the notebook produces issues-to-label.json, second block produces copilot-issues.json)
- run tag-issues bash script using GitHub CLI
- run tag-copilot bash script using GitHub CLI

#### Notes

- you will need two dependencies, one is GitHub CLI and the other is a library called jq (it's how the json files are being parsed), once you have both, do a normal GitHub auth login and cd into the directory with the bash scripts
- the command to run the bash scripts: bash script-name.sh

Credit to [Paul](https://github.com/Paul-M-Kallarackal) for the scrape_combined.py script.
