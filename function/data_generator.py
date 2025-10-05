# data_generator.py
import uuid
import random
import csv
from faker import Faker
import os

# Configuration
NUM_ROWS = 700
OUTPUT_DIR = 'data'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'people.csv')
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
            about = f"Former lead engineer at {fake.company()} and two-time startup founder. Successfully raised a ${random.randint(1, 10)}M round for his last venture. Deeply committed to solving the problem of {fake.word()}."
        else:
            idea = fake.catch_phrase() + " focused on " + random.choice(KEYWORDS_POOL)
            about = fake.text(max_nb_chars=150)
            
        kws = random.sample(KEYWORDS_POOL, k=random.randint(2, 5))
        stage = random.choice(STAGES)
        
        data.append({
            "id": str(uuid.uuid4()),
            "founder_name": founder_name,
            "role": random.choice(ROLES),
            "company": fake.company(),
            "location": random.choice(LOCATIONS),
            "idea": idea,
            "about": about,
            "keywords": ", ".join(kws),
            "stage": stage,
            "linked_in": f"[https://linkedin.com/in/](https://linkedin.com/in/){founder_name.replace(' ', '-').lower()}",
            "notes": fake.text(max_nb_chars=50) if random.random() < 0.2 else "", # 20% have notes
        })
        
    return data

if __name__ == "__main__":
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
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