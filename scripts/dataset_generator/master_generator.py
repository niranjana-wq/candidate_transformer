import random
import uuid
from typing import List, Dict, Any
from faker import Faker

class MasterGenerator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.fake = Faker()
        self.fake.seed_instance(seed)
        random.seed(seed)
        
        self.tech_skills = ["Python", "Java", "C++", "React", "Node.js", "Docker", "Kubernetes", "AWS", "SQL", "Machine Learning", "Go", "Rust"]
        self.companies = ["Google", "Amazon", "Microsoft", "Meta", "Apple", "Netflix", "Uber", "Airbnb", "Stripe", "Block"]
        self.degrees = ["B.S. Computer Science", "M.S. Computer Science", "B.A. Mathematics", "Ph.D. Artificial Intelligence"]

    def generate_candidate(self) -> Dict[str, Any]:
        c_id = str(uuid.UUID(int=random.getrandbits(128), version=4))
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        domain = self.fake.domain_name()
        
        num_skills = random.randint(3, 8)
        skills = random.sample(self.tech_skills, num_skills)
        
        num_exp = random.randint(1, 4)
        experience = []
        for _ in range(num_exp):
            experience.append({
                "company": random.choice(self.companies),
                "title": self.fake.job(),
                "start_date": self.fake.date_between(start_date="-10y", end_date="-1y").strftime("%Y-%m-%d"),
                "end_date": self.fake.date_between(start_date="-1y", end_date="today").strftime("%Y-%m-%d")
            })
            
        education = [{
            "degree": random.choice(self.degrees),
            "institution": self.fake.university() if hasattr(self.fake, 'university') else self.fake.company() + " University",
            "end_year": str(random.randint(2010, 2024))
        }]

        return {
            "uuid": c_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": f"{first_name.lower()}.{last_name.lower()}@{domain}",
            "phone": self.fake.phone_number(),
            "github": f"https://github.com/{first_name.lower()}{last_name.lower()}",
            "linkedin": f"https://linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{random.randint(100,999)}",
            "location": {
                "city": self.fake.city(),
                "country": self.fake.country()
            },
            "skills": skills,
            "experience": experience,
            "education": education
        }

    def generate_ambiguous_pair(self, base_candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a candidate that shares the exact same name and some history, but is technically different."""
        pair = base_candidate.copy()
        pair["uuid"] = str(uuid.UUID(int=random.getrandbits(128), version=4))
        pair["email"] = f"{base_candidate['first_name'].lower()}.{base_candidate['last_name'].lower()}@otherdomain.com"
        pair["phone"] = self.fake.phone_number()
        pair["github"] = f"https://github.com/{base_candidate['first_name'].lower()}_{base_candidate['last_name'].lower()}_alt"
        pair["linkedin"] = f"https://linkedin.com/in/{base_candidate['first_name'].lower()}-{base_candidate['last_name'].lower()}-alt"
        
        # Keep name identical, but change location
        pair["location"] = {
            "city": self.fake.city(),
            "country": self.fake.country()
        }
        return pair

    def generate_dataset(self, scale: int = 100, ambiguous_rate: float = 0.05) -> List[Dict[str, Any]]:
        dataset = []
        num_ambiguous = int(scale * ambiguous_rate)
        num_standard = scale - num_ambiguous
        
        for _ in range(num_standard):
            dataset.append(self.generate_candidate())
            
        # Select random base candidates to pair
        if num_ambiguous > 0 and num_standard > 0:
            bases = random.choices(dataset, k=num_ambiguous)
            for base in bases:
                dataset.append(self.generate_ambiguous_pair(base))
                
        random.shuffle(dataset)
        return dataset
