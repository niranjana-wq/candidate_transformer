from transform.mapper import mapping_registry

"""
Declarative default schema mappings for all supported source types.
Maps native adapter extraction keys to CanonicalRecord paths.
"""

CSV_MAPPING = {
    "candidate_id": "candidate_id",
    "full_name": "full_name",
    "emails": "emails",
    "phones": "phones",
    "location": "location.country",
    "job_title": "headline",
    "years_experience": "years_experience",
    "education": "education",
    "skills": "skills",
    "github_url": "links.github",
    "linkedin_url": "links.linkedin",
    "current_company": "experience[0].company"
}

JSON_MAPPING = {
    "candidate_id": "candidate_id",
    "name": "full_name",
    "full_name": "full_name",
    "contact.primary_email": "emails",
    "contact.alternate_emails": "emails",
    "contact.primary_phone": "phones",
    "contact.alternate_phone": "phones",
    "location.country": "location.country",
    "location.city": "location.city",
    "social.github": "links.github",
    "social.linkedin": "links.linkedin",
    "social.portfolio": "links.portfolio",
    "education": "education",
    "experience": "experience",
    "skills": "skills"
}

PDF_MAPPING = {
    "name": "full_name",
    "headline": "headline",
    "email": "emails",
    "phone": "phones",
    "location": "location.country",
    "skills": "skills",
    "experience": "experience",
    "education": "education"
}

TXT_MAPPING = {
    "name": "full_name",
    "email": "emails",
    "phone": "phones",
    "location": "location.country",
    "skills": "skills"
}

GITHUB_MAPPING = {
    "name": "full_name",
    "email": "emails",
    "bio": "headline",
    "location": "location.country"
}

LINKEDIN_MAPPING = {
    "full_name": "full_name",
    "headline": "headline",
    "location": "location.country",
    "emails": "emails",
    "phones": "phones",
    "skills": "skills",
    "experience": "experience",
    "education": "education"
}

mapping_registry.register("csv", CSV_MAPPING)
mapping_registry.register("json", JSON_MAPPING)
mapping_registry.register("pdf", PDF_MAPPING)
mapping_registry.register("txt", TXT_MAPPING)
mapping_registry.register("github", GITHUB_MAPPING)
mapping_registry.register("linkedin", LINKEDIN_MAPPING)
