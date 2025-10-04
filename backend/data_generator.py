# backend/src/data_generator.py
import uuid
import random
import csv
from faker import Faker

NUM_ROWS = 700
OUTPUT_FILE = 'data/people.csv'
ROLES = ["Founder", "Co-founder", "Engineer", "PM", "Investor", "Other"]
STAGES = ["none", "pre-seed", "seed", "series A", "growth"]
KEYWORDS_POOL = [
"healthtech", "AI", "marketplace", "fintech", "saas", "devtools",
"biotech", "e-commerce", "edtech", "social", "blockchain",
"cleantech", "robotics", "foodtech", "agritech", "cybersecurity"
]
LOCATIONS = [
"San Francisco, USA", "New York, USA", "London, UK", "Berlin, Germany",
"Bangalore, India", "Singapore, Singapore", "Toronto, Canada", "Paris, France"
]


def generate_data(num_rows):
    fake = Faker()
    data = []
    for _ in range(num_rows):
        founder_name = fake.name()
        
        # Ensure a few founders have high-quality 'about' and 'idea'
        if random.random() < 0.15: # 15% get detailed bios
            idea = f"A cutting-edge {random.choice(KEYWORDS_POOL)} platform that uses {random.choice(['AI', 'ML', 'blockchain'])} to optimize {fake.bs()}. The solution is focused on achieving a 10x improvement in efficiency."
            about = f"Former lead engineer at {fake.company()} and two-time startup founder. Successfully raised a $5M seed round. Specializes in scalable architecture and system design. Has a strong track record of building and exiting companies in the {random.choice(KEYWORDS_POOL)} space."
            stage = random.choice(["seed", "series A", "growth"])
        else:
            idea = f"Building a simple, yet effective, {random.choice(KEYWORDS_POOL)} solution for {fake.job()}s."
            about = f"Started career in {fake.job()}. Has strong skills in {random.choice(['Python', 'React', 'Data Analysis'])} and is passionate about {fake.catch_phrase()}."
            stage = random.choice(STAGES)
            
        # Select 2-4 unique keywords
        kws = random.sample(KEYWORDS_POOL, k=random.randint(2, 4))
        
        data.append({
            "id": str(uuid.uuid4()),
            "founder_name": founder_name,
            "email": fake.email(),
            "role": random.choice(ROLES),
            "company": fake.company(),
            "location": random.choice(LOCATIONS),
            "idea": idea,
            "about": about,
            "keywords": ", ".join(kws),
            "stage": stage,
            "linked_in": f"https://linkedin.com/in/{founder_name.replace(' ', '-').lower()}",
            "notes": fake.text(max_nb_chars=50) if random.random() < 0.2 else "", # 20% have notes
        })
        
    return data

if __name__ == "__main__":
    print(f"Generating {NUM_ROWS} rows of data...")
    dataset = generate_data(NUM_ROWS)

    # Get column names from the first dictionary
    fieldnames = list(dataset[0].keys())

    # Write to CSV
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dataset)

    print(f"Data successfully generated and saved to {OUTPUT_FILE}")

    # 4. Generate README snippet
    print("\nREADME Snippet (12 Example Rows):")
    readme_snippet = [
        "| ID (Snippet) | Founder Name | Role | Company | Idea | Keywords | Stage | Location |",
        "|---|---|---|---|---|---|---|---|"
    ]
    for row in dataset[:12]:
        row_data = [
            row['id'][:8] + '...',
            row['founder_name'],
            row['role'],
            row['company'],
            row['idea'][:50] + '...',
            row['keywords'],
            row['stage'],
            row['location']
        ]
        readme_snippet.append("| " + " | ".join(row_data) + " |")

    print('\n'.join(readme_snippet))